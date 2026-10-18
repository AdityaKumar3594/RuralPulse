import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it } from 'vitest'
import { consentStatus, loginAs, mockApi, question, renderApp } from '../../test/utils'
import { opportunity } from '../discover/testData'

const evaluation = (over: Record<string, unknown> = {}) => ({
  id: 'e1',
  opportunity: { slug: 'merit-scholarship', kind: 'scholarship', title: 'Merit Scholarship', url: 'https://scholarships.gov.in/merit' },
  outcome: 'ELIGIBLE',
  reasons: [],
  checks: [],
  missing: [],
  flags: [],
  facts_used: {},
  rules_version: '2026-10-1',
  opportunity_fingerprint: 'abc',
  record: {},
  evaluated_on: '2026-10-18',
  evaluated_at: '2026-10-18T08:00:00Z',
  ...over,
})

const stageCheck = (over: Record<string, unknown> = {}) => ({
  rule: 'education_stage', result: 'pass', expected: ['class_10', 'class_12'], actual: 'class_10', basis: 'reported', ...over,
})

const base = (ev: unknown) => ({
  'GET /consents/me': { body: consentStatus() },
  'POST /eligibility/evaluations': { body: ev },
})

beforeEach(() => loginAs())

it('ELIGIBLE: says what was met, never promises the benefit, and shows version, date and caveats', async () => {
  const api = mockApi(
    base(
      evaluation({
        checks: [
          stageCheck(),
          { rule: 'age_min', result: 'pass', expected: { limit: 15, as_on: '2026-10-18' }, actual: 16, basis: 'reported' },
          { rule: 'family_income_max', result: 'pass', expected: 250000, actual: 120000, basis: 'reported' },
        ],
        flags: ['based_on_self_reported_facts', 'has_criteria_not_checked_by_engine'],
      }),
    ),
  )
  await renderApp('/eligibility/merit-scholarship')
  const heading = await screen.findByRole('heading', { name: /You meet the rules we could check/ })
  expect(heading).toHaveFocus()
  expect(heading.closest('.outcome')).toHaveClass('outcome--ELIGIBLE')
  expect(screen.getByText(/This is not a promise that you will get it/)).toBeInTheDocument()
  expect(api.calls.find((c) => c.method === 'POST')?.body).toEqual({ opportunity: 'merit-scholarship', language: 'en' })

  const stage = screen.getByText('Class or course', { selector: 'strong' }).closest('li')!
  expect(within(stage).getByText('Met')).toBeInTheDocument()
  expect(within(stage).getByText('The rule says: Class 10, Class 12')).toBeInTheDocument()
  expect(within(stage).getByText('Your answer: Class 10 (you told us)')).toBeInTheDocument()
  const age = screen.getByText('Minimum age', { selector: 'strong' }).closest('li')!
  expect(within(age).getByText(/The rule says: 15 years, counted on 18 Oct 2026/)).toBeInTheDocument()
  expect(within(age).getByText('Your answer: 16 years (you told us)')).toBeInTheDocument()
  const income = screen.getByText('Family income', { selector: 'strong' }).closest('li')!
  expect(within(income).getByText('The rule says: ₹2,50,000 a year or less')).toBeInTheDocument()

  expect(screen.getByText('Based on what you told us, which has not been checked.')).toBeInTheDocument()
  expect(screen.getByText(/other rules we cannot check/)).toBeInTheDocument()
  expect(screen.getByText(/Rule version: 2026-10-1/)).toBeInTheDocument()
  expect(screen.getByText(/Checked on: 18 Oct 2026/)).toBeInTheDocument()
  expect(screen.getByText(/Eligibility is separate from whether this suits you/)).toBeInTheDocument()
  const official = screen.getByRole('link', { name: /Go to the official website/ })
  expect(official).toHaveAttribute('target', '_blank')
  expect(official).toHaveAttribute('rel', 'noopener noreferrer')
  expect(screen.getByRole('button', { name: 'Explain in simple words' })).toBeInTheDocument()
})

