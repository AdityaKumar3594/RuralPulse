import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it } from 'vitest'
import { consentStatus, loginAs, mockApi, renderApp } from '../../test/utils'

const sourceCard = {
  slug: 'national-learning-platform',
  title: 'National Learning Platform',
  url: 'https://learn.example.gov.in',
  kind: 'platform',
  source: 'Skill Portal',
  verification_status: 'unverified',
  verified_fields: [],
  freshness: 'stale',
}

const item = (over: Record<string, unknown> = {}) => ({
  slug: 'electrician',
  family: 'skilled_trades',
  kind: 'match',
  points: 7.25,
  match_level: 'strong',
  reasons: [
    { student_field: 'interests', student_term: 'wiring', basis: 'reported', career_field: 'keywords', matched_text: 'wiring', points: 3 },
    { student_field: 'skills', student_term: 'fixing', basis: 'observed', career_field: 'activities', matched_text: 'fix wiring', points: 2 },
  ],
  stage: { typical_min_stage: 'class_10', status: 'below', student_stage: 'class_9' },
  unknowns: ['career_cost_unknown', 'career_time_needed_unknown'],
  career: { slug: 'electrician', family: 'skilled_trades', title: 'Electrician', description: 'Installs and fixes wiring.', entry_notes: 'Usually ITI after Class 10.' },
  routes: [],
  sources: [sourceCard],
  next_actions: [
    { type: 'view_career', career: 'electrician' },
    { type: 'plan_prerequisite', typical_min_stage: 'class_10' },
    { type: 'open_route', route_kind: 'self_learning', opportunity: 'national-learning-platform', url: 'https://learn.example.gov.in' },
  ],
  flags: ['catalog_entry_unverified', 'entry_requirements_are_typical_not_official'],
  language_fallback: false,
  ...over,
})

const explore = item({
  slug: 'tailor',
  family: 'creative_crafts',
  kind: 'explore',
  points: null,
  match_level: null,
  reasons: [],
  stage: { typical_min_stage: null, status: 'not_required', student_stage: 'class_9' },
  career: { slug: 'tailor', family: 'creative_crafts', title: 'Tailor', description: 'Makes clothes.', entry_notes: null },
  sources: [],
  next_actions: [{ type: 'tell_us', fact: 'education_stage', question_id: 'q_education_stage' }],
})

const run = (over: Record<string, unknown> = {}) => ({
  id: 'run-1',
  ranking_version: 'v1',
  status: 'ok',
  created_at: '2026-10-18T08:00:00Z',
  families: ['skilled_trades'],
  profile_summary: { terms: [], education_stage: 'class_9', hypotheses_ignored: 0, unmatched_terms: [] },
  missing: [],
  items: [item(), explore],
  notes: ['points_are_keyword_evidence_not_a_probability', 'interest_is_not_ability', 'eligibility_is_checked_separately'],
  ...over,
})

const base = (r: unknown) => ({
  'GET /consents/me': { body: consentStatus() },
  'POST /recommendations': { body: r },
})

beforeEach(() => loginAs())

it('shows Matches and "Explore something different" as separate sections with level labels and reasons, no percentages', async () => {
  const api = mockApi(base(run()))
  await renderApp('/recommendations')
  const matches = (await screen.findByRole('heading', { name: 'Matches' })).closest('section')!
  const exploreSection = screen.getByRole('heading', { name: 'Explore something different' }).closest('section')!
  expect(matches).not.toBe(exploreSection)
  expect(api.calls.find((c) => c.method === 'POST')?.body).toEqual({ language: 'en', limit: 5 })

  const card = within(matches).getByRole('heading', { name: 'Electrician' }).closest('li')!
  expect(within(card).getByText('Strong match')).toBeInTheDocument()
  expect(within(card).getByText('You told us "wiring" (interests). This career lists "wiring" (keywords).')).toBeInTheDocument()
  expect(within(card).getByText('A teacher or helper saw "fixing" (skills). This career lists "fix wiring" (activities).')).toBeInTheDocument()
  expect(within(card).getByText(/This career usually starts after Class 10\. You told us you are at Class 9\. This is for your information/)).toBeInTheDocument()
  expect(within(card).getByText('We do not know what this costs.')).toBeInTheDocument()
  expect(within(card).getByText('We do not know how long this takes.')).toBeInTheDocument()
  expect(within(card).getByText('This career entry is an unverified draft.')).toBeInTheDocument()
  expect(within(card).getByText('Entry requirements are typical, not official.')).toBeInTheDocument()
  expect(within(card).getByText('Check is old')).toBeInTheDocument()
  expect(within(card).getByText('Not verified yet')).toBeInTheDocument()
  expect(within(card).getByRole('link', { name: 'Read about this career' })).toHaveAttribute('href', '/careers/electrician')
  expect(within(card).getByRole('link', { name: 'Read about: Self learning' })).toHaveAttribute('href', '/opportunities/national-learning-platform')
  expect(within(card).getByText('See how to reach Class 10')).toBeInTheDocument()
  expect(within(card).getByRole('button', { name: 'Explain in simple words' })).toBeInTheDocument()
  expect(within(card).getByRole('button', { name: 'Build my pathway' })).toBeInTheDocument()

  const ex = within(exploreSection).getByRole('heading', { name: 'Tailor' }).closest('li')!
  expect(within(ex).getByText('To explore')).toBeInTheDocument()
  expect(within(ex).queryByText(/match$/)).not.toBeInTheDocument()
  expect(within(ex).queryByText('Why this career')).not.toBeInTheDocument()
  expect(within(exploreSection).getByText(/not because they match what you told us/)).toBeInTheDocument()
  expect(within(ex).getByRole('link', { name: 'Tell us your class or course' })).toHaveAttribute('href', '/interview')

  const text = document.body.textContent ?? ''
  expect(text).not.toMatch(/\d\s*%|percent|probability/i)
  expect(text).not.toContain('7.25')
  expect(screen.getByText('A match shows words in common. It is not a chance of success.')).toBeInTheDocument()
})

