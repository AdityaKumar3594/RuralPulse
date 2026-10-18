# Ruralpulse architecture

AI-powered learning-to-livelihood platform for rural Indian students (Class 9 to graduation),
their teachers/facilitators, and approved opportunity partners. Tamil is the first target language.

## Shape

A **modular monolith**: one FastAPI backend, one React frontend, one PostgreSQL database.
Additional infrastructure (vector store, queues, caches) is added only for a measured need.

| Layer | Where |
|---|---|
| Presentation | `frontend/` — student app, facilitator dashboard, admin (React + TS + Vite) |
| Access | `backend/app/core/` — settings, DB, auth, authorization, rate limits, audit |
| Core domain | `backend/app/modules/<module>/` — models, schemas, service, router per module |
| Intelligence | `backend/app/ai/` + `modules/{retrieval,eligibility,recommend,pathway}` |
| Data | PostgreSQL + Alembic migrations (`backend/migrations/`), curated seeds in `data/seed/` |
| Integrations | `backend/app/integrations/` — BHASHINI speech/translation, data source adapters |

## Planned modules

`identity` (users, roles, consent) · `profile` (fields with provenance) · `interview` (versioned
question bank, next-question selection) · `catalog` (careers, skills, routes) · `sources`
(source registry, opportunities, ingestion, freshness) · `retrieval` (Postgres full-text search +
filters) · `eligibility` (deterministic rules) · `recommend` (explainable ranking) · `pathway`
· `applications` · `facilitator` · `partners`.

Modules call each other through service functions. API routes live under `/api`.

## Non-negotiable rules

1. **Eligibility is deterministic code.** Results are `ELIGIBLE | INELIGIBLE | UNKNOWN |
   NEEDS_REVIEW`, stored with the rule version and evidence. Missing data → `UNKNOWN`, never
   `INELIGIBLE`. The LLM never decides eligibility. Eligibility is kept separate from suitability.
2. **Profile provenance.** Every important profile field is `reported`, `observed`, `hypothesis`
   or `unknown`, with its source. Interest is not ability; missing evidence is not inability.
3. **Grounded facts only.** Amounts, deadlines, eligibility and links come from source records
   with a URL and a verification timestamp. LLM explanations are checked against the evidence;
   on failure a deterministic template is used.
4. **Retrieved content is data, not instructions.** It is delimited in prompts and never executed.
5. **Server-side authorization.** Facilitators see only assigned students; access is audited.
6. **Minimal data about minors.** Collect only what the current task needs; design for verifiable
   parental consent (DPDP Rules 2025, Rule 10). No ads or behavioural tracking. We make no
   claim of legal compliance.
7. **No fakes.** No placeholder integrations presented as working; demo data is labelled.

## AI

Provider-independent `LLMProvider` interface; default provider Anthropic Claude
(`LLM_PROVIDER=anthropic`, `LLM_MODEL`). With `LLM_PROVIDER=none` the app still works using
templates. Outputs are validated against Pydantic schemas before use.

## Interview engine

`modules/interview/`: a versioned question bank (`questions.py`, stable ids, Tamil + English),
a pure selector (`selector.py`: highest-priority applicable question that is not answered or
skipped) and an interpreter (`interpreter.py`). Free text is interpreted deterministically where
that is enough, otherwise by the LLM through `app/ai/`. The LLM only proposes: each value must
quote the student's own words, be confident, and pass the profile field validator before the
profile changes. Without an LLM, lists are split deterministically and choice/number questions
ask the student to choose. Sessions are stored server-side and resumed per student.

## Knowledge base and retrieval

`modules/sources` (source registry, opportunities, freshness), `modules/catalog` (careers) and
`modules/retrieval` (search). Records come from validated YAML in `data/seed/` through
`app/ingestion` (`make seed`); see `docs/data-provenance.md`. Search is PostgreSQL full text
(`simple` configuration, which keeps Tamil words intact) plus `pg_trgm` for near-spellings. It
reports `exact`, `partial` or `browse` matches, never "semantic" ones (no embeddings yet), and
answers `insufficient_evidence` instead of padding weak results. Filters drop a record only when
it explicitly excludes the student; silence means "unknown", not "no". Expired records are
hidden by default, stale and unverified ones are returned with flags. Retrieved text is data:
Phase 3 must pass it to the LLM inside delimiters, never as instructions.

## Eligibility engine

`modules/eligibility/engine.py` is pure code (no database, network or LLM; a test forbids it
from importing `app.ai`). It takes an opportunity's published criteria and the student's facts
and returns one of four outcomes, with per-rule checks and the rule version (`RULES_VERSION`):

| Outcome | Meaning |
|---|---|
| ELIGIBLE | every criterion is modelled, checked against known facts, and met; record is fresh |
| INELIGIBLE | a criterion definitely fails, or the deadline/expiry has passed |
| UNKNOWN | nothing failed but a fact is missing, or no verified criteria exist (never a "no") |
| NEEDS_REVIEW | nothing failed, but a person must look: criteria the engine cannot evaluate (`other_criteria`), conflicting facts (reported vs observed), or a stale record |

Precedence: definite failure > conflict > missing fact > no verified criteria > needs review >
eligible. Only criteria listed in the record's `verified_fields` are used. Hypotheses and
"I don't know" are never facts. Facts come from the profile (observed wins over reported, and a
disagreement is a conflict) plus the registered birth date. Family income is collected only on
demand (`q_annual_family_income`, never in the general interview and never interpreted by the
LLM). Every evaluation is stored in `eligibility_evaluations` with the facts used, the rule
version, a fingerprint of the opportunity rules and the record's verification state. The audit
log keeps the outcome but none of the facts. Eligibility is separate from suitability.

## Voice and language

UI strings via react-i18next (`frontend/src/i18n/`), English fallback. Speech-to-text, TTS and
translation go through an adapter; BHASHINI is the first adapter once credentials are available
and Tamil support is verified live. Text input is always available.

## Scope

Offline functionality is **out of scope** (see `decisions/0002-offline-out-of-scope.md`).
The app targets low-end Android phones on low bandwidth: small bundles, timeouts, retries and
clear connection-error states.

## Local ports

Postgres `5432`, backend `8100` (8000 is commonly taken), frontend dev server `5173` which proxies
`/api` to the backend (`API_PROXY_TARGET` overrides).
