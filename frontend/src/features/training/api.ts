import { apiGet, apiPost, apiPut, type ApiGetOptions } from '../../api/client'
import type { FacilitatorModule, ModuleBody, TrainingModule } from './types'

const id = encodeURIComponent

export const listModules = (o?: ApiGetOptions) => apiGet<TrainingModule[]>('/modules', o)
export const getModule = (moduleId: string, o?: ApiGetOptions) => apiGet<TrainingModule>(`/modules/${id(moduleId)}`, o)
export const enroll = (moduleId: string) => apiPost<TrainingModule>(`/modules/${id(moduleId)}/enroll`)
export const setLessonDone = (moduleId: string, index: number, done: boolean) =>
  apiPut<TrainingModule>(`/modules/${id(moduleId)}/lessons/${index}`, { done })

export const listMine = (o?: ApiGetOptions) => apiGet<FacilitatorModule[]>('/facilitator/modules', o)
export const createModule = (body: ModuleBody) => apiPost<TrainingModule>('/facilitator/modules', body)
export const updateModule = (moduleId: string, body: ModuleBody) =>
  apiPut<TrainingModule>(`/facilitator/modules/${id(moduleId)}`, body)
export const publishModule = (moduleId: string) => apiPost<TrainingModule>(`/facilitator/modules/${id(moduleId)}/publish`)
export const withdrawModule = (moduleId: string) => apiPost<TrainingModule>(`/facilitator/modules/${id(moduleId)}/withdraw`)
