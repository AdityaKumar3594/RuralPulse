import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it } from 'vitest'
import { consentStatus, loginAs, mockApi, question, renderApp } from '../../test/utils'

const entry = (over: Record<string, unknown>) => ({
  id: crypto.randomUUID(),
  provenance: 'reported',
  value: null,
  verification: 'unverified',
  source: 'student_form',
  basis: null,
  created_at: 'x',
  ...over,
})
const field = (key: string, entries: unknown[] = [], over: Record<string, unknown> = {}) => ({
  key,
  description: `desc ${key}`,
  state: entries.length ? 'established' : 'unknown',
  conflict: false,
  entries,
  ...over,
})

const questions = [
  question(),
  question({ id: 'q_interests', field_key: 'interests', kind: 'list_text', prompt: 'What do you enjoy?', options: [] }),
  question({ id: 'q_skills', field_key: 'skills', kind: 'list_text', prompt: 'What can you do?', options: [] }),
]

const profile = {
  fields: [
    field('education_stage', [entry({ value: 'class_10', verification: 'verified' })], { conflict: true }),
    field('interests', [entry({ value: ['farming', 'drawing'] })]),
    field('skills', [entry({ provenance: 'hypothesis', value: ['welding'], basis: 'Likes tools' })], {
      state: 'hypothesis_only',
    }),
    field('goals', [entry({ provenance: 'unknown' })], { state: 'unknown' }),
    field('district'),
  ],
}

const base = () => ({
  'GET /consents/me': { body: consentStatus() },
  'GET /profile': { body: profile },
  'GET /interview/questions': { body: questions },
})

beforeEach(() => loginAs())

it('shows each field with how we know it, using localised choice labels', async () => {
  const api = mockApi(base())
  await renderApp('/profile')
  const stage = (await screen.findByRole('heading', { name: 'Class or course' })).closest('li')!
  expect(within(stage).getByText('You told us')).toBeInTheDocument()
  expect(within(stage).getByText('Class 10')).toBeInTheDocument() // label, not "class_10"
  expect(within(stage).getByText(/Checked/)).toBeInTheDocument()
  expect(within(stage).getByText(/a teacher saw are different/)).toBeInTheDocument()
  expect(api.calls.find((c) => c.path === '/interview/questions')?.query).toBe('?language=en')

  const interests = screen.getByRole('heading', { name: 'Interests' }).closest('li')!
  expect(within(interests).getByText('farming, drawing')).toBeInTheDocument()
})

it('keeps hypotheses, unknowns and missing data clearly distinct', async () => {
  mockApi(base())
  await renderApp('/profile')
  const skills = (await screen.findByRole('heading', { name: 'Skills' })).closest('li')!
  expect(within(skills).getByText('A suggestion, not confirmed')).toBeInTheDocument()
  const goals = screen.getByRole('heading', { name: 'Goals' }).closest('li')!
  expect(within(goals).getByText('You said you do not know')).toBeInTheDocument()
  const district = screen.getByRole('heading', { name: 'District' }).closest('li')!
  expect(within(district).getByText('Not told yet')).toBeInTheDocument()
})

it('shows Tamil labels for field names', async () => {
  mockApi(base())
  await renderApp('/profile', 'ta')
  expect(await screen.findByRole('heading', { name: 'வகுப்பு அல்லது படிப்பு' })).toBeInTheDocument()
})

it('changing a list field saves the items as reported values', async () => {
  const api = mockApi({
    ...base(),
    'PUT /profile/fields/interests': { body: { fields: [field('interests', [entry({ value: ['farming', 'music'] })])] } },
  })
  await renderApp('/profile')
  await userEvent.click(await screen.findByRole('button', { name: 'Change: Interests' }))
  const box = screen.getByLabelText('Your answer')
  expect(box).toHaveValue('farming, drawing')
  await userEvent.clear(box)
  await userEvent.type(box, 'farming, music, music')
  expect(screen.queryByRole('button', { name: 'Skip for now' })).not.toBeInTheDocument() // no skip when editing
  await userEvent.click(screen.getByRole('button', { name: 'Save' }))
  expect(await screen.findByText('farming, music')).toBeInTheDocument()
  expect(api.calls.find((c) => c.method === 'PUT')?.body).toEqual({ value: ['farming', 'music'] })
})

