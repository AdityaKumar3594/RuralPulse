import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it } from 'vitest'
import { consentStatus, loginAs, mockApi, renderApp } from '../../test/utils'
import { career, hit, opportunity, searchResponse } from './testData'

beforeEach(() => sessionStorage.clear())

it('searches with the chosen filters and shows each result with its source, match type and freshness', async () => {
  const api = mockApi({ 'GET /search': { body: searchResponse({ results: [hit({ match_type: 'partial', flags: ['not_human_reviewed'] })] }) } })
  await renderApp('/search')
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('What are you looking for?'), '  scholarship ')
  await user.selectOptions(screen.getByLabelText('Show'), 'opportunity')
  await user.selectOptions(screen.getByLabelText('Kind of opportunity'), 'scholarship')
  await user.type(screen.getByLabelText(/Your state/), 'Tamil Nadu')
  await user.selectOptions(screen.getByLabelText('Class or course'), 'class_10')
  await user.click(screen.getByRole('button', { name: 'Search' }))

  const card = (await screen.findByRole('heading', { name: 'Merit Scholarship' })).closest('li')!
  const params = new URLSearchParams(api.calls[0].query)
  expect(Object.fromEntries(params)).toEqual({
    q: 'scholarship', type: 'opportunity', kind: 'scholarship', state: 'Tamil Nadu', stage: 'class_10', language: 'en',
  })
  expect(within(card).getByText('Money for students with good marks.')).toBeInTheDocument()
  expect(within(card).getByText('Scholarship')).toBeInTheDocument()
  expect(within(card).getByText('Partial match')).toBeInTheDocument()
  expect(within(card).getByText('Only some of your words matched.')).toBeInTheDocument()
  expect(within(card).getByText('Source: National Scholarship Portal')).toBeInTheDocument()
  expect(within(card).getByText('Checked recently')).toBeInTheDocument()
  expect(within(card).getByText('Verified against its source')).toBeInTheDocument()
  expect(within(card).getByText('Not yet re-checked by a person.')).toBeInTheDocument()
  expect(within(card).getByRole('link', { name: /View details/ })).toHaveAttribute('href', '/opportunities/merit-scholarship')
  expect(screen.getByRole('heading', { name: 'Results' })).toHaveFocus()
  expect(screen.getByText(/Partial: only some words matched/)).toBeInTheDocument()
})

it('does not send the kind filter together with careers', async () => {
  const api = mockApi({ 'GET /search': { body: searchResponse() } })
  await renderApp('/search')
  const user = userEvent.setup()
  await user.selectOptions(screen.getByLabelText('Kind of opportunity'), 'job')
  await user.selectOptions(screen.getByLabelText('Show'), 'career')
  expect(screen.getByLabelText('Kind of opportunity')).toBeDisabled()
  await user.click(screen.getByRole('button', { name: 'Search' }))
  await screen.findByRole('heading', { name: 'Results' })
  expect(new URLSearchParams(api.calls[0].query).has('kind')).toBe(false)
})

it('says nothing is guessed when there is insufficient evidence', async () => {
  mockApi({ 'GET /search': { body: searchResponse({ status: 'insufficient_evidence', message: 'No approved record matches. Nothing is guessed.', results: [] }) } })
  await renderApp('/search')
  await userEvent.click(screen.getByRole('button', { name: 'Search' }))
  expect(await screen.findByText('No approved record matches. Nothing is guessed.')).toHaveAttribute('role', 'status')
  expect(screen.queryByRole('list')).not.toBeInTheDocument()
})

it('warns when only partial matches were found', async () => {
  mockApi({ 'GET /search': { body: searchResponse({ status: 'partial_only', results: [hit({ match_type: 'partial' })] }) } })
  await renderApp('/search')
  await userEvent.click(screen.getByRole('button', { name: 'Search' }))
  expect(await screen.findByText(/Only some of your words matched\. Please read each result carefully/)).toBeInTheDocument()
})

