import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it } from 'vitest'
import { consentStatus, loginAs, mockApi, question, renderApp, session } from '../../test/utils'

const interests = question({
  id: 'q_interests',
  field_key: 'interests',
  kind: 'list_text',
  prompt: 'What do you enjoy doing?',
  options: [],
})

const result = (over: Record<string, unknown> = {}) => ({
  outcome: 'recorded',
  corrected: false,
  interpreted_by: 'student',
  message: null,
  session: session({ question: interests, progress: { answered: 1, total: 11 } }),
  ...over,
})

beforeEach(() => loginAs())

const base = () => ({
  'GET /consents/me': { body: consentStatus() },
  'POST /interview/sessions': { body: session() },
})

it('shows the question, why we ask, and progress, and focuses the question', async () => {
  mockApi(base())
  await renderApp('/interview')
  const heading = await screen.findByRole('heading', { name: 'Which class or course are you in now?' })
  expect(heading).toHaveFocus()
  expect(screen.getByText(/Why we ask: So we only suggest courses that fit\./)).toBeInTheDocument()
  expect(screen.getByText('0 of 11 questions')).toBeInTheDocument()
  expect(screen.getByRole('progressbar')).toHaveAttribute('max', '11')
})

it('starts the session in the UI language', async () => {
  const api = mockApi(base())
  await renderApp('/interview', 'ta')
  await screen.findByRole('heading', { level: 2 })
  expect(api.calls.find((c) => c.path === '/interview/sessions')?.body).toEqual({ language: 'ta' })
})

it('tapping an option sends a structured value and shows the next question', async () => {
  const api = mockApi({
    ...base(),
    'POST /interview/sessions/s1/answers': { body: result() },
  })
  await renderApp('/interview')
  await userEvent.click(await screen.findByRole('button', { name: 'Class 10' }))
  expect(await screen.findByText('What do you enjoy doing?')).toBeInTheDocument()
  expect(api.calls.find((c) => c.path.endsWith('/answers'))?.body).toEqual({
    question_id: 'q_education_stage',
    kind: 'value',
    value: 'class_10',
  })
  expect(screen.getByText('1 of 11 questions')).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'What do you enjoy doing?' })).toHaveFocus()
})

it('free text on a choice question is sent as text for interpretation', async () => {
  const api = mockApi({ ...base(), 'POST /interview/sessions/s1/answers': { body: result() } })
  await renderApp('/interview')
  await userEvent.click(await screen.findByText('Or type in your own words'))
  await userEvent.type(screen.getByLabelText('Your answer'), 'I study in tenth')
  await userEvent.click(screen.getByRole('button', { name: 'Send' }))
  await screen.findByText('What do you enjoy doing?')
  expect(api.calls.find((c) => c.path.endsWith('/answers'))?.body).toEqual({
    question_id: 'q_education_stage',
    kind: 'text',
    text: 'I study in tenth',
  })
})

it('"I don\'t know" and "Skip" send their own answer kinds', async () => {
  const api = mockApi({ ...base(), 'POST /interview/sessions/s1/answers': { body: result() } })
  await renderApp('/interview')
  await userEvent.click(await screen.findByRole('button', { name: "I don't know" }))
  await screen.findByText('What do you enjoy doing?')
  await userEvent.click(screen.getByRole('button', { name: 'Skip for now' }))
  await waitFor(() => expect(api.count('POST /interview/sessions/s1/answers')).toBe(2))
  const kinds = api.calls.filter((c) => c.path.endsWith('/answers')).map((c) => (c.body as { kind: string }).kind)
  expect(kinds).toEqual(['unknown', 'skip'])
})

it('an unclear answer shows the clarification and keeps the same question', async () => {
  mockApi({
    ...base(),
    'POST /interview/sessions/s1/answers': {
      body: result({
        outcome: 'needs_clarification',
        message: 'I could not tell which option you mean. Please choose one.',
        session: session(),
      }),
    },
  })
  await renderApp('/interview')
  await userEvent.click(await screen.findByText('Or type in your own words'))
  await userEvent.type(screen.getByLabelText('Your answer'), 'maybe both')
  await userEvent.click(screen.getByRole('button', { name: 'Send' }))
  expect(await screen.findByText(/Please choose one/)).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Which class or course are you in now?' })).toBeInTheDocument()
})

