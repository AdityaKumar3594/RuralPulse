import { apiGet, apiPost, apiPut, type ApiGetOptions } from '../../api/client'

export interface ConsentOut {
  purpose: string
  policy_version: string
  given_by: 'self' | 'guardian' | string
  verification: string
  granted_at: string
}

export interface ConsentStatus {
  required_given_by: 'self' | 'guardian'
  policy_version: string
  active: ConsentOut | null
}

export interface MyFacilitator {
  id: string
  display_name: string
  since: string
}

export interface Endorsement {
  id: string
  opportunity_slug: string
  note: string | null
  status: 'suggested' | 'seen' | 'dismissed' | string
  created_at: string
}

export type HelpTopic = 'general' | 'interview' | 'pathway' | 'application'

export interface ShareBody {
  given_by: 'self' | 'guardian'
  guardian_name?: string
  guardian_phone?: string
}

export const getSharing = (o?: ApiGetOptions) => apiGet<ConsentStatus>('/consents/facilitator-access', o)
export const grantSharing = (body: ShareBody) => apiPost<ConsentOut>('/consents/facilitator-access', body)
export const withdrawSharing = () => apiPost<void>('/consents/facilitator-access/withdraw')
export const getMyFacilitators = (o?: ApiGetOptions) => apiGet<MyFacilitator[]>('/me/facilitators', o)
export const getMyEndorsements = (o?: ApiGetOptions) => apiGet<Endorsement[]>('/me/endorsements', o)
export const setEndorsementStatus = (id: string, status: 'seen' | 'dismissed') =>
  apiPut<Endorsement>(`/me/endorsements/${encodeURIComponent(id)}`, { status })
export const askForHelp = (topic: HelpTopic, message: string | null) =>
  apiPost<unknown>('/me/help-requests', { topic, message })
