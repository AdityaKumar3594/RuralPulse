"""Builds the evidence package for an explanation and the deterministic template from it.

Evidence is structured facts that already exist (ranking results, eligibility outcomes,
pathway steps). It is the only thing the AI sees and the only thing an explanation may cite.
"""

import re
from typing import Any

from app.modules.explain.texts import tr
from app.modules.pathway.texts import stage_label

_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
MAX_STRING = 300


def clean(text: str) -> str:
    """Neutralise text from outside (profile, catalog, partners) before it goes near a prompt:
    no control characters, no angle brackets (so nothing can close our <evidence> tags)."""
    text = _CONTROL.sub(" ", text).replace("<", "‹").replace(">", "›")
    return text[:MAX_STRING]


def sanitize(value: Any) -> Any:
    if isinstance(value, str):
        return clean(value)
    if isinstance(value, dict):
        return {clean(str(k)): sanitize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize(v) for v in value]
    return value


# --- recommendation ---


def recommendation_evidence(item: dict[str, Any], language: str) -> tuple[dict, set[str], None]:
    caveats = [f for f in item["flags"] if f == "catalog_entry_unverified"] + list(item["unknowns"])
    evidence = {
        "kind": "recommendation",
        "language": language,
        "career": {
            "title": item["career"]["title"],
            "family": item["career"]["family"],
            "description": item["career"]["description"],
        },
        "recommendation_kind": item["kind"],
        "match_level": item["match_level"],
        "reasons": [
            {
                "student_said": r["student_term"],
                "career_lists": r["matched_text"],
                "in": r["career_field"],
            }
            for r in item["reasons"][:3]
        ],
        "entry": {
            "typical_min_stage": item["stage"]["typical_min_stage"],
            "status": item["stage"]["status"],
            "student_stage": item["stage"]["student_stage"],
            "notes": item["career"]["entry_notes"],
        },
        "routes": [{"kind": r["kind"], "title": r["title"]} for r in item["routes"]],
        "sources": [
            {
                "title": s["title"],
                "url": s["url"],
                "verification": s["verification_status"],
                "freshness": s["freshness"],
            }
            for s in item["sources"]
        ],
        "unknowns": item["unknowns"],
        "flags": item["flags"],
        "caveats": caveats,
    }
    return sanitize(evidence), {s["url"] for s in item["sources"]}, None


def recommendation_template(evidence: dict[str, Any]) -> dict[str, Any]:
    lang = evidence["language"]
    title = evidence["career"]["title"]
    if evidence["recommendation_kind"] == "explore":
        headline = tr("rec_headline_explore", lang, title=title)
        why = [tr("rec_why_explore", lang)]
    else:
        level = tr(f"level_{evidence['match_level']}", lang)
        headline = tr("rec_headline_match", lang, title=title, level=level)
        why = [
            tr("rec_why_term", lang, term=r["student_said"], matched=r["career_lists"])
            for r in evidence["reasons"]
        ]
    entry = evidence["entry"]
    requirements = []
    if entry["typical_min_stage"]:
        requirements.append(
            tr("rec_req_stage", lang, stage=stage_label(entry["typical_min_stage"], lang))
        )
        if entry["status"] == "below" and entry["student_stage"]:
            requirements.append(
                tr("rec_req_below", lang, stage=stage_label(entry["student_stage"], lang))
            )
    else:
        requirements.append(tr("rec_req_none", lang))
    note = (
        tr("rec_caveat_catalog", lang)
        if "catalog_entry_unverified" in evidence["flags"]
        else tr("rec_caveat_checked", lang)
    )
    missing = [tr(u, lang) for u in evidence["unknowns"] if u in _RECOMMENDATION_UNKNOWNS][:5]
    if entry["status"] == "unknown" and entry["typical_min_stage"]:
        next_action = tr("next_tell_stage", lang)
    elif entry["status"] == "below" and entry["typical_min_stage"]:
        next_action = tr(
            "next_plan_prerequisite", lang, stage=stage_label(entry["typical_min_stage"], lang)
        )
    else:
        next_action = tr("next_view_career", lang)
    return {
        "headline": headline,
        "why": why,
        "requirements": requirements,
        "eligibility_status": "NOT_APPLICABLE",
        "freshness_note": note,
        "missing_information": missing,
        "next_action": next_action,
    }


_RECOMMENDATION_UNKNOWNS = {
    "career_cost_unknown",
    "career_time_needed_unknown",
    "career_location_not_considered",
    "student_skills_not_told",
    "student_interests_not_told",
}


# --- eligibility ---


