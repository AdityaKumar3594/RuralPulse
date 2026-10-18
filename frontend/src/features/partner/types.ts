export type ProviderStatus = 'pending' | 'approved' | 'suspended'
export const PROVIDER_KINDS = ['ngo', 'employer', 'training_provider', 'mentor', 'government'] as const
export type ProviderKind = (typeof PROVIDER_KINDS)[number]

export interface Provider {
  id: string
  name: string
  kind: string
  website: string
  description: string | null
  status: ProviderStatus
  created_at: string
}

export const OPPORTUNITY_KINDS = [
  'platform',
  'course',
  'scholarship',
  'scheme',
  'apprenticeship',
  'internship',
  'exam',
  'training_program',
  'mentorship',
  'job',
] as const

export const EDUCATION_STAGES = [
  'class_9',
  'class_10',
  'class_11',
  'class_12',
  'iti_or_diploma',
  'undergraduate',
  'graduate',
  'not_in_school',
] as const

export type Period = 'month' | 'year' | 'one_time'

export interface Submission {
  id: string
  provider_id: string
  status: string
  payload: Record<string, unknown>
  replaces_slug: string | null
  review_notes: string | null
  published_slug: string | null
  revision: number
  created_at: string
  updated_at: string
}

export interface Localized {
  en: string
  ta?: string
}

export interface SubmissionPayload {
  kind: string
  title: Localized
  summary: Localized
  url: string
  keywords: string[]
  scope: { level: 'national' | 'state'; states: string[] }
  eligibility: {
    education_stages: string[] | null
    min_age: number | null
    max_age: number | null
    max_family_income_inr_per_year: number | null
    text: Localized | null
  } | null
  required_documents: string[]
  application_deadline: string | null
  expires_on: string | null
  benefits: { text: Localized; amount_inr: number | null; period: Period | null }[]
}

export type ExternalStatus = 'submitted' | 'under_review' | 'accepted' | 'rejected'
export const EXTERNAL_STATUSES: ExternalStatus[] = ['submitted', 'under_review', 'accepted', 'rejected']

export interface Stats {
  opportunity: string
  by_internal_status: Record<string, number>
  by_external_status: Record<string, number>
}
