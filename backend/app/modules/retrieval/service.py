"""Keyword retrieval over approved careers and opportunities (PostgreSQL full text + trigram).

Principles:
- Unknown is not negative: a record is dropped by a filter only when it *explicitly* excludes
  the student (a stated state or education stage that does not match). Silence keeps it,
  flagged as such.
- Expired records are hidden by default; stale and unverified ones are returned with flags.
- With no match we say so (`insufficient_evidence`) instead of padding with weak results.
- Results carry source and freshness metadata so explanations can cite them.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, literal, or_, select
from sqlalchemy.orm import Session

from app.core.localize import Localizer
from app.core.text import tokenize
from app.modules.catalog.models import Career
from app.modules.sources.freshness import freshness
from app.modules.sources.models import Opportunity, Publication, Source
from app.modules.sources.service import flags_for, source_brief

# Measured on pg_trgm word_similarity: genuine typos score 0.57-0.75 (e.g. electrcian 0.64,
# scholarshpi 0.75) while look-alike words score 0.50-0.56 (scholar/school 0.50,
# training/trade 0.56). 0.6 keeps the typos and drops those, at the cost of missing very short
# misspellings. Typo tolerance is best-effort, not a guarantee.
SIMILARITY_THRESHOLD = 0.6
MIN_SIMILARITY_LEN = 5  # shorter words give noisy trigram matches


@dataclass(frozen=True)
class Filters:
    type: str | None = None  # "career" | "opportunity"
    kind: str | None = None  # opportunity kind
    family: str | None = None  # career family
    state: str | None = None
    stage: str | None = None
    include_expired: bool = False
    include_unverified: bool = True


def _candidates(db: Session, model: Any, tokens: list[str]) -> list[tuple[Any, str, float]]:
    """(row, match_type, score) for every row matching at least one query word."""
    if not tokens:
        return [(row, "browse", 0.0) for row in db.scalars(select(model))]
    exact_q = func.plainto_tsquery("simple", " ".join(tokens))
    prefix_q = func.to_tsquery("simple", " | ".join(f"'{t}':*" for t in tokens))
    exact = model.search_vector.op("@@")(exact_q)
    prefix = model.search_vector.op("@@")(prefix_q)
    fuzzy_tokens = [t for t in tokens if len(t) >= MIN_SIMILARITY_LEN]
    sim = (
        func.greatest(*[func.word_similarity(t, model.search_text) for t in fuzzy_tokens])
        if fuzzy_tokens
        else None
    )
    conditions = [exact, prefix] + ([sim >= SIMILARITY_THRESHOLD] if sim is not None else [])
    columns = [model, exact, func.ts_rank(model.search_vector, prefix_q)]
    columns.append(sim if sim is not None else literal(0.0))
    rows = db.execute(select(*columns).where(or_(*conditions)))
    out = []
    for row, is_exact, rank, similarity in rows:
        score = (2.0 if is_exact else 0.0) + float(rank or 0) + 0.5 * float(similarity or 0)
        out.append((row, "exact" if is_exact else "partial", round(score, 4)))
    return out


def _opportunity_passes(opp: Opportunity, fresh: str, f: Filters) -> bool:
    if opp.publication_status is not Publication.PUBLISHED:
        return False
    if f.kind and opp.kind != f.kind:
        return False
    if fresh == "expired" and not f.include_expired:
        return False
    if fresh == "unverified" and not f.include_unverified:
        return False
    states = [s.casefold() for s in opp.scope.get("states", [])]
    if f.state and opp.scope.get("level") == "state" and f.state.casefold() not in states:
        return False  # stated as restricted to other states
    stages = (opp.eligibility or {}).get("education_stages")
    # stated as open only to other stages
    return not (f.stage and stages and f.stage not in stages)


def _eligibility_known(opp: Opportunity) -> bool:
    e = opp.eligibility or {}
    return "eligibility" in opp.verified_fields and any(
        e.get(k) is not None
        for k in ("education_stages", "min_age", "max_age", "max_family_income_inr_per_year")
    )


def search(
    db: Session,
    query: str | None,
    *,
    lang: str,
    filters: Filters,
    limit: int,
    fresh_days: int,
    today: date | None = None,
) -> dict[str, Any]:
    today = today or datetime.now(UTC).date()
    tokens = tokenize(query)
    hits: list[dict[str, Any]] = []

    if filters.type in (None, "opportunity") and not filters.family:
        sources = {s.id: s for s in db.scalars(select(Source))}
        for opp, match, score in _candidates(db, Opportunity, tokens):
            fresh = freshness(opp, today, fresh_days)
            if not _opportunity_passes(opp, fresh, filters):
                continue
            loc = Localizer(lang)
            flags = flags_for(opp, fresh)
            hits.append(
                {
                    "type": "opportunity",
                    "id": opp.slug,
                    "title": loc.text(opp.title),
                    "summary": loc.text(opp.summary),
                    "match_type": match,
                    "score": score,
                    "group": opp.kind,
                    "url": opp.url,
                    "source": source_brief(sources[opp.source_id], loc),
                    "freshness": fresh,
                    "verification": {
                        "status": opp.verification_status.value,
                        "verified_fields": opp.verified_fields,
                        "verified_at": opp.verified_at,
                        "verified_by": opp.verified_by,
                        "human_reviewed": opp.human_reviewed,
                        "evidence": opp.evidence,
                    },
                    "eligibility_known": _eligibility_known(opp),
                    "flags": flags,
                    "language_fallback": loc.fell_back,
                }
            )

    if filters.type in (None, "career") and not filters.kind:
        for career, match, score in _candidates(db, Career, tokens):
            if filters.family and career.family != filters.family:
                continue
            loc = Localizer(lang)
            hits.append(
                {
                    "type": "career",
                    "id": career.slug,
                    "title": loc.text(career.title),
                    "summary": loc.text(career.description),
                    "match_type": match,
                    "score": score,
                    "group": career.family,
                    "url": None,
                    "source": None,
                    "freshness": None,
                    "verification": None,
                    "eligibility_known": None,
                    "flags": ["catalog_entry_unverified"]
                    if career.verification_status != "verified"
                    else [],
                    "language_fallback": loc.fell_back,
                }
            )

    hits.sort(key=lambda h: (-h["score"], h["title"] or ""))
    hits = hits[:limit]

    if not hits:
        status, message = "insufficient_evidence", "No approved record matches. Nothing is guessed."
    elif tokens and not any(h["match_type"] == "exact" for h in hits):
        status, message = "partial_only", "Only partial keyword matches were found."
    else:
        status, message = "ok", None
    return {
        "query": query,
        "language": lang,
        "status": status,
        "message": message,
        "results": hits,
    }
