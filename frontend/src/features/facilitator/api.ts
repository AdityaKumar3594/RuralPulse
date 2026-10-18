import { apiGet, apiPost, apiPut, type ApiGetOptions } from '../../api/client'
import type { Application, ExternalStatus } from '../applications/types'
import type {
  Endorsement,
  HelpRequest,
  Plan,
  RecRun,
  ReviewDecision,
  SearchHit,
  StepStatus,
  StudentProfile,
  StudentSummary,
} from './types'

const id = encodeURIComponent
const lang = (l: string) => `language=${l === 'ta' ? 'ta' : 'en'}`
const base = (sid: string) => `/facilitator/students/${id(sid)}`

export const listStudents = (o?: ApiGetOptions) => apiGet<StudentSummary[]>('/facilitator/students', o)
export const listHelpRequests = (o?: ApiGetOptions) => apiGet<HelpRequest[]>('/facilitator/help-requests', o)
export const resolveHelp = (requestId: string) =>
  apiPost<HelpRequest>(`/facilitator/help-requests/${id(requestId)}/resolve`)

export const getProfile = (sid: string, o?: ApiGetOptions) => apiGet<StudentProfile>(`${base(sid)}/profile`, o)

export interface ObservationBody {
  key: string
  value: unknown
  provenance: 'observed' | 'hypothesis'
  basis: string
  verified: boolean
}
export const addObservation = (sid: string, body: ObservationBody) =>
  apiPost<unknown>(`${base(sid)}/observations`, body)

export interface AssistedBody {
  key: string
  value?: unknown
  unknown?: boolean
}
export const addAssistedAnswer = (sid: string, body: AssistedBody) =>
  apiPost<unknown>(`${base(sid)}/assisted-answers`, body)

export const getRecommendations = (sid: string, language: string, o?: ApiGetOptions) =>
  apiGet<RecRun>(`${base(sid)}/recommendations/latest?${lang(language)}`, o)
export const reviewRecommendation = (
  sid: string,
  body: { run_id: string; career: string; decision: ReviewDecision; note: string | null },
) => apiPost<unknown>(`${base(sid)}/recommendations/review`, body)

export const endorse = (sid: string, opportunity: string, note: string | null) =>
  apiPost<Endorsement>(`${base(sid)}/endorsements`, { opportunity, note })
export const searchOpportunities = (q: string, language: string, o?: ApiGetOptions) =>
  apiGet<{ results: SearchHit[] }>(
    `/search?type=opportunity&limit=10&${lang(language)}${q.trim() ? `&q=${encodeURIComponent(q.trim())}` : ''}`,
    o,
  )

export const getPathways = (sid: string, language: string, o?: ApiGetOptions) =>
  apiGet<Plan[]>(`${base(sid)}/pathways?${lang(language)}`, o)
export const setStep = (sid: string, planId: string, stepId: string, status: StepStatus, language: string) =>
  apiPut<Plan>(`${base(sid)}/pathways/${id(planId)}/steps/${id(stepId)}?${lang(language)}`, { status })

export const getApplications = (sid: string, language: string, o?: ApiGetOptions) =>
  apiGet<Application[]>(`${base(sid)}/applications?${lang(language)}`, o)
export const confirmApplication = (appId: string, language: string, status: Exclude<ExternalStatus, 'unknown'>, note: string | null) =>
  apiPost<Application>(`/facilitator/applications/${id(appId)}/confirm?${lang(language)}`, { status, note })