def eligibility_evidence(
    evaluation: dict[str, Any], opportunity: dict[str, Any], language: str
) -> tuple[dict, set[str], str]:
    elig = opportunity.get("eligibility") or {}
    record = evaluation["record"]
    caveats = []
    if opportunity["freshness"] != "fresh":
        caveats.append(opportunity["freshness"])
    if not record.get("human_reviewed"):
        caveats.append("not_human_reviewed")
    evidence = {
        "kind": "eligibility",
        "language": language,
        "opportunity": {
            "title": opportunity["title"],
            "provider": opportunity["provider"],
            "url": opportunity["url"],
            "summary": opportunity["summary"],
        },
        "outcome": evaluation["outcome"],
        "reasons": evaluation["reasons"],
        "checks": [
            {
                "rule": c["rule"],
                "result": c["result"],
                "expected": c["expected"],
                "actual": c["actual"],
            }
            for c in evaluation["checks"]
        ],
        "missing": [m["fact"] for m in evaluation["missing"]],
        "flags": evaluation["flags"],
        "record": {
            "verified_fields": record["verified_fields"],
            "verified_at": record["verified_at"],
            "human_reviewed": record["human_reviewed"],
            "freshness": opportunity["freshness"],
        },
        "benefits": [b["text"] for b in opportunity["benefits"] if b["text"]],
        "required_documents": opportunity["required_documents"],
        "deadline": opportunity["application_deadline"].isoformat()
        if opportunity["application_deadline"]
        else None,
        "other_criteria": elig.get("other_criteria", []),
        "caveats": caveats,
    }
    return sanitize(evidence), {opportunity["url"]}, evaluation["outcome"]


def _reason_text(code: str, evidence: dict[str, Any], lang: str) -> str:
    checks = {c["rule"]: c for c in evidence["checks"]}
    if code == "family_income_above_limit":
        c = checks["family_income_max"]
        return tr(code, lang, expected=c["expected"], actual=c["actual"])
    if code in ("age_below_minimum", "age_above_maximum"):
        c = checks["age_min" if code == "age_below_minimum" else "age_max"]
        return tr(code, lang, limit=c["expected"]["limit"])
    if code == "state_not_covered":
        return tr(code, lang, states=", ".join(checks["state"]["expected"]))
    if code.startswith("conflicting_"):
        return tr("conflicting", lang)
    if code.startswith("missing_"):
        return tr("missing_some", lang)
    if code == "other_criteria_need_review":
        return tr(code, lang, conditions="; ".join(evidence["other_criteria"]))
    if code in ("criteria_not_verified", "no_verified_criteria"):
        return tr("no_verified_criteria", lang)
    return tr(code, lang)


def eligibility_template(evidence: dict[str, Any]) -> dict[str, Any]:
    lang, outcome = evidence["language"], evidence["outcome"]
    title = evidence["opportunity"]["title"]
    why = [_reason_text(c, evidence, lang) for c in evidence["reasons"]] or [
        tr("why_all_met", lang)
    ]
    requirements = []
    if evidence["required_documents"]:
        requirements.append(
            tr("req_documents", lang, docs="; ".join(evidence["required_documents"]))
        )
    requirements += [tr("req_benefit", lang, text=b) for b in evidence["benefits"]][:2]
    if evidence["deadline"]:
        requirements.append(tr("req_deadline", lang, date=evidence["deadline"]))
    record = evidence["record"]
    note = tr(f"fresh_{record['freshness']}", lang, date=record["verified_at"] or "")
    if not record["human_reviewed"]:
        note += tr("not_human_reviewed", lang)
    missing = [tr(f"fact_{m}", lang) for m in evidence["missing"]]
    if outcome == "UNKNOWN":
        action = (
            tr("next_UNKNOWN_missing", lang)
            if missing
            else tr("next_UNKNOWN", lang, url=evidence["opportunity"]["url"])
        )
    elif outcome == "INELIGIBLE":
        action = tr("next_INELIGIBLE", lang)
    else:
        action = tr(f"next_{outcome}", lang, url=evidence["opportunity"]["url"])
    return {
        "headline": tr(f"elig_headline_{outcome}", lang, title=title),
        "why": why[:5],
        "requirements": requirements[:5],
        "eligibility_status": outcome,
        "freshness_note": note,
        "missing_information": missing[:5],
        "next_action": action,
    }


# --- pathway ---


def pathway_evidence(plan: dict[str, Any], language: str) -> tuple[dict, set[str], None]:
    steps = [
        {
            "id": s["id"],
            "title": s["title"],
            "type": s["type"],
            "level": s["requirement_level"],
            "status": s["status"],
            "depends_on": s["depends_on"],
        }
        for s in plan["steps"]
    ]
    urls = {s["resource"]["url"] for s in plan["steps"] if s.get("resource")}
    evidence = {
        "kind": "pathway",
        "language": language,
        "career": plan["career"]["title"],
        "steps": steps,
        "alternatives": plan["alternatives"],
        "unknowns": plan["unknowns"],
        "caveats": list(plan["unknowns"]),
    }
    return sanitize(evidence), urls, None


def pathway_template(evidence: dict[str, Any]) -> dict[str, Any]:
    lang = evidence["language"]
    pending = [s for s in evidence["steps"] if s["status"] != "done"]
    first = next(
        (s for s in pending if s["status"] == "in_progress"), pending[0] if pending else None
    )
    return {
        "headline": tr("path_headline", lang, title=evidence["career"]),
        "why": [tr("path_why", lang), tr("path_alternatives", lang)],
        "requirements": [s["title"] for s in evidence["steps"] if s["type"] == "qualification"][:5],
        "eligibility_status": "NOT_APPLICABLE",
        "freshness_note": tr("path_unknown_effort", lang),
        "missing_information": [],
        "next_action": tr("path_next", lang, step=first["title"])
        if first
        else tr("path_all_done", lang),
    }