it('labels stale, unverified and expired records with words and symbols, plus their flags', async () => {
  mockApi({
    'GET /search': {
      body: searchResponse({
        results: [
          hit({ id: 'a', title: 'Old scheme', freshness: 'stale', flags: ['needs_reverification'] }),
          hit({ id: 'b', title: 'Draft scheme', freshness: 'unverified', verification: { ...hit().verification, status: 'unverified' }, flags: ['unverified'] }),
          hit({ id: 'c', title: 'Closed scheme', freshness: 'expired', flags: ['expired_or_deadline_passed'] }),
          hit({ id: 'electrician', type: 'career', title: 'Electrician', group: 'skilled_trades', url: null, source: null, freshness: null, verification: null, eligibility_known: null, flags: ['catalog_entry_unverified'] }),
        ],
      }),
    },
  })
  await renderApp('/search')
  await userEvent.click(screen.getByRole('button', { name: 'Search' }))
  const stale = (await screen.findByRole('heading', { name: 'Old scheme' })).closest('li')!
  expect(within(stale).getByText('Check is old')).toBeInTheDocument()
  expect(within(stale).getByText('Needs to be checked again against its source.')).toBeInTheDocument()
  const draft = screen.getByRole('heading', { name: 'Draft scheme' }).closest('li')!
  expect(within(draft).getByText('Not checked yet')).toBeInTheDocument()
  expect(within(draft).getByText('Not verified yet')).toBeInTheDocument()
  const closed = screen.getByRole('heading', { name: 'Closed scheme' }).closest('li')!
  expect(within(closed).getByText('Expired')).toBeInTheDocument()
  expect(within(closed).getByText('Expired, or the deadline has passed.')).toBeInTheDocument()
  const careerCard = screen.getByRole('heading', { name: 'Electrician' }).closest('li')!
  expect(within(careerCard).getByText('Skilled trades')).toBeInTheDocument()
  expect(within(careerCard).getByText('This career entry is an unverified draft.')).toBeInTheDocument()
  expect(within(careerCard).getByRole('link', { name: /View details/ })).toHaveAttribute('href', '/careers/electrician')
})

it('shows a translated error and retries the search', async () => {
  let n = 0
  mockApi({
    'GET /search': () => (++n === 1 ? { status: 404, body: {} } : { body: searchResponse() }),
  })
  await renderApp('/search')
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: 'Search' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Something went wrong')
  await user.click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByRole('heading', { name: 'Merit Scholarship' })).toBeInTheDocument()
})

it('renders the search page in Tamil', async () => {
  const api = mockApi({ 'GET /search': { body: searchResponse({ results: [hit()] }) } })
  await renderApp('/search', 'ta')
  expect(screen.getByRole('heading', { level: 1, name: 'தொழில்களையும் வாய்ப்புகளையும் தேடுங்கள்' })).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'தேடு' }))
  const card = (await screen.findByRole('heading', { name: 'Merit Scholarship' })).closest('li')!
  expect(within(card).getByText('உதவித்தொகை')).toBeInTheDocument()
  expect(within(card).getByText('சமீபத்தில் சரிபார்த்தது')).toBeInTheDocument()
  expect(new URLSearchParams(api.calls[0].query).get('language')).toBe('ta')
})

it('browses careers by family', async () => {
  const api = mockApi({
    'GET /careers': (call) => ({
      body: new URLSearchParams(call.query).get('family')
        ? [{ slug: 'electrician', family: 'skilled_trades', title: 'Electrician' }]
        : [
            { slug: 'electrician', family: 'skilled_trades', title: 'Electrician' },
            { slug: 'tailor', family: 'creative_crafts', title: 'Tailor' },
          ],
    }),
  })
  await renderApp('/careers')
  expect(await screen.findByRole('heading', { name: 'Tailor' })).toBeInTheDocument()
  await userEvent.selectOptions(screen.getByLabelText('Group of careers'), 'skilled_trades')
  await screen.findByText('Careers shown: 1')
  expect(screen.queryByRole('heading', { name: 'Tailor' })).not.toBeInTheDocument()
  expect(api.calls.at(-1)?.query).toContain('family=skilled_trades')
  expect(screen.getByRole('link', { name: /Read about this career/ })).toHaveAttribute('href', '/careers/electrician')
})

