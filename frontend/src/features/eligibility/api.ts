import { apiPost, type ApiGetOptions } from '../../api/client'
import type { Evaluation } from './types'

export const evaluate = (opportunity: string, language: string, o?: ApiGetOptions) =>
  apiPost<Evaluation>('/eligibility/evaluations', { opportunity, language }, o)
