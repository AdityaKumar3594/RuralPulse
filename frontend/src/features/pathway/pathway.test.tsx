import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it } from 'vitest'
import { consentStatus, loginAs, mockApi, renderApp } from '../../test/utils'

const step = (over: Record<string, unknown> = {}) => ({
  id: 'skills',
  type: 'skill_building',
  group: 'preparation',
  title: 'Build these skills (helpful, not required)',
  depends_on: [],
  requirement_level: 'suggested_preparation',
  estimated_effort: null,
  stage: null,
  route_index: null,
  route_kind: null,
  skills: ['Safety', 'Measuring'],
  resource: null,
  completion_criteria: { type: 'self_report' },
  status: 'not_started',
  note: null,
  ...over,
})

const stageStep = step({
  id: 'stage:class_10',
  type: 'qualification',
  group: 'foundation',
  title: 'Complete Class 10 (this is the usual requirement, not an official rule)',
  requirement_level: 'typical_route',
  stage: 'class_10',
  skills: null,
})
const resourceStep = step({
  id: 'resource:national-learning-platform',
  type: 'learning_resource',
  title: 'National Learning Platform',
  skills: null,
  resource: {
    slug: 'national-learning-platform',
    title: 'National Learning Platform',
    url: 'https://learn.example.gov.in',
    kind: 'platform',
    source: 'Skill Portal',
    verification_status: 'unverified',
    freshness: 'stale',
    check_eligibility: true,
  },
})
const itiRoute = step({
  id: 'route:0',
  type: 'route',
  group: 'alternative:0',
  title: 'ITI course',
  depends_on: ['stage:class_10'],
  requirement_level: 'typical_route',
  route_index: 0,
  route_kind: 'iti',
  skills: null,
})
const onlineRoute = step({
  id: 'route:1',
  type: 'route',
  group: 'alternative:1',
  title: 'Learn online',
  requirement_level: 'typical_route',
  route_index: 1,
  route_kind: 'self_learning',
  skills: null,
})

const plan = (steps: unknown[] = [stageStep, step(), resourceStep, itiRoute, onlineRoute], over: Record<string, unknown> = {}) => ({
  id: 'p1',
  career: { slug: 'electrician', title: 'Electrician', family: 'skilled_trades' },
  version: '2026-10-1',
  student_stage: 'class_9',
  created_at: '2026-10-18T08:00:00Z',
  steps,
  alternatives: ['route:0', 'route:1'],
  unknowns: ['effort_not_available', 'cost_not_available', 'local_availability_unknown', 'requirements_are_typical_not_official'],
  language_fallback: false,
  ...over,
})

const base = (p: unknown = plan()) => ({
  'GET /consents/me': { body: consentStatus() },
  'GET /pathways/p1': { body: p },
})

beforeEach(() => loginAs())

it('lists pathways with progress and links', async () => {
  mockApi({
    'GET /consents/me': { body: consentStatus() },
    'GET /pathways': { body: [plan([step({ status: 'done' }), stageStep])] },
  })
  await renderApp('/pathways')
  const card = (await screen.findByRole('heading', { name: 'Electrician' })).closest('li')!
  expect(within(card).getByText('Steps done: 1 of 2')).toBeInTheDocument()
  expect(within(card).getByRole('progressbar')).toHaveAttribute('max', '2')
  expect(within(card).getByRole('link', { name: /Open this pathway/ })).toHaveAttribute('href', '/pathways/p1')
})

it('invites the student to build a first pathway when there are none', async () => {
  mockApi({ 'GET /consents/me': { body: consentStatus() }, 'GET /pathways': { body: [] } })
  await renderApp('/pathways')
  expect(await screen.findByText(/You have no pathways yet/)).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'See suggestions' })).toHaveAttribute('href', '/recommendations')
  expect(screen.getByRole('link', { name: 'Browse careers' })).toHaveAttribute('href', '/careers')
})

