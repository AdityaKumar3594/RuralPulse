// backend/app/modules/recommend/schemas.py
import type { Freshness } from '../discover/types'

export interface Reason {
  student_field: string
  student_term: string
  basis: string
  career_field: string
  matched_text: string
  points: number
}

export interface StageInfo {
  typical_min_stage: string | null
  status: 'meets' | 'below' | 'unknown' | 'not_required'
  student_stage: string | null
}

export interface SourceCard {
  slug: string
  title: string | null
  url: string
  kind: string
  source: string | null
  verification_status: string
  verified_fields: string[]
  freshness: Freshness
}

export interface NextAction {
  type: string
  career?: string
  typical_min_stage?: string
  opportunity?: string
  route_kind?: string
  url?: string
  fact?: string
  question_id?: string
}

export interface Recommendation {
  slug: string
  family: string
  kind: 'match' | 'explore'
  /** Keyword-match points. Never shown: not a probability or a measure of ability. */
  points: number | null
  match_level: 'strong' | 'moderate' | 'weak' | null
  reasons: Reason[]
  stage: StageInfo
  unknowns: string[]
  career: { slug: string; family: string; title: string | null; description: string | null; entry_notes: string | null }
  routes: { kind: string; title: string | null; min_stage: string | null; opportunity: SourceCard | null }[]
  sources: SourceCard[]
  next_actions: NextAction[]
  flags: string[]
  language_fallback: boolean
}

export interface Run {
  id: string
  ranking_version: string
  status: 'ok' | 'no_matches' | 'insufficient_profile'
  created_at: string
  families: string[]
  profile_summary: {
    terms?: { field: string; text: string; basis: string }[]
    education_stage?: string | null
    hypotheses_ignored?: number
    unmatched_terms?: { field: string; text: string }[]
  }
  missing: { field: string; question_id: string | null }[]
  items: Recommendation[]
  notes: string[]
}