it('shows a career with entry notes, the typical-not-official note and the draft warning', async () => {
  mockApi({ 'GET /careers/electrician': { body: career() } })
  await renderApp('/careers/electrician')
  expect(await screen.findByRole('heading', { level: 1, name: 'Electrician' })).toBeInTheDocument()
  expect(screen.getByText('Most people join an ITI after Class 10.')).toBeInTheDocument()
  expect(screen.getByText(/typical, not official/)).toBeInTheDocument()
  expect(screen.getByText(/unverified draft\. A person has not checked it/)).toBeInTheDocument()
  expect(screen.getByText('Usually starts after: Class 10')).toBeInTheDocument()
  expect(screen.getByText('Fix wiring')).toBeInTheDocument()
  expect(screen.getByText('Safety')).toBeInTheDocument()
  const routes = screen.getByRole('heading', { name: 'Ways to get into this work' }).closest('section')!
  expect(within(routes).getByText('ITI course')).toBeInTheDocument()
  expect(within(routes).getByRole('link', { name: 'National Learning Platform' })).toHaveAttribute('href', '/opportunities/national-learning-platform')
  expect(screen.getByRole('link', { name: 'Plumber' })).toHaveAttribute('href', '/careers/plumber')
  expect(screen.getByRole('heading', { name: 'Places to learn' })).toBeInTheDocument()
  // Anonymous visitors cannot build a pathway.
  expect(screen.queryByRole('button', { name: 'Build my pathway' })).not.toBeInTheDocument()
})

it('still shows the typical-not-official note when the entry has no notes, and no draft warning when verified', async () => {
  mockApi({ 'GET /careers/electrician': { body: career({ entry: { typical_min_stage: null, notes: null }, verification_status: 'verified' }) } })
  await renderApp('/careers/electrician')
  await screen.findByRole('heading', { level: 1, name: 'Electrician' })
  expect(screen.getByText('No entry notes are recorded yet.')).toBeInTheDocument()
  expect(screen.getByText(/typical, not official/)).toBeInTheDocument()
  expect(screen.queryByText(/unverified draft/)).not.toBeInTheDocument()
})

it('shows a not-found career with a translated error', async () => {
  mockApi({ 'GET /careers/nope': { status: 404, body: { detail: 'career_not_found' } } })
  await renderApp('/careers/nope')
  expect(await screen.findByRole('alert')).toHaveTextContent('We could not find this career.')
})

it('shows an opportunity with an official link that clearly leaves the app, and honest verification', async () => {
  mockApi({ 'GET /opportunities/merit-scholarship': { body: opportunity() } })
  await renderApp('/opportunities/merit-scholarship')
  expect(await screen.findByRole('heading', { level: 1, name: 'Merit Scholarship' })).toBeInTheDocument()
  const link = screen.getByRole('link', { name: /Go to the official website \(this leaves Ruralpulse\)/ })
  expect(link).toHaveAttribute('href', 'https://scholarships.gov.in/merit')
  expect(link).toHaveAttribute('target', '_blank')
  expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  expect(screen.getByText('Provider: Ministry of Education')).toBeInTheDocument()
  expect(screen.getByText('National Scholarship Portal (published by Govt of India)')).toBeInTheDocument()
  expect(screen.getByText('Checked details: web address, who can apply')).toBeInTheDocument()
  expect(screen.getByText(/Last checked on/)).toBeInTheDocument()
  expect(screen.getAllByText('Not yet re-checked by a person.').length).toBeGreaterThan(0)
  expect(screen.getByText('We do not know the deadline.')).toBeInTheDocument()
  expect(screen.getByText('Class or course: Class 10, Class 12')).toBeInTheDocument()
  expect(screen.getByText('Family income: not more than ₹2,50,000 a year')).toBeInTheDocument()
  expect(screen.getByText('Other rules: Studying in a government school')).toBeInTheDocument()
  // Nothing is shown for details the record does not have.
  expect(screen.queryByRole('heading', { name: 'Benefits' })).not.toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Dates' })).not.toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Documents listed' })).not.toBeInTheDocument()
  // Anonymous: asked to log in, no check button.
  expect(screen.queryByRole('button', { name: 'Check if I can apply' })).not.toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Log in' })).toBeInTheDocument()
})