it('shows steps in order with honest requirement labels, dependencies, alternatives and unknowns', async () => {
  mockApi(base())
  await renderApp('/pathways/p1')
  expect(await screen.findByRole('heading', { level: 1, name: 'Pathway: Electrician' })).toBeInTheDocument()

  const ordered = screen.getByRole('list', { name: 'Steps in order' })
  expect(ordered.tagName).toBe('OL')
  const titles = within(ordered).getAllByRole('heading', { level: 3 }).map((h) => h.textContent)
  expect(titles).toEqual([
    'Complete Class 10 (this is the usual requirement, not an official rule)',
    'Build these skills (helpful, not required)',
    'National Learning Platform',
  ])
  expect(within(ordered).getByText('Step 1')).toBeInTheDocument()
  expect(within(ordered).getByText('Skills: Safety, Measuring')).toBeInTheDocument()

  // Requirement levels are never "mandatory".
  expect(screen.getAllByText('Usual route, not an official rule').length).toBeGreaterThan(0)
  expect(screen.getAllByText('Helpful, not required').length).toBeGreaterThan(0)
  expect(document.body.textContent).not.toMatch(/mandatory|compulsory/i)

  // Resource card with freshness and the right links.
  const res = screen.getByRole('heading', { name: 'Resource' }).parentElement!
  expect(within(res).getByText('Check is old')).toBeInTheDocument()
  expect(within(res).getByText('Source: Skill Portal')).toBeInTheDocument()
  expect(within(res).getByRole('link', { name: 'Check if I can apply' })).toHaveAttribute('href', '/eligibility/national-learning-platform')
  const ext = within(res).getByRole('link', { name: /Go to the official website/ })
  expect(ext).toHaveAttribute('target', '_blank')
  expect(ext).toHaveAttribute('rel', 'noopener noreferrer')

  // Alternatives are grouped and explained.
  const alt = screen.getByRole('heading', { name: 'Choose any one of these routes' }).closest('section')!
  expect(within(alt).getByText(/You do not need to do all of them/)).toBeInTheDocument()
  const iti = within(alt).getByRole('heading', { name: 'ITI course' }).closest('li')!
  expect(within(iti).getByText(/After: Complete Class 10/)).toBeInTheDocument()
  expect(within(alt).getByRole('heading', { name: 'Learn online' })).toBeInTheDocument()

  // What we do not know.
  const unknown = screen.getByRole('heading', { name: 'What we do not know' }).closest('section')!
  expect(within(unknown).getByText('We do not know how much effort each step needs.')).toBeInTheDocument()
  expect(within(unknown).getByText('We do not know what each step costs.')).toBeInTheDocument()
  expect(within(unknown).getByText('We do not know what is available near you.')).toBeInTheDocument()
  expect(screen.getByText('Pathway version: 2026-10-1')).toBeInTheDocument()
  expect(screen.getByText('Steps done: 0 of 5')).toBeInTheDocument()
})

it('disables "In progress" and "Done" while earlier steps are not done, and says why', async () => {
  mockApi(base())
  await renderApp('/pathways/p1')
  const iti = (await screen.findByRole('heading', { name: 'ITI course' })).closest('li')!
  expect(within(iti).getByRole('button', { name: 'In progress' })).toBeDisabled()
  expect(within(iti).getByRole('button', { name: 'Done' })).toBeDisabled()
  expect(within(iti).getByRole('button', { name: 'Not started' })).toBeEnabled()
  expect(within(iti).getByRole('button', { name: 'Not started' })).toHaveAttribute('aria-pressed', 'true')
  expect(within(iti).getByText('Finish the earlier steps first.')).toBeInTheDocument()
  const group = within(iti).getByRole('group', { name: 'Progress: ITI course' })
  expect(group).toHaveAccessibleDescription('Finish the earlier steps first.')

  const free = screen.getByRole('heading', { name: 'Learn online' }).closest('li')!
  expect(within(free).getByRole('button', { name: 'Done' })).toBeEnabled()
})

it('saves a status change and shows the updated plan', async () => {
  const updated = plan([stageStep, step({ status: 'in_progress' }), resourceStep, itiRoute, onlineRoute])
  const api = mockApi({
    ...base(),
    'PUT /pathways/p1/steps/skills': { body: updated },
  })
  await renderApp('/pathways/p1')
  const skills = (await screen.findByRole('heading', { name: 'Build these skills (helpful, not required)' })).closest('li')!
  await userEvent.click(within(skills).getByRole('button', { name: 'In progress' }))
  expect(await within(skills).findByRole('status')).toHaveTextContent('Saved: Build these skills (helpful, not required) is now "In progress".')
  expect(within(skills).getByRole('button', { name: 'In progress' })).toHaveAttribute('aria-pressed', 'true')
  const put = api.calls.find((c) => c.method === 'PUT')
  expect(put?.body).toEqual({ status: 'in_progress' })
  expect(put?.query).toBe('?language=en')
})

