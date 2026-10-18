import { apiGet, apiPost, apiPut, type ApiGetOptions } from './client'
import type {
  AnswerPayload,
  AnswerResult,
  ConsentStatus,
  InterviewSession,
  Profile,
  Question,
  TokenResponse,
} from './types'

export const register = (body: {
  display_name: string
  phone: string
  pin: string
  date_of_birth: string
  preferred_language: string
}) => apiPost<TokenResponse>('/auth/register', body)

export const login = (body: { phone: string; pin: string }) => apiPost<TokenResponse>('/auth/login', body)

export const getConsentStatus = (o?: ApiGetOptions) => apiGet<ConsentStatus>('/consents/me', o)

export const grantConsent = (body: {
  given_by: 'self' | 'guardian'
  guardian_name?: string
  guardian_phone?: string
}) => apiPost<unknown>('/consents', body)

export const withdrawConsent = () => apiPost<void>('/consents/withdraw')

export const startInterview = (language: string) =>
  apiPost<InterviewSession>('/interview/sessions', { language })

export const answerQuestion = (sessionId: string, payload: AnswerPayload) =>
  apiPost<AnswerResult>(`/interview/sessions/${sessionId}/answers`, payload)

export const getQuestions = (language: string, o?: ApiGetOptions) =>
  apiGet<Question[]>(`/interview/questions?language=${encodeURIComponent(language)}`, o)

export const getProfile = (o?: ApiGetOptions) => apiGet<Profile>('/profile', o)

export const updateProfileField = (key: string, body: { value: unknown } | { unknown: true }) =>
  apiPut<Profile>(`/profile/fields/${encodeURIComponent(key)}`, body)