it('insufficient profile: says what is missing, links to the interview, and still offers exploring', async () => {
  mockApi(
    base(
      run({
        status: 'insufficient_profile',
        missing: [
          { field: 'goals', question_id: 'q_goals' },
          { field: 'education_stage', question_id: 'q_education_stage' },
        ],
        items: [explore],
      }),
    ),
  )
  await renderApp('/recommendations')
  expect(await screen.findByRole('heading', { name: 'We need to know a little more about you' })).toBeInTheDocument()
  const missing = screen.getByRole('heading', { name: 'What would help us' }).closest('section')!
  expect(within(missing).getByText('What you want to do later')).toBeInTheDocument()
  expect(within(missing).getByText('Your class or course')).toBeInTheDocument()
  expect(within(missing).getByRole('link', { name: 'Answer questions' })).toHaveAttribute('href', '/interview')
  expect(screen.queryByRole('heading', { name: 'Matches' })).not.toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Explore something different' })).toBeInTheDocument()
})

it('no matches: says the catalog may not cover it and lists the unmatched words', async () => {
  mockApi(
    base(
      run({
        status: 'no_matches',
        items: [],
        profile_summary: { terms: [], education_stage: 'class_9', unmatched_terms: [{ field: 'goals', text: 'astronaut' }] },
      }),
    ),
  )
  await renderApp('/recommendations')
  expect(await screen.findByRole('heading', { name: 'We found no careers that match' })).toBeInTheDocument()
  expect(screen.getByText(/The catalog may not cover what you told us/)).toBeInTheDocument()
  expect(screen.getByText('what you want to do: astronaut')).toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Matches' })).not.toBeInTheDocument()
})

it('explains a recommendation with the run and career', async () => {
  const api = mockApi({
    ...base(run()),
    'POST /explanations': {
      body: {
        id: 'x1', kind: 'recommendation', language: 'en', source: 'template', fallback_reason: 'ai_not_configured', model: null, cached: false,
        explanation: { headline: 'Electrician uses words you told us', why: ['You said wiring'], requirements: [], eligibility_status: 'NOT_APPLICABLE', freshness_note: '', missing_information: [], next_action: 'Read about it' },
        sources: [], created_at: 'x',
      },
    },
  })
  await renderApp('/recommendations')
  const card = (await screen.findByRole('heading', { name: 'Electrician' })).closest('li')!
  await userEvent.click(within(card).getByRole('button', { name: 'Explain in simple words' }))
  expect(await within(card).findByText(/Electrician uses words you told us/)).toBeInTheDocument()
  expect(api.calls.find((c) => c.path === '/explanations')?.body).toEqual({
    kind: 'recommendation', run_id: 'run-1', career: 'electrician', language: 'en',
  })
})

it('builds a pathway and goes to it', async () => {
  const api = mockApi({
    ...base(run()),
    'POST /pathways': { status: 201, body: { id: 'p1' } },
    'GET /pathways/p1': {
      body: { id: 'p1', career: { slug: 'electrician', title: 'Electrician', family: 'skilled_trades' }, version: 'v', student_stage: null, created_at: 'x', steps: [], alternatives: [], unknowns: [], language_fallback: false },
    },
  })
  await renderApp('/recommendations')
  const card = (await screen.findByRole('heading', { name: 'Electrician' })).closest('li')!
  await userEvent.click(within(card).getByRole('button', { name: 'Build my pathway' }))
  expect(await screen.findByRole('heading', { level: 1, name: 'Pathway: Electrician' })).toBeInTheDocument()
  expect(api.calls.find((c) => c.method === 'POST' && c.path === '/pathways')?.body).toEqual({ career: 'electrician', language: 'en' })
})

it('shows an error if the pathway cannot be built, and allows retry', async () => {
  let n = 0
  mockApi({
    ...base(run({ items: [item()] })),
    'POST /pathways': () => (++n === 1 ? { status: 404, body: { detail: 'career_not_found' } } : { status: 201, body: { id: 'p1' } }),
    'GET /pathways/p1': { body: { id: 'p1', career: { slug: 'electrician', title: 'Electrician', family: 'x' }, version: 'v', student_stage: null, created_at: 'x', steps: [], alternatives: [], unknowns: [], language_fallback: false } },
  })
  await renderApp('/recommendations')
  await userEvent.click(await screen.findByRole('button', { name: 'Build my pathway' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('We could not find this career.')
  await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByRole('heading', { level: 1, name: 'Pathway: Electrician' })).toBeInTheDocument()
})

it('shows an error with retry when suggestions cannot be loaded', async () => {
  let n = 0
  mockApi({
    'GET /consents/me': { body: consentStatus() },
    'POST /recommendations': () => (++n === 1 ? { status: 422, body: {} } : { body: run() }),
  })
  await renderApp('/recommendations')
  expect(await screen.findByRole('alert')).toHaveTextContent('Something went wrong')
  await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByRole('heading', { name: 'Matches' })).toBeInTheDocument()
})

it('renders in Tamil and asks the server for Tamil', async () => {
  const api = mockApi(base(run()))
  await renderApp('/recommendations', 'ta')
  expect(await screen.findByRole('heading', { name: 'பொருந்துபவை' })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'வேறு ஒன்றை ஆராயுங்கள்' })).toBeInTheDocument()
  expect(screen.getByText('வலுவான பொருத்தம்')).toBeInTheDocument()
  expect(api.calls.find((c) => c.method === 'POST')?.body).toEqual({ language: 'ta', limit: 5 })
})
