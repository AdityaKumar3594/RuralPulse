// backend/app/modules/eligibility/schemas.py
export type Outcome = 'ELIGIBLE' | 'INELIGIBLE' | 'UNKNOWN' | 'NEEDS_REVIEW'
export type CheckResult = 'pass' | 'fail' | 'unknown' | 'conflict'

export interface Check {
  rule: string
  result: CheckResult
  expected: unknown
  actual: unknown
  basis: string | null
}

export interface MissingFact {
  fact: string
  /** Interview question that collects it; null means it was set at registration. */
  question_id: string | null
}

export interface Evaluation {
  id: string
  opportunity: { slug: string; kind: string; title: string | null; url: string }
  outcome: Outcome
  reasons: string[]
  checks: Check[]
  missing: MissingFact[]
  flags: string[]
  facts_used: Record<string, unknown>
  rules_version: string
  opportunity_fingerprint: string
  record: Record<string, unknown>
  evaluated_on: string
  evaluated_at: string
}
