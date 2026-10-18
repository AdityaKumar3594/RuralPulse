"""Checks an AI-written explanation against the evidence it was given.

An explanation is accepted only if every concrete claim traces back to the evidence. Anything
else (an invented amount, deadline, link, eligibility verdict, guarantee, or a claim that the
student applied or was accepted) is rejected and replaced by a deterministic template.
"""

import json
import re
import unicodedata
from typing import Any

FIELDS = (
    "headline",
    "why",
    "requirements",
    "eligibility_status",
    "freshness_note",
    "missing_information",
    "next_action",
)
STATUSES = {"ELIGIBLE", "INELIGIBLE", "UNKNOWN", "NEEDS_REVIEW", "NOT_APPLICABLE"}
MAX_TEXT = 400
MAX_ITEMS = 5

# Phrases that promise outcomes or claim actions the system cannot confirm (English / Tamil).
FORBIDDEN_ANYWHERE = [
    r"\bguarantee",
    r"\bdefinitely\b",
    r"\bsure to\b",
    r"\b100\s?%",
    r"\bwill (?:get|receive|win)\b",
    r"\byou (?:have|'ve) applied\b",
    r"\byour application (?:was|has been) (?:sent|submitted|accepted)",
    r"\byou (?:were|have been|are) (?:accepted|selected|shortlisted)\b",
    "உறுதியாக",
    "நிச்சயம்",
    "கண்டிப்பாக கிடைக்கும்",
    "விண்ணப்பித்துவிட்டீர்கள்",
    "ஏற்றுக்கொள்ளப்பட்டீர்கள்",
]
# Claims of eligibility are allowed only when the computed outcome is ELIGIBLE.
ELIGIBILITY_CLAIMS = [
    r"\byou (?:are|'re) eligible\b",
    r"\byou qualify\b",
    r"\byou can (?:definitely )?apply\b",
    "நீங்கள் தகுதியானவர்",
    "நீங்கள் தகுதி பெற்றவர்",
]
NUMBER_RE = re.compile(r"\d[\d,]*")
URL_RE = re.compile(
    r"https?://[^\s)\]]+|\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:gov|nic|org|com|net|edu)\.?(?:in)?\b[^\s)\]]*",
    re.I,
)


def ascii_digits(text: str) -> str:
    """Map digits of any script (including Tamil) to ASCII so numbers compare equal."""
    return "".join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in text)


def numbers_in(text: str) -> set[str]:
    return {m.rstrip(",").replace(",", "") for m in NUMBER_RE.findall(ascii_digits(text))}


def urls_in(text: str) -> set[str]:
    return {m.rstrip(".,;:").lower() for m in URL_RE.findall(text)}


def evidence_text(evidence: Any) -> str:
    return json.dumps(evidence, ensure_ascii=False, default=str)


def _strings(output: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for key in FIELDS:
        value = output.get(key)
        if isinstance(value, str):
            out.append(value)
        elif isinstance(value, list):
            out.extend(v for v in value if isinstance(v, str))
    return out


def _script_ok(texts: list[str], language: str) -> bool:
    letters = [c for t in texts for c in t if c.isalpha()]
    if not letters:
        return True
    tamil = sum(1 for c in letters if "஀" <= c <= "௿")
    share = tamil / len(letters)
    return share >= 0.5 if language == "ta" else share <= 0.2


def validate_explanation(
    output: Any,
    evidence: dict[str, Any],
    *,
    language: str,
    outcome: str | None,
    allowed_urls: set[str],
) -> list[str]:
    """Return a list of violation codes; empty means the explanation may be shown."""
    violations: list[str] = []
    if not isinstance(output, dict) or set(output) != set(FIELDS):
        return ["bad_shape"]
    for key in ("headline", "freshness_note", "next_action"):
        if (
            not isinstance(output[key], str)
            or not output[key].strip()
            or len(output[key]) > MAX_TEXT
        ):
            violations.append(f"bad_{key}")
    for key in ("why", "requirements", "missing_information"):
        items = output[key]
        if (
            not isinstance(items, list)
            or len(items) > MAX_ITEMS
            or not all(isinstance(i, str) and 0 < len(i) <= MAX_TEXT for i in items)
        ):
            violations.append(f"bad_{key}")
    if output["eligibility_status"] not in STATUSES:
        violations.append("bad_eligibility_status")
    if violations:
        return violations

    expected = outcome or "NOT_APPLICABLE"
    if output["eligibility_status"] != expected:
        violations.append("eligibility_status_mismatch")

    texts = _strings(output)
    blob = " \n".join(texts)
    folded = blob.casefold()

    allowed_numbers = numbers_in(evidence_text(evidence))
    invented = numbers_in(blob) - allowed_numbers
    if invented:
        violations.append("invented_number")

    allowed = {u.lower().rstrip("/") for u in allowed_urls}
    for url in urls_in(blob):
        bare = re.sub(r"^https?://", "", url).rstrip("/")
        if not any(
            bare in a or a.endswith(bare) or bare in re.sub(r"^https?://", "", a) for a in allowed
        ):
            violations.append("invented_link")
            break

    if any(re.search(p, folded) for p in FORBIDDEN_ANYWHERE if p.isascii()) or any(
        p in blob for p in FORBIDDEN_ANYWHERE if not p.isascii()
    ):
        violations.append("promise_or_unconfirmed_claim")
    if expected != "ELIGIBLE" and (
        any(re.search(p, folded) for p in ELIGIBILITY_CLAIMS if p.isascii())
        or any(p in blob for p in ELIGIBILITY_CLAIMS if not p.isascii())
    ):
        violations.append("eligibility_claim_without_eligible_outcome")
    if not _script_ok(texts, language):
        violations.append("wrong_language")
    if evidence.get("caveats") and not output["freshness_note"].strip():
        violations.append("missing_caveat")
    return violations
