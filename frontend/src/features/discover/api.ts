import { apiGet, type ApiGetOptions } from '../../api/client'
import type { Career, CareerBrief, Opportunity, SearchParams, SearchResponse } from './types'

function query(params: Record<string, string | undefined>): string {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v) sp.set(k, v)
  const s = sp.toString()
  return s ? `?${s}` : ''
}

export const search = (params: SearchParams, language: string, o?: ApiGetOptions) =>
  apiGet<SearchResponse>(`/search${query({ ...params, language })}`, o)

export const listCareers = (family: string | undefined, language: string, o?: ApiGetOptions) =>
  apiGet<CareerBrief[]>(`/careers${query({ family, language })}`, o)

export const getCareer = (slug: string, language: string, o?: ApiGetOptions) =>
  apiGet<Career>(`/careers/${encodeURIComponent(slug)}${query({ language })}`, o)

export const getOpportunity = (slug: string, language: string, o?: ApiGetOptions) =>
  apiGet<Opportunity>(`/opportunities/${encodeURIComponent(slug)}${query({ language })}`, o)
