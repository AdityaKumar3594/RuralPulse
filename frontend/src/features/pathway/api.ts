import { apiGet, apiPost, apiPut, type ApiGetOptions } from '../../api/client'
import type { Plan, StepStatus } from './types'

export const listPlans = (language: string, o?: ApiGetOptions) =>
  apiGet<Plan[]>(`/pathways?language=${encodeURIComponent(language)}`, o)

export const getPlan = (id: string, language: string, o?: ApiGetOptions) =>
  apiGet<Plan>(`/pathways/${encodeURIComponent(id)}?language=${encodeURIComponent(language)}`, o)

export const createPlan = (career: string, language: string) => apiPost<Plan>('/pathways', { career, language })

export const setStepStatus = (planId: string, stepId: string, status: StepStatus, language: string) =>
  apiPut<Plan>(
    `/pathways/${encodeURIComponent(planId)}/steps/${encodeURIComponent(stepId)}?language=${encodeURIComponent(language)}`,
    { status },
  )
