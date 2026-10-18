from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.localize import Localizer
from app.modules.catalog.models import Career
from app.modules.sources.models import Opportunity


def list_careers(db: Session, family: str | None = None) -> list[Career]:
    stmt = select(Career).order_by(Career.family, Career.slug)
    if family:
        stmt = stmt.where(Career.family == family)
    return list(db.scalars(stmt))


def get_career(db: Session, slug: str) -> Career | None:
    return db.get(Career, slug)


def career_brief(c: Career, loc: Localizer) -> dict[str, Any]:
    return {"slug": c.slug, "family": c.family, "title": loc.text(c.title)}


def _opp_brief(o: Opportunity, loc: Localizer) -> dict[str, Any]:
    return {"slug": o.slug, "kind": o.kind, "title": loc.text(o.title), "url": o.url}


def career_out(db: Session, c: Career, lang: str) -> dict[str, Any]:
    loc = Localizer(lang)
    wanted = {r["opportunity"] for r in c.routes if r.get("opportunity")} | set(
        c.learning_resources
    )
    opps = {o.slug: o for o in db.scalars(select(Opportunity).where(Opportunity.slug.in_(wanted)))}
    related = {r.slug: r for r in db.scalars(select(Career).where(Career.slug.in_(c.related)))}
    out = {
        **career_brief(c, loc),
        "description": loc.text(c.description),
        "activities": loc.items(c.activities),
        "skills": loc.items(c.skills),
        "entry": {
            "typical_min_stage": c.entry.get("typical_min_stage"),
            "notes": loc.text(c.entry.get("notes")),
        },
        "routes": [
            {
                "kind": r["kind"],
                "title": loc.text(r["title"]),
                "min_stage": r.get("min_stage"),
                "opportunity": _opp_brief(opps[r["opportunity"]], loc)
                if r.get("opportunity") in opps
                else None,
            }
            for r in c.routes
        ],
        "related": [career_brief(related[s], loc) for s in c.related if s in related],
        "learning_resources": [_opp_brief(opps[s], loc) for s in c.learning_resources if s in opps],
        "source_refs": c.source_refs,
        "verification_status": c.verification_status,
        "human_reviewed": c.human_reviewed,
        "localization_status": c.localization_status,
        "language": lang,
    }
    out["language_fallback"] = loc.fell_back
    return out
