import { apiGet, apiPost, apiPut, type ApiGetOptions } from '../../api/client'
import type { ExternalStatus, Provider, Stats, Submission, SubmissionPayload } from './types'

export const getProvider = (o?: ApiGetOptions) => apiGet<Provider>('/partner/provider', o)
export const createProvider = (body: { name: string; kind: string; website: string; description: string | null }) =>
  apiPost<Provider>('/partner/provider', body)
export const updateProvider = (body: Partial<{ name: string; kind: string; website: string; description: string | null }>) =>
  apiPut<Provider>('/partner/provider', body)

export const listSubmissions = (o?: ApiGetOptions) => apiGet<Submission[]>('/partner/submissions', o)
export const getSubmission = (id: string, o?: ApiGetOptions) =>
  apiGet<Submission>(`/partner/submissions/${encodeURIComponent(id)}`, o)
export const createSubmission = (p: SubmissionPayload) => apiPost<Submission>('/partner/submissions', p)
export const updateSubmission = (id: string, p: SubmissionPayload) =>
  apiPut<Submission>(`/partner/submissions/${encodeURIComponent(id)}`, p)
export const submitSubmission = (id: string) =>
  apiPost<Submission>(`/partner/submissions/${encodeURIComponent(id)}/submit`)
export const withdrawSubmission = (id: string) =>
  apiPost<Submission>(`/partner/submissions/${encodeURIComponent(id)}/withdraw`)
export const reviseSubmission = (id: string) =>
  apiPost<Submission>(`/partner/submissions/${encodeURIComponent(id)}/revise`)

export const confirmApplication = (reference_code: string, status: ExternalStatus, note: string | null) =>
  apiPost<{ opportunity: string; external_status: string }>('/partner/applications/confirm', {
    reference_code,
    status,
    note,
  })

export const getStats = (slug: string, o?: ApiGetOptions) =>
  apiGet<Stats>(`/partner/opportunities/${encodeURIComponent(slug)}/stats`, o)