it('INELIGIBLE: names the rule that is not met, with distinct wording and style', async () => {
  mockApi(
    base(
      evaluation({
        outcome: 'INELIGIBLE',
        reasons: ['education_stage_not_met'],
        checks: [stageCheck({ result: 'fail', actual: 'class_9' })],
      }),
    ),
  )
  await renderApp('/eligibility/merit-scholarship')
  const heading = await screen.findByRole('heading', { name: /You do not meet at least one rule/ })
  expect(heading.closest('.outcome')).toHaveClass('outcome--INELIGIBLE')
  expect(screen.getByText('Your class or course is not one of those listed.')).toBeInTheDocument()
  expect(screen.getByText('Not met')).toBeInTheDocument()
  expect(screen.getByText('Your answer: Class 9 (you told us)')).toBeInTheDocument()
  expect(screen.queryByText(/You meet the rules/)).not.toBeInTheDocument()
})

it('UNKNOWN: says not knowing is not a "no" and lists what is missing', async () => {
  mockApi(
    base(
      evaluation({
        outcome: 'UNKNOWN',
        reasons: ['missing_education_stage', 'missing_date_of_birth'],
        checks: [stageCheck({ result: 'unknown', actual: null, basis: null })],
        missing: [
          { fact: 'education_stage', question_id: 'q_education_stage' },
          { fact: 'date_of_birth', question_id: null },
        ],
      }),
    ),
  )
  await renderApp('/eligibility/merit-scholarship')
  const heading = await screen.findByRole('heading', { name: 'We cannot tell yet' })
  expect(heading.closest('.outcome')).toHaveClass('outcome--UNKNOWN')
  expect(screen.getByText(/Not knowing is not a "no"/)).toBeInTheDocument()
  expect(screen.getByText('Your answer: not known')).toBeInTheDocument()
  expect(screen.getByText('Not known')).toBeInTheDocument()
  const missing = screen.getByRole('heading', { name: 'What we still need to know' }).parentElement!
  expect(within(missing).getByRole('button', { name: 'Answer: Your class or course' })).toBeInTheDocument()
  expect(within(missing).getByText('This was given when you registered. It cannot be changed here.')).toBeInTheDocument()
  expect(within(missing).getAllByRole('button')).toHaveLength(1) // nothing to answer for date of birth
})

it('NEEDS_REVIEW: asks for a person to check and shows conflicting answers side by side', async () => {
  mockApi(
    base(
      evaluation({
        outcome: 'NEEDS_REVIEW',
        reasons: ['conflicting_education_stage', 'other_criteria_need_review'],
        checks: [
          stageCheck({ result: 'conflict', actual: [['reported', 'class_9'], ['observed', 'class_10']], basis: null }),
        ],
        flags: ['has_criteria_not_checked_by_engine'],
      }),
    ),
  )
  await renderApp('/eligibility/merit-scholarship')
  const heading = await screen.findByRole('heading', { name: 'A person needs to check this' })
  expect(heading.closest('.outcome')).toHaveClass('outcome--NEEDS_REVIEW')
  expect(screen.getByText('Answers differ')).toBeInTheDocument()
  expect(
    screen.getByText('Your answer: you told us: Class 9; a teacher or helper saw this: Class 10'),
  ).toBeInTheDocument()
  expect(screen.getByText('You gave us different answers about your class or course.')).toBeInTheDocument()
})

it('uses a different symbol and wording for every outcome, not just colour', async () => {
  const symbols: string[] = []
  for (const outcome of ['ELIGIBLE', 'INELIGIBLE', 'UNKNOWN', 'NEEDS_REVIEW']) {
    mockApi(base(evaluation({ outcome })))
    const { unmount } = await renderApp('/eligibility/merit-scholarship')
    const h = await screen.findByRole('heading', { level: 2 })
    symbols.push(h.textContent ?? '')
    unmount()
  }
  expect(new Set(symbols).size).toBe(4)
})

