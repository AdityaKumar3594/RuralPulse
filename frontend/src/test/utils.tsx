import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { vi } from 'vitest'
import { AuthProvider } from '../auth/AuthContext'
import i18n from '../i18n'
import { AppRoutes } from '../routes'

export interface Call {
  method: string
  path: string
  query: string
  body: unknown
  headers: Headers
}

type Reply = { status?: number; body?: unknown }
type Handler = Reply | ((call: Call) => Reply | Promise<Reply>) | 'network-error'

/** Stubs fetch. Keys look like "POST /interview/sessions"; query strings are ignored for matching. */
export function mockApi(handlers: Record<string, Handler>) {
  const calls: Call[] = []
  const impl = async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const url = new URL(String(input), 'http://localhost')
    const method = init.method ?? 'GET'
    const path = url.pathname.replace(/^\/api/, '')
    const call: Call = {
      method,
      path,
      query: url.search,
      body: init.body ? JSON.parse(String(init.body)) : undefined,
      headers: new Headers(init.headers),
    }
    calls.push(call)
    const handler = handlers[`${method} ${path}`]
    if (!handler) throw new Error(`unmocked request: ${method} ${path}`)
    if (handler === 'network-error') throw new TypeError('offline')
    const reply = typeof handler === 'function' ? await handler(call) : handler
    if (reply.status === 204) return new Response(null, { status: 204 })
    return new Response(JSON.stringify(reply.body ?? {}), { status: reply.status ?? 200 })
  }
  const fetchMock = vi.fn(impl)
  vi.stubGlobal('fetch', fetchMock)
  return { calls, fetchMock, count: (key: string) => calls.filter((c) => `${c.method} ${c.path}` === key).length }
}

export const USER = { id: 'u1', role: 'student', display_name: 'Asha', preferred_language: 'en' }

export function loginAs(user = USER) {
  sessionStorage.setItem('Ruralpulse.token', 'test-token')
  sessionStorage.setItem('Ruralpulse.user', JSON.stringify(user))
}

export async function renderApp(route: string, lang = 'en') {
  await i18n.changeLanguage(lang)
  return render(
    <MemoryRouter initialEntries={[route]}>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </MemoryRouter>,
  )
}

export const consentStatus = (over: Record<string, unknown> = {}) => ({
  required_given_by: 'self',
  policy_version: 'draft',
  active: { purpose: 'data_processing', policy_version: 'draft', given_by: 'self', verification: 'self_declared', granted_at: 'x' },
  ...over,
})

export const question = (over: Record<string, unknown> = {}) => ({
  id: 'q_education_stage',
  field_key: 'education_stage',
  kind: 'single_choice',
  prompt: 'Which class or course are you in now?',
  why: 'So we only suggest courses that fit.',
  options: [
    { value: 'class_9', label: 'Class 9' },
    { value: 'class_10', label: 'Class 10' },
  ],
  ...over,
})

export const session = (over: Record<string, unknown> = {}) => ({
  id: 's1',
  status: 'active',
  language: 'en',
  question: question(),
  progress: { answered: 0, total: 11 },
  ...over,
})
