# 0001 — Modular monolith on FastAPI, React and PostgreSQL

Status: accepted (2026-10-18)

**Context.** Hackathon prototype that must be extensible, open source and cheap to run.
**Decision.** One backend with strict module boundaries, one frontend, PostgreSQL as the source
of truth with full-text search. No microservices, vector DB or message broker until a measured
need exists (pgvector is the first candidate if semantic retrieval proves its value).
**Consequences.** Simple deployment and testing; modules can be extracted later along their
existing boundaries.
