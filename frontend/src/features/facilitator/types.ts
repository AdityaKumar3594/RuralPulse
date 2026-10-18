// Shapes from backend/app/modules/facilitator/schemas.py (+ pathway/recommend embedded shapes)

export interface StudentSummary {
  id: string
  display_name: string
  preferred_language: string
  is_minor: boolean
  shared: boolean
  open_help_requests: number
}

export interface ProfileEntry {
  provenance: 'reported' | 'observed' | 'hypothesis' | 'unknown'
  value: unknown
  verification: 'unverified' | 'verified' | 'disputed' | string
  source: string
  basis: string | null
  created_at: string
}

export interface ProfileField {
  key: string
  description: string
  state: 'established' | 'hypothesis_only' | 'unknown' | string
  conflict: boolean
  entries: ProfileEntry[]
}

export interface StudentProfile {
  student: StudentSummary
  fields: ProfileField[]
}

export interface HelpRequest {
  id: string
  student_id: string
  topic: string
  message: string | null
  opportunity_slug: string | null
  status: string
  created_at: string
}

export type ReviewDecision = 'agree' | 'disagree' | 'needs_discussion'

export interface RecItem {
  slug: string
  family: string
  kind: 'match' | 'explore'
  match_level: 'strong' | 'moderate' | 'weak' | null
  career: { slug: string; title: string | null; description: string | null }
  reasons: { student_term: string; student_field: string; career_field: string; matched_text: string; basis: string }[]
  unknowns: string[]
}

export interface RecRun {
  id: string
  status: 'ok' | 'no_matches' | 'insufficient_profile'
  created_at: string
  items: RecItem[]
  notes: string[]
}

export type StepStatus = 'not_started' | 'in_progress' | 'done'

export interface PlanStep {
  id: string
  title: string | null
  type: string
  status: StepStatus
  note: string | null
  depends_on: string[]
}

export interface Plan {
  id: string
  career: { slug: string; title: string | null; family: string }
  created_at: string
  steps: PlanStep[]
}

export interface SearchHit {
  id: string
  title: string | null
}

export interface Endorsement {
  id: string
  opportunity_slug: string
  note: string | null
  status: string
  created_at: string
}
