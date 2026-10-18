import { apiPost } from '../../api/client'
import type { Run } from './types'

export const createRun = (language: string, limit = 5, o?: { signal?: AbortSignal }) =>
  apiPost<Run>('/recommendations', { language, limit }, o)
