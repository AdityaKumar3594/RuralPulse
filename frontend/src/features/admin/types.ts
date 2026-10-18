export type VerifiedField =
  | 'url'
  | 'provider'
  | 'existence'
  | 'eligibility'
  | 'benefit'
  | 'deadline'
  | 'documents'
  | 'scope'

export const VERIFIED_FIELDS: VerifiedField[] = [
  'url',
  'provider',
  'existence',
  'eligibility',
  'benefit',
  'deadline',
  'documents',
  'scope',
]

export type StaffRole = 'facilitator' | 'partner'

export interface AdminUser {
  id: string
  role: string
  display_name: string
  phone: string
  is_active: boolean
}

export interface Assignment {
  id: string
  facilitator_id: string
  student_id: string
  created_at: string
  ended_at: string | null
}

export type ProviderStatus = 'pending' | 'approved' | 'suspended'

export interface Provider {
  id: string
  name: string
  kind: string
  website: string
  description: string | null
  status: ProviderStatus
  created_at: string
}

export const SUBMISSION_STATUSES = [
  'submitted',
  'changes_requested',
  'approved',
  'rejected',
  'withdrawn',
  'draft',
] as const
export type SubmissionStatus = (typeof SUBMISSION_STATUSES)[number]

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

export interface Evidence {
  url: string
  note: string
}

export type Decision = 'approve' | 'request_changes' | 'reject'

export interface DecisionResult {
  submission: Submission
  published_slug: string | null
  verification_status: string | null
  stripped_claims: string[]
}