it('list questions: empty text is rejected locally; text is sent otherwise', async () => {
  const api = mockApi({
    'GET /consents/me': { body: consentStatus() },
    'POST /interview/sessions': { body: session({ question: interests }) },
    'POST /interview/sessions/s1/answers': { body: result({ session: session({ status: 'completed', question: null }) }) },
  })
  await renderApp('/interview')
  await userEvent.click(await screen.findByRole('button', { name: 'Send' }))
  expect(screen.getByText('Please enter an answer.')).toBeInTheDocument()
  expect(api.count('POST /interview/sessions/s1/answers')).toBe(0)
  await userEvent.type(screen.getByLabelText('Your answer'), 'farming, drawing')
  await userEvent.click(screen.getByRole('button', { name: 'Send' }))
  expect(await screen.findByRole('heading', { name: 'Thank you!' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'See my profile' })).toHaveAttribute('href', '/profile')
})

it('number question: digits are sent as a number, and out-of-range is rejected locally', async () => {
  const hours = question({ id: 'q_weekly_learning_hours', field_key: 'weekly_learning_hours', kind: 'number', prompt: 'Hours?', options: [], min_value: 0, max_value: 70 })
  const api = mockApi({
    'GET /consents/me': { body: consentStatus() },
    'POST /interview/sessions': { body: session({ question: hours }) },
    'POST /interview/sessions/s1/answers': { body: result() },
  })
  await renderApp('/interview')
  const input = await screen.findByLabelText('Your answer (a number)')
  await userEvent.type(input, '99')
  await userEvent.click(screen.getByRole('button', { name: 'Send' }))
  expect(screen.getByText('Enter a whole number from 0 to 70.')).toBeInTheDocument()
  expect(api.count('POST /interview/sessions/s1/answers')).toBe(0)
  await userEvent.clear(input)
  await userEvent.type(input, '6')
  await userEvent.click(screen.getByRole('button', { name: 'Send' }))
  await screen.findByText('What do you enjoy doing?')
  expect(api.calls.find((c) => c.path.endsWith('/answers'))?.body).toMatchObject({ kind: 'value', value: 6 })
})

it('a connection failure keeps what the student typed and lets them resend', async () => {
  let fail = true
  const api = mockApi({
    'GET /consents/me': { body: consentStatus() },
    'POST /interview/sessions': { body: session({ question: interests }) },
    'POST /interview/sessions/s1/answers': () => {
      if (fail) throw new TypeError('offline')
      return { body: result({ session: session({ status: 'completed', question: null }) }) }
    },
  })
  await renderApp('/interview')
  await userEvent.type(await screen.findByLabelText('Your answer'), 'farming')
  await userEvent.click(screen.getByRole('button', { name: 'Send' }))
  expect(await screen.findByText(/Could not reach the server/)).toBeInTheDocument()
  expect(screen.getByLabelText('Your answer')).toHaveValue('farming')
  expect(api.count('POST /interview/sessions/s1/answers')).toBe(1) // not retried behind the scenes
  fail = false
  await userEvent.click(screen.getByRole('button', { name: 'Send' }))
  expect(await screen.findByRole('heading', { name: 'Thank you!' })).toBeInTheDocument()
})

it('if the session cannot be started, shows an error with a retry button', async () => {
  let fail = true
  mockApi({
    'GET /consents/me': { body: consentStatus() },
    'POST /interview/sessions': () => {
      if (fail) throw new TypeError('offline')
      return { body: session() }
    },
  })
  await renderApp('/interview')
  expect(await screen.findByText(/Could not reach the server/)).toBeInTheDocument()
  fail = false
  await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByText('Which class or course are you in now?')).toBeInTheDocument()
})

it('an already finished interview shows the thank-you screen', async () => {
  mockApi({
    'GET /consents/me': { body: consentStatus() },
    'POST /interview/sessions': { body: session({ status: 'completed', question: null }) },
  })
  await renderApp('/interview')
  expect(await screen.findByRole('heading', { name: 'Thank you!' })).toBeInTheDocument()
})
