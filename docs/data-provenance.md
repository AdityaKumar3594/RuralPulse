# Data provenance

Everything the app tells a student as fact must trace back to a source record. This page says
what is in `data/seed/`, how it was checked, and what it does **not** claim.

## Files

| File | Contents |
|---|---|
| `data/seed/sources.yaml` | Registry of publishers (domains, whether a public API was found) |
| `data/seed/opportunities.yaml` | Opportunities and portals, each with verification metadata |
| `data/seed/careers.yaml` | Career catalog (30 careers, 10 families, English + Tamil) |

Test fixtures live in `backend/tests/fixtures/seed/` and are never loaded in production.

## The invariant

A structured claim (benefit amount, deadline, eligibility rules, required documents, state
scope) is accepted by the loader **only if** the record lists that field in
`verification.verified_fields` and carries evidence (an official URL and a note). Unverified
records hold general descriptions only. `make validate-seed` (also run in CI) rejects violations.
Ingestion never promotes a record to verified by itself.

## What was verified, and by whom (2026-10-18)

Checked by an automated agent (Claude Code), **not yet by a person**: `human_reviewed` is
`false` on every record and must only be flipped by someone who re-checks the official page.

| Record | Verified fields | Evidence |
|---|---|---|
| Portals (DIKSHA, SWAYAM, Skill India Digital Hub, Apprenticeship India, NSP, NCS, TN skill portal) | url, provider, existence | Page reachable; title and "Government of India/Tamil Nadu" wording read from the page |
| NAPS stipend support | benefit | PIB release 11 Feb 2026 (MSDE): government share limited to 25% of the prescribed minimum stipend, up to Rs. 1,500 per month per apprentice |
| NMMSS scholarship | eligibility, documents | Official NMMSS FAQ on scholarships.gov.in: parental income not above Rs. 3,50,000; 55% in Class VII (5% relaxation for SC/ST); Government, aided or local body schools; income and caste certificates checked at the school |
| TN skill portal | scope | Page header "Government of Tamil Nadu"; `naanmudhalvan.tn.gov.in` redirected to it |

`other_criteria` on a record lists conditions the source states that the eligibility engine
cannot check (for NMMSS: school type and Class VII marks). While any exist, a student who
passes every modelled rule gets NEEDS_REVIEW, never ELIGIBLE.

Deliberately **not** recorded: NMMSS classes covered and scholarship amount (the FAQ does not
state them), application deadlines (they change yearly), and anything only seen on aggregator
sites. Amounts can change: records are reported `stale` after 180 days and the UI must send
students to the official page.

## Careers

The career catalog is a **curated draft**: `verification_status: unverified`,
`localization_status: unreviewed`. Descriptions say what the work is, with no salaries,
statistics or demand claims (enforced by the schema). Entry routes are "typical, not an official
requirement". A subject expert should review the catalog, and a native Tamil speaker the Tamil.

## Source access

None of the listed sources offers a public read API that we found (`api_access: none_found`).
We link to them and do not scrape. Add an ingestion adapter only after access, permitted use
and authentication are established.

## Re-checking

`make check-links` confirms every seed URL still responds (a 200 does not prove the facts still
match). Re-verification means re-reading the official page, updating `verified_at`, and setting
`human_reviewed: true` only after a person has done so.
