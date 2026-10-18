import { apiGet, apiPost, apiPut, type ApiGetOptions } from '../../api/client'
import type { Application, ExternalStatus, InternalStatus } from './types'

const lang = (l: string) => `language=${l === 'ta' ? 'ta' : 'en'}`

export const listApplications = (language: string, o?: ApiGetOptions) =>
  apiGet<Application[]>(`/applications?${lang(language)}`, o)
export const getApplication = (id: string, language: string, o?: ApiGetOptions) =>
  apiGet<Application>(`/applications/${encodeURIComponent(id)}?${lang(language)}`, o)
export const saveApplication = (opportunity: string, language: string) =>
  apiPost<Application>('/applications', { opportunity, language: language === 'ta' ? 'ta' : 'en' })

export interface UpdateBody {
  internal_status?: InternalStatus
  note?: string
  documents?: Record<string, boolean>
  reported_external_status?: ExternalStatus
}
export const updateApplication = (id: string, language: string, body: UpdateBody) =>
  apiPut<Application>(`/applications/${encodeURIComponent(id)}?${lang(language)}`, body)
export const askApplicationHelp = (id: string, message: string | null) =>
  apiPost<unknown>(`/applications/${encodeURIComponent(id)}/help`, { message })