it('unlocks later steps once the prerequisite is done (ids with a colon are encoded)', async () => {
  const done = plan([{ ...stageStep, status: 'done' }, step(), resourceStep, itiRoute, onlineRoute])
  const api = mockApi({ ...base(), 'PUT /pathways/p1/steps/stage%3Aclass_10': { body: done } })
  await renderApp('/pathways/p1')
  const stage = (await screen.findByRole('heading', { name: /Complete Class 10/ })).closest('li')!
  await userEvent.click(within(stage).getByRole('button', { name: 'Done' }))
  await within(stage).findByRole('status')
  expect(api.count('PUT /pathways/p1/steps/stage%3Aclass_10')).toBe(1)
  const iti = screen.getByRole('heading', { name: 'ITI course' }).closest('li')!
  expect(within(iti).getByRole('button', { name: 'Done' })).toBeEnabled()
  expect(within(iti).queryByText('Finish the earlier steps first.')).not.toBeInTheDocument()
})

it('explains a prerequisites_not_done conflict and leaves the step as it was', async () => {
  mockApi({
    ...base(),
    'PUT /pathways/p1/steps/route%3A1': { status: 409, body: { detail: 'prerequisites_not_done' } },
  })
  await renderApp('/pathways/p1')
  const route = (await screen.findByRole('heading', { name: 'Learn online' })).closest('li')!
  await userEvent.click(within(route).getByRole('button', { name: 'Done' }))
  expect(await within(route).findByRole('alert')).toHaveTextContent('You cannot change this step yet. Finish the steps before it first.')
  expect(within(route).getByRole('button', { name: 'Not started' })).toHaveAttribute('aria-pressed', 'true')
  expect(within(route).getByRole('button', { name: 'Done' })).toBeEnabled() // controls come back so the student can try again
})

it('explains a dependent_steps_started conflict', async () => {
  const p = plan([{ ...stageStep, status: 'done' }, step(), resourceStep, { ...itiRoute, status: 'in_progress' }, onlineRoute])
  mockApi({
    ...base(p),
    'PUT /pathways/p1/steps/stage%3Aclass_10': { status: 409, body: { detail: 'dependent_steps_started' } },
  })
  await renderApp('/pathways/p1')
  const stage = (await screen.findByRole('heading', { name: /Complete Class 10/ })).closest('li')!
  await userEvent.click(within(stage).getByRole('button', { name: 'Not started' }))
  expect(await within(stage).findByRole('alert')).toHaveTextContent('You cannot move this step back because a later step has already been started.')
  expect(within(stage).getByRole('button', { name: 'Done' })).toHaveAttribute('aria-pressed', 'true')
})

it('explains the pathway through the explanation panel', async () => {
  const api = mockApi({
    ...base(),
    'POST /explanations': {
      body: {
        id: 'x2', kind: 'pathway', language: 'en', source: 'ai', fallback_reason: null, model: 'm', cached: false,
        explanation: { headline: 'Start with Class 10', why: [], requirements: [], eligibility_status: 'NOT_APPLICABLE', freshness_note: '', missing_information: [], next_action: 'Pick a route' },
        sources: [], created_at: 'x',
      },
    },
  })
  await renderApp('/pathways/p1')
  await userEvent.click(await screen.findByRole('button', { name: 'Explain in simple words' }))
  expect(await screen.findByText(/Start with Class 10/)).toBeInTheDocument()
  expect(screen.getByText('Written by AI from checked facts')).toBeInTheDocument()
  expect(api.calls.find((c) => c.path === '/explanations')?.body).toEqual({ kind: 'pathway', plan_id: 'p1', language: 'en' })
})

it('shows a translated error with retry when the pathway cannot be loaded', async () => {
  let n = 0
  mockApi({
    'GET /consents/me': { body: consentStatus() },
    'GET /pathways/p1': () => (++n === 1 ? { status: 404, body: { detail: 'plan_not_found' } } : { body: plan() }),
  })
  await renderApp('/pathways/p1')
  expect(await screen.findByRole('alert')).toHaveTextContent('We could not find this pathway.')
  await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByRole('heading', { level: 1, name: 'Pathway: Electrician' })).toBeInTheDocument()
})

it('renders a pathway in Tamil', async () => {
  const api = mockApi(base())
  await renderApp('/pathways/p1', 'ta')
  expect(await screen.findByRole('heading', { level: 1, name: 'வழித்திட்டம்: Electrician' })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'இந்த வழிகளில் ஏதேனும் ஒன்றைத் தேர்ந்தெடுங்கள்' })).toBeInTheDocument()
  expect(screen.getAllByText('வழக்கமான வழி, அதிகாரபூர்வ விதி அல்ல').length).toBeGreaterThan(0)
  expect(screen.getAllByText('தொடங்கவில்லை').length).toBeGreaterThan(0)
  expect(api.calls.find((c) => c.path === '/pathways/p1')?.query).toBe('?language=ta')
})
