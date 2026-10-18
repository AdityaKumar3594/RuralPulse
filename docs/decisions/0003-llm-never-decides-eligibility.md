# 0003 — The LLM never decides eligibility

Status: accepted (2026-10-18)

**Decision.** Eligibility is computed by a versioned, deterministic rules engine over structured
profile data and published requirements. The LLM may interpret free-text answers into candidate
structured values (validated before saving) and explain computed results in simple language.
**Consequences.** Results are reproducible and auditable; explanations are validated against the
computed result and evidence.
