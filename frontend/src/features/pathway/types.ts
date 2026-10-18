// backend/app/modules/pathway/schemas.py
import type { Freshness } from '../discover/types'

export type StepStatus = 'not_started' | 'in_progress' | 'done'

export interface ResourceCard {
  slug: string
  title: string | null
  url: string
  kind: string
  source: string | null
  verification_status: string
  freshness: Freshness
  check_eligibility: boolean
}

export interface Step {
  id: string
  type: string
  group: string
  title: string | null
  depends_on: string[]
  /** typical_route | suggested_preparation. Nothing is ever "mandatory". */
  requirement_level: string
  estimated_effort: null
  stage: string | null
  route_index: number | null
  route_kind: string | null
  skills: string[] | null
  resource: ResourceCard | null
  completion_criteria: { type?: string; field?: string; reaches?: string }
  status: StepStatus
  note: string | null
}

export interface Plan {
  id: string
  career: { slug: string; title: string | null; family: string }
  version: string
  student_stage: string | null
  created_at: string
  steps: Step[]
  alternatives: string[]
  unknowns: string[]
  language_fallback: boolean
}
