import { apiGet, apiPost, apiRequest, type ApiGetOptions } from '../../api/client'
import type {
  AdminUser,
  Assignment,
  Decision,
  DecisionResult,
  Evidence,
  Provider,
  StaffRole,
  Submission,
  VerifiedField,
} from './types'

function qs(params: Record<string, string | undefined>): string {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v) sp.set(k, v)
  const s = sp.toString()
  return s ? `?${s}` : ''
}

export const listUsers = (role: string | undefined, o?: ApiGetOptions) =>
  apiGet<AdminUser[]>(`/admin/users${qs({ role })}`, o)

export const createStaff = (body: { role: StaffRole; phone: string; pin: string; display_name: string }) =>
  apiPost<AdminUser>('/admin/users', body)

export const listAssignments = (o?: ApiGetOptions) => apiGet<Assignment[]>('/admin/assignments', o)

export const createAssignment = (facilitator_id: string, student_id: string) =>
  apiPost<Assignment>('/admin/assignments', { facilitator_id, student_id })

// The shared client's method type has no DELETE, but it hands the method straight to fetch.
export const endAssignment = (id: string) =>
  apiRequest<Assignment>(`/admin/assignments/${encodeURIComponent(id)}`, { method: 'DELETE' as 'POST' })

export const listProviders = (status: string | undefined, o?: ApiGetOptions) =>
  apiGet<Provider[]>(`/admin/providers${qs({ status_: status })}`, o)

export const setProvider = (id: string, action: 'approve' | 'suspend') =>
  apiPost<Provider>(`/admin/providers/${encodeURIComponent(id)}/${action}`)

export const listSubmissions = (status: string, o?: ApiGetOptions) =>
  apiGet<Submission[]>(`/admin/submissions${qs({ status_: status })}`, o)

export const decide = (
  id: string,
  decision: Decision,
  notes: string,
  verified_fields: VerifiedField[],
  evidence: Evidence[],
) =>
  apiPost<DecisionResult>(`/admin/submissions/${encodeURIComponent(id)}/decision`, {
    decision,
    notes: notes || null,
    verification: { verified_fields, evidence },
  })

export const reverify = (slug: string, verified_fields: VerifiedField[], evidence: Evidence[]) =>
  apiPost<void>(`/admin/opportunities/${encodeURIComponent(slug)}/reverify`, { verified_fields, evidence })

export const withdrawOpportunity = (slug: string) =>
  apiPost<void>(`/admin/opportunities/${encodeURIComponent(slug)}/withdraw`)
