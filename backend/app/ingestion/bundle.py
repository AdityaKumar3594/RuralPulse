"""Loading and cross-checking the whole seed set, independent of the database."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import TypeAdapter, ValidationError

from app.modules.catalog.seed_schema import CareerSeed
from app.modules.sources.seed_schema import (
    TRUSTED_SUFFIXES,
    OpportunitySeed,
    SourceSeed,
    host_allowed,
    https_host,
)

SEED_FILES = ("sources.yaml", "opportunities.yaml", "careers.yaml")


class SeedError(Exception):
    def __init__(self, problems: list[str]) -> None:
        super().__init__("\n".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class SeedBundle:
    sources: list[SourceSeed]
    opportunities: list[OpportunitySeed]
    careers: list[CareerSeed]


def _read(path: Path, adapter: TypeAdapter[Any], problems: list[str]) -> list[Any]:
    if not path.exists():
        problems.append(f"{path.name}: file not found")
        return []
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    except yaml.YAMLError as exc:
        problems.append(f"{path.name}: invalid YAML ({exc})")
        return []
    try:
        return adapter.validate_python(raw)
    except ValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(p) for p in err["loc"])
            problems.append(f"{path.name}: {loc}: {err['msg']}")
        return []


def _duplicates(label: str, ids: list[str], problems: list[str]) -> None:
    for i in sorted({i for i in ids if ids.count(i) > 1}):
        problems.append(f"duplicate {label}: {i}")


def load_bundle(directory: Path) -> SeedBundle:
    """Read and validate every seed file. Raises SeedError listing *all* problems found."""
    problems: list[str] = []
    sources = _read(directory / "sources.yaml", TypeAdapter(list[SourceSeed]), problems)
    opps = _read(directory / "opportunities.yaml", TypeAdapter(list[OpportunitySeed]), problems)
    careers = _read(directory / "careers.yaml", TypeAdapter(list[CareerSeed]), problems)

    _duplicates("source id", [s.id for s in sources], problems)
    _duplicates("opportunity slug", [o.slug for o in opps], problems)
    _duplicates("career slug", [c.slug for c in careers], problems)

    by_source = {s.id: s for s in sources}
    opp_slugs = {o.slug for o in opps}
    career_slugs = {c.slug for c in careers}

    for o in opps:
        src = by_source.get(o.source)
        if src is None:
            problems.append(f"opportunity {o.slug}: unknown source '{o.source}'")
            continue
        if not host_allowed(https_host(o.url), src.allowed_domains):
            problems.append(f"opportunity {o.slug}: url host is not on source '{src.id}' domains")
        for ev in o.verification.evidence:
            try:
                host = https_host(ev.url)
            except ValueError as exc:
                problems.append(f"opportunity {o.slug}: evidence {exc}")
                continue
            if not (host.endswith(TRUSTED_SUFFIXES) or host_allowed(host, src.allowed_domains)):
                problems.append(
                    f"opportunity {o.slug}: evidence host {host} is not an official site"
                )
    for c in careers:
        for rel in c.related:
            if rel not in career_slugs or rel == c.slug:
                problems.append(f"career {c.slug}: bad related career '{rel}'")
        for res in c.learning_resources:
            if res not in opp_slugs:
                problems.append(f"career {c.slug}: unknown learning resource '{res}'")
        for route in c.routes:
            if route.opportunity and route.opportunity not in opp_slugs:
                problems.append(
                    f"career {c.slug}: route cites unknown opportunity '{route.opportunity}'"
                )
        for ref in c.source_refs:
            if ref.source not in by_source:
                problems.append(f"career {c.slug}: unknown source '{ref.source}'")
    if problems:
        raise SeedError(problems)
    return SeedBundle(sources, opps, careers)
