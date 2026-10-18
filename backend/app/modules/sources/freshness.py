from datetime import date
from typing import Literal

from app.modules.sources.models import Opportunity, Verification

Freshness = Literal["fresh", "stale", "expired", "unverified"]


def freshness(opp: Opportunity, today: date, fresh_days: int) -> Freshness:
    """How far the record can be trusted *today*.

    expired: past its expiry or application deadline.  unverified: never checked against an
    official page.  stale: checked, but longer ago than `fresh_days`.
    """
    if opp.expires_on is not None and opp.expires_on < today:
        return "expired"
    if opp.application_deadline is not None and opp.application_deadline < today:
        return "expired"
    if opp.verification_status is not Verification.VERIFIED:
        return "unverified"
    if opp.verified_at is None or (today - opp.verified_at).days > fresh_days:
        return "stale"
    return "fresh"
