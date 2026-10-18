import { apiPost } from '../../api/client'
import type { Freshness } from './types'

export type ExplainRef =
  | { kind: 'recommendation'; run_id: string; career: string }
  | { kind: 'eligibility'; evaluation_id: string }
  | { kind: 'pathway'; plan_id: string }

export type ExplainRequest = ExplainRef & { language?: 'ta' | 'en' }

export type ExplanationStatus = 'ELIGIBLE' | 'INELIGIBLE' | 'UNKNOWN' | 'NEEDS_REVIEW' | 'NOT_APPLICABLE'

export interface Explanation {
  id: string
  kind: string
  language: string
  source: 'ai' | 'template'
  fallback_reason: string | null
  model: string | null
  cached: boolean
  explanation: {
    headline: string
    why: string[]
    requirements: string[]
    eligibility_status: ExplanationStatus
    freshness_note: string
    missing_information: string[]
    next_action: string
  }
  sources: { title?: string; url?: string; freshness?: Freshness }[]
  created_at: string
}

export const explain = (body: ExplainRequest) => apiPost<Explanation>('/explanations', body)
