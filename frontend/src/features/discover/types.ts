// Shapes of the backend responses (backend/app/modules/{sources,catalog,retrieval}/schemas.py).

export type Freshness = 'fresh' | 'stale' | 'expired' | 'unverified'

export interface SourceBrief {
  id: string
  name: string
  publisher: string
  base_url: string
}

export interface Verification {
  status: 'unverified' | 'verified'
  verified_fields: string[]
  verified_at: string | null
  verified_by: string | null
  human_reviewed: boolean
  evidence: Record<string, string>[]
}

export interface SearchHit {
  type: 'career' | 'opportunity'
  id: string
  title: string | null
  summary: string | null
  match_type: 'exact' | 'partial' | 'browse'
  score: number
  group: string
  url: string | null
  source: SourceBrief | null
  freshness: Freshness | null
  verification: Verification | null
  eligibility_known: boolean | null
  flags: string[]
  language_fallback: boolean
}

export interface SearchResponse {
  query: string | null
  language: string
  search_mode: 'keyword'
  status: 'ok' | 'partial_only' | 'insufficient_evidence'
  message: string | null
  results: SearchHit[]
}

export interface CareerBrief {
  slug: string
  family: string
  title: string | null
}

export interface OpportunityBrief {
  slug: string
  kind: string
  title: string | null
  url: string
}

export interface CareerRoute {
  kind: string
  title: string | null
  min_stage: string | null
  opportunity: OpportunityBrief | null
}

export interface Career extends CareerBrief {
  description: string | null
  activities: string[]
  skills: string[]
  entry: { typical_min_stage?: string | null; notes?: string | null }
  routes: CareerRoute[]
  related: CareerBrief[]
  learning_resources: OpportunityBrief[]
  verification_status: string
  human_reviewed: boolean
  localization_status: string
  language: string
  language_fallback: boolean
}

export interface Benefit {
  text: string | null
  amount_inr: number | null
  period: 'month' | 'year' | 'one_time' | null
}

export interface PublishedEligibility {
  education_stages?: string[] | null
  min_age?: number | null
  max_age?: number | null
  max_family_income_inr_per_year?: number | null
  other_criteria?: (string | null)[]
  text?: string | null
}

export interface Opportunity extends OpportunityBrief {
  summary: string | null
  provider: string
  source: SourceBrief
  scope: { level?: 'national' | 'state'; states?: string[] }
  eligibility: PublishedEligibility | null
  required_documents: string[]
  application_deadline: string | null
  expires_on: string | null
  benefits: Benefit[]
  verification: Verification
  freshness: Freshness
  flags: string[]
  language: string
  language_fallback: boolean
}

export interface SearchParams {
  q?: string
  type?: string
  kind?: string
  state?: string
  stage?: string
}
