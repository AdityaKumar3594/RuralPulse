export interface User {
  id: string
  role: string
  display_name: string
  preferred_language: string
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  user: User
}

export interface Consent {
  purpose: string
  policy_version: string
  given_by: 'self' | 'guardian'
  verification: string
  granted_at: string
}

export interface ConsentStatus {
  required_given_by: 'self' | 'guardian'
  policy_version: string
  active: Consent | null
}

export interface Option {
  value: string
  label: string
}

export type QuestionKind = 'single_choice' | 'list_text' | 'number' | 'short_text'

export interface Question {
  id: string
  field_key: string
  kind: QuestionKind
  prompt: string
  why: string
  options: Option[]
  /** Bounds for number questions, from the server. */
  min_value?: number | null
  max_value?: number | null
}

export interface InterviewSession {
  id: string
  status: 'active' | 'completed'
  language: string
  question: Question | null
  progress: { answered: number; total: number }
}

export type AnswerPayload =
  | { question_id: string; kind: 'value'; value: unknown }
  | { question_id: string; kind: 'text'; text: string }
  | { question_id: string; kind: 'unknown' }
  | { question_id: string; kind: 'skip' }

export interface AnswerResult {
  outcome: 'recorded' | 'unknown' | 'skipped' | 'needs_clarification'
  corrected: boolean
  interpreted_by: 'student' | 'deterministic' | 'ai' | null
  message: string | null
  session: InterviewSession
}

export type Provenance = 'reported' | 'observed' | 'hypothesis' | 'unknown'

export interface ProfileEntry {
  id: string
  provenance: Provenance
  value: unknown
  verification: 'unverified' | 'verified' | 'disputed'
  source: string
  basis: string | null
  created_at: string
}

export interface ProfileField {
  key: string
  description: string
  state: 'established' | 'hypothesis_only' | 'unknown'
  conflict: boolean
  entries: ProfileEntry[]
}

export interface Profile {
  fields: ProfileField[]
}