it('shows benefits, dates and documents when the record has them', async () => {
  mockApi({
    'GET /opportunities/merit-scholarship': {
      body: opportunity({
        benefits: [{ text: 'Yearly support', amount_inr: 12000, period: 'year' }],
        application_deadline: '2026-12-31',
        expires_on: '2027-03-31',
        required_documents: ['Marksheet'],
        freshness: 'stale',
        flags: ['needs_reverification'],
      }),
    },
  })
  await renderApp('/opportunities/merit-scholarship')
  expect(await screen.findByText(/Yearly support/)).toHaveTextContent('About ₹12,000 every year')
  expect(screen.getByText(/Application deadline: /)).toBeInTheDocument()
  expect(screen.getByText(/This record is valid until: /)).toBeInTheDocument()
  expect(screen.getByText('Marksheet')).toBeInTheDocument()
  expect(screen.getByText('Check is old')).toBeInTheDocument()
})

it('does not turn an unsafe address into a link', async () => {
  mockApi({ 'GET /opportunities/merit-scholarship': { body: opportunity({ url: 'javascript:alert(1)' }) } })
  await renderApp('/opportunities/merit-scholarship')
  expect(await screen.findByText('No safe web address is available for this record.')).toBeInTheDocument()
  expect(screen.queryByRole('link', { name: /official website/ })).not.toBeInTheDocument()
})

it('offers "Check if I can apply" to students for kinds with criteria, and not otherwise', async () => {
  loginAs()
  mockApi({
    'GET /consents/me': { body: consentStatus() },
    'GET /opportunities/merit-scholarship': { body: opportunity() },
  })
  await renderApp('/opportunities/merit-scholarship')
  expect(await screen.findByRole('button', { name: 'Check if I can apply' })).toBeInTheDocument()
})

it('explains why a platform cannot be checked for eligibility', async () => {
  loginAs()
  mockApi({ 'GET /opportunities/p': { body: opportunity({ slug: 'p', kind: 'platform', eligibility: null }) } })
  await renderApp('/opportunities/p')
  expect(await screen.findByText('We cannot check eligibility for this kind of opportunity.')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Check if I can apply' })).not.toBeInTheDocument()
})

it('explains when a scheme has no published rules', async () => {
  loginAs()
  mockApi({ 'GET /opportunities/s': { body: opportunity({ slug: 's', kind: 'scheme', eligibility: null }) } })
  await renderApp('/opportunities/s')
  expect(await screen.findByText(/We hold no published rules/)).toBeInTheDocument()
})

it('renders an opportunity in Tamil', async () => {
  mockApi({ 'GET /opportunities/merit-scholarship': { body: opportunity() } })
  await renderApp('/opportunities/merit-scholarship', 'ta')
  expect(await screen.findByRole('link', { name: /அதிகாரபூர்வ இணையதளத்துக்குச் செல்/ })).toBeInTheDocument()
  expect(screen.getAllByText('ஒரு நபர் இன்னும் மீண்டும் சரிபார்க்கவில்லை.').length).toBeGreaterThan(0)
})

it('renders a career in Tamil', async () => {
  mockApi({ 'GET /careers/electrician': { body: career() } })
  await renderApp('/careers/electrician', 'ta')
  expect(await screen.findByText(/இந்தத் தேவைகள் வழக்கமானவை, அதிகாரபூர்வமானவை அல்ல/)).toBeInTheDocument()
})
