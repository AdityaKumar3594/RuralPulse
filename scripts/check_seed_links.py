"""Check that every URL in data/seed still responds. Network required; run by hand:

    cd backend && uv run --with certifi python ../scripts/check_seed_links.py

A 200 only shows that the page exists, not that the facts on it still match the record.
Some government sites block scripts (403/timeouts); those need a manual look.
"""

import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

import certifi
import yaml

SEED = Path(__file__).resolve().parents[1] / "data" / "seed"
# Verify certificates against certifi's bundle: some Python builds ship without a CA store.
CONTEXT = ssl.create_default_context(cafile=certifi.where())
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15"


def check(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})  # noqa: S310 - https only, from our seed
    try:
        with urllib.request.urlopen(req, timeout=30, context=CONTEXT) as resp:  # noqa: S310
            final = resp.geturl()
            return f"{resp.status}" + (f" -> {final}" if final.rstrip("/") != url.rstrip("/") else "")
    except urllib.error.HTTPError as exc:
        return f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return f"ERROR {type(exc).__name__}"


def main() -> int:
    urls: dict[str, str] = {}
    for src in yaml.safe_load((SEED / "sources.yaml").read_text(encoding="utf-8")):
        urls[src["base_url"]] = f"source {src['id']}"
    for opp in yaml.safe_load((SEED / "opportunities.yaml").read_text(encoding="utf-8")):
        urls.setdefault(opp["url"], f"opportunity {opp['slug']}")
        for ev in opp.get("verification", {}).get("evidence", []):
            urls.setdefault(ev["url"], f"evidence for {opp['slug']}")
    bad = 0
    for url, label in urls.items():
        result = check(url)
        ok = result.startswith("200")
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} {result:<60} {label}: {url}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