it('changing a choice sends the value; "I don\'t know" sends unknown', async () => {
  const api = mockApi({
    ...base(),
    'PUT /profile/fields/education_stage': { body: profile },
  })
  await renderApp('/profile')
  await userEvent.click(await screen.findByRole('button', { name: 'Change: Class or course' }))
  expect(screen.queryByText('Or type in your own words')).not.toBeInTheDocument() // strict values only
  await userEvent.click(screen.getByRole('button', { name: 'Class 9' }))
  await userEvent.click(await screen.findByRole('button', { name: 'Change: Class or course' }))
  await userEvent.click(screen.getByRole('button', { name: "I don't know" }))
  const bodies = api.calls.filter((c) => c.method === 'PUT').map((c) => c.body)
  expect(bodies).toEqual([{ value: 'class_9' }, { unknown: true }])
})

it('a failed save shows the error and keeps the editor open', async () => {
  mockApi({ ...base(), 'PUT /profile/fields/interests': 'network-error' })
  await renderApp('/profile')
  await userEvent.click(await screen.findByRole('button', { name: 'Change: Interests' }))
  await userEvent.click(screen.getByRole('button', { name: 'Save' }))
  expect(await screen.findByText(/Could not reach the server/)).toBeInTheDocument()
  expect(screen.getByLabelText('Your answer')).toBeInTheDocument()
})

it('withdrawing consent needs a confirmation, then returns to the consent screen', async () => {
  let withdrawn = false
  const api = mockApi({
    ...base(),
    'GET /consents/me': () => ({ body: withdrawn ? consentStatus({ active: null }) : consentStatus() }),
    'POST /consents/withdraw': () => {
      withdrawn = true
      return { status: 204 }
    },
  })
  await renderApp('/profile')
  await userEvent.click(await screen.findByRole('button', { name: 'Take back my permission' }))
  expect(api.count('POST /consents/withdraw')).toBe(0) // not yet: asked to confirm first
  expect(screen.getByRole('alert')).toHaveTextContent(/Take back permission\?/)
  await userEvent.click(screen.getByRole('button', { name: 'Yes, take it back' }))
  expect(await screen.findByRole('heading', { name: 'Your permission' })).toBeInTheDocument()
  expect(api.count('POST /consents/withdraw')).toBe(1)
})

it('shows an error with retry when the profile cannot be loaded', async () => {
  let fail = true
  mockApi({
    ...base(),
    'GET /profile': () => {
      if (fail) throw new TypeError('offline')
      return { body: profile }
    },
  })
  await renderApp('/profile')
  expect(await screen.findByText(/Could not reach the server/)).toBeInTheDocument()
  fail = false
  await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByRole('heading', { name: 'Class or course' })).toBeInTheDocument()
})

it('income is edited as a plain number with the server\'s bounds, accepting digit separators', async () => {
  const income = question({
    id: 'q_annual_family_income',
    field_key: 'annual_family_income_inr',
    kind: 'number',
    prompt: 'What is your family income in a year?',
    options: [],
    min_value: 0,
    max_value: 100000000,
  })
  const api = mockApi({
    'GET /consents/me': { body: consentStatus() },
    'GET /profile': { body: { fields: [field('annual_family_income_inr')] } },
    'GET /interview/questions': { body: [income] },
    'PUT /profile/fields/annual_family_income_inr': { body: { fields: [field('annual_family_income_inr', [entry({ value: 350000 })])] } },
  })
  await renderApp('/profile')
  await userEvent.click(await screen.findByRole('button', { name: /Change: Family income per year/ }))
  const box = screen.getByLabelText('Your answer (a number)')
  await userEvent.type(box, 'three lakh')
  await userEvent.click(screen.getByRole('button', { name: 'Save' }))
  expect(screen.getByText('Enter a whole number from 0 to 100000000.')).toBeInTheDocument()
  expect(api.calls.some((c) => c.method === 'PUT')).toBe(false)
  await userEvent.clear(box)
  await userEvent.type(box, '3,50,000')
  await userEvent.click(screen.getByRole('button', { name: 'Save' }))
  expect(await screen.findByText('350000')).toBeInTheDocument()
  expect(api.calls.find((c) => c.method === 'PUT')?.body).toEqual({ value: 350000 })
})