it('lets the student answer a missing fact right there, then checks again', async () => {
  let evaluations = 0
  const api = mockApi({
    'GET /consents/me': { body: consentStatus() },
    'POST /eligibility/evaluations': () => {
      evaluations++
      return {
        body:
          evaluations === 1
            ? evaluation({
                outcome: 'UNKNOWN',
                reasons: ['missing_education_stage'],
                checks: [stageCheck({ result: 'unknown', actual: null, basis: null })],
                missing: [{ fact: 'education_stage', question_id: 'q_education_stage' }],
              })
            : evaluation({ id: 'e2', checks: [stageCheck()] }),
      }
    },
    'GET /interview/questions': { body: [question()] },
    'PUT /profile/fields/education_stage': { body: { fields: [] } },
  })
  await renderApp('/eligibility/merit-scholarship')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: 'Answer: Your class or course' }))
  expect(await screen.findByRole('heading', { name: 'Which class or course are you in now?' })).toHaveFocus()
  expect(api.calls.find((c) => c.path === '/interview/questions')?.query).toBe('?language=en')
  await user.click(screen.getByRole('button', { name: 'Class 10' }))

  expect(await screen.findByRole('heading', { name: /You meet the rules we could check/ })).toBeInTheDocument()
  const put = api.calls.find((c) => c.method === 'PUT')
  expect(put?.path).toBe('/profile/fields/education_stage')
  expect(put?.body).toEqual({ value: 'class_10' })
  expect(api.count('POST /eligibility/evaluations')).toBe(2)
  expect(screen.queryByText('What we still need to know')).not.toBeInTheDocument()
})

it('keeps the answer form open and shows the error if saving fails', async () => {
  mockApi({
    'GET /consents/me': { body: consentStatus() },
    'POST /eligibility/evaluations': {
      body: evaluation({ outcome: 'UNKNOWN', missing: [{ fact: 'education_stage', question_id: 'q_education_stage' }] }),
    },
    'GET /interview/questions': { body: [question()] },
    'PUT /profile/fields/education_stage': { status: 422, body: { detail: 'invalid_value' } },
  })
  await renderApp('/eligibility/merit-scholarship')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: 'Answer: Your class or course' }))
  await user.click(await screen.findByRole('button', { name: 'Class 10' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('That answer is not valid.')
  expect(screen.getByRole('button', { name: 'Class 10' })).toBeEnabled()
})

it('shows a translated error and retries', async () => {
  let n = 0
  mockApi({
    'GET /consents/me': { body: consentStatus() },
    'POST /eligibility/evaluations': () => (++n === 1 ? { status: 404, body: { detail: 'opportunity_not_found' } } : { body: evaluation() }),
  })
  await renderApp('/eligibility/merit-scholarship')
  expect(await screen.findByRole('alert')).toHaveTextContent('We could not find this opportunity.')
  await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByRole('heading', { name: /You meet the rules we could check/ })).toBeInTheDocument()
})

it('re-runs the check on request', async () => {
  const api = mockApi(base(evaluation()))
  await renderApp('/eligibility/merit-scholarship')
  await userEvent.click(await screen.findByRole('button', { name: 'Check again' }))
  await waitFor(() => expect(api.count('POST /eligibility/evaluations')).toBe(2))
  expect(await screen.findByRole('heading', { name: /You meet the rules we could check/ })).toBeInTheDocument()
})

it('starts from the opportunity page with a button', async () => {
  const api = mockApi({
    ...base(evaluation({ outcome: 'INELIGIBLE' })),
    'GET /opportunities/merit-scholarship': { body: opportunity() },
  })
  await renderApp('/opportunities/merit-scholarship')
  await userEvent.click(await screen.findByRole('button', { name: 'Check if I can apply' }))
  expect(await screen.findByRole('heading', { name: /You do not meet at least one rule/ })).toBeInTheDocument()
  expect(api.count('POST /eligibility/evaluations')).toBe(1)
})

it('renders the result in Tamil with Tamil rule names and the UI language in the request', async () => {
  const api = mockApi(
    base(
      evaluation({
        outcome: 'UNKNOWN',
        reasons: ['missing_education_stage'],
        checks: [stageCheck({ result: 'unknown', actual: null, basis: null })],
        missing: [{ fact: 'education_stage', question_id: 'q_education_stage' }],
      }),
    ),
  )
  await renderApp('/eligibility/merit-scholarship', 'ta')
  expect(await screen.findByRole('heading', { name: 'இன்னும் எங்களால் சொல்ல முடியவில்லை' })).toBeInTheDocument()
  expect(screen.getByText('உங்கள் வகுப்பு அல்லது படிப்பு எங்களுக்குத் தெரியாது.')).toBeInTheDocument()
  expect(screen.getByText('வகுப்பு அல்லது படிப்பு', { selector: 'strong' })).toBeInTheDocument()
  expect(screen.getByText(/தகுதி என்பது இது உங்களுக்குப் பொருந்துமா/)).toBeInTheDocument()
  expect(api.calls.find((c) => c.method === 'POST')?.body).toEqual({ opportunity: 'merit-scholarship', language: 'ta' })
})
