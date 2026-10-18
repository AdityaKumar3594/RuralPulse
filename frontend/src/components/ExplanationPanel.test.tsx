import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it } from 'vitest'
import i18n from '../i18n'
import { mockApi } from '../test/utils'
import { ExplanationPanel } from './ExplanationPanel'

const out = (over: Record<string, unknown> = {}, fields: Record<string, unknown> = {}) => ({
  id: 'x1',
  kind: 'eligibility',
  language: 'en',
  source: 'template',
  fallback_reason: 'ai_not_configured',
  model: null,
  cached: false,
  explanation: {
    headline: 'You meet the rules we could check',
    why: ['Your class matches', 'Your age matches'],
    requirements: ['Class 10 or 12'],
    eligibility_status: 'ELIGIBLE',
    freshness_note: 'Checked on 1 Sep 2026',
    missing_information: ['Your family income'],
    next_action: 'Read the official page',
    ...fields,
  },
  sources: [
    { title: 'Merit Scholarship', url: 'https://scholarships.gov.in/merit', freshness: 'stale' },
    { title: 'Bad link', url: 'javascript:alert(1)', freshness: 'fresh' },
  ],
  created_at: 'x',
  ...over,
})

const request = { kind: 'eligibility', evaluation_id: 'e1' } as const

it('shows every part of the explanation, the sources, and the standard-wording label', async () => {
  await i18n.changeLanguage('en')
  const api = mockApi({ 'POST /explanations': { body: out() } })
  render(<ExplanationPanel request={request} />)
  await userEvent.click(screen.getByRole('button', { name: 'Explain in simple words' }))

  const panel = (await screen.findByText(/You meet the rules we could check/)).closest('section')!
  expect(api.calls[0].body).toEqual({ kind: 'eligibility', evaluation_id: 'e1', language: 'en' })
  expect(within(panel).getByText('Standard wording')).toBeInTheDocument()
  expect(within(panel).queryByText('Written by AI from checked facts')).not.toBeInTheDocument()
  expect(within(panel).getByText('Your class matches')).toBeInTheDocument()
  expect(within(panel).getByText('Your age matches')).toBeInTheDocument()
  expect(within(panel).getByText('Class 10 or 12')).toBeInTheDocument()
  expect(within(panel).getByText('Meets the rules we could check')).toBeInTheDocument()
  expect(within(panel).getByText('Checked on 1 Sep 2026')).toBeInTheDocument()
  expect(within(panel).getByText('Your family income')).toBeInTheDocument()
  expect(within(panel).getByText('Read the official page')).toBeInTheDocument()
  const link = within(panel).getByRole('link', { name: /Merit Scholarship/ })
  expect(link).toHaveAttribute('href', 'https://scholarships.gov.in/merit')
  expect(link).toHaveAttribute('target', '_blank')
  expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  expect(within(panel).getByText('Check is old')).toBeInTheDocument()
  // A non-web address is never made clickable.
  expect(within(panel).queryByRole('link', { name: /Bad link/ })).not.toBeInTheDocument()
  expect(screen.getByRole('heading', { name: /In simple words/ })).toHaveFocus()
})

it('labels AI-written text as written by AI from checked facts, not as certain', async () => {
  await i18n.changeLanguage('en')
  mockApi({ 'POST /explanations': { body: out({ source: 'ai', fallback_reason: null, model: 'm' }) } })
  render(<ExplanationPanel request={request} />)
  await userEvent.click(screen.getByRole('button', { name: 'Explain in simple words' }))
  expect(await screen.findByText('Written by AI from checked facts')).toBeInTheDocument()
  expect(screen.queryByText('Standard wording')).not.toBeInTheDocument()
})

it('hides the eligibility result when it does not apply and omits empty parts', async () => {
  await i18n.changeLanguage('en')
  mockApi({
    'POST /explanations': {
      body: out({ sources: [] }, { eligibility_status: 'NOT_APPLICABLE', why: [], requirements: [], missing_information: [], freshness_note: '' }),
    },
  })
  render(<ExplanationPanel request={{ kind: 'pathway', plan_id: 'p1' }} />)
  await userEvent.click(screen.getByRole('button', { name: 'Explain in simple words' }))
  await screen.findByText(/You meet the rules we could check/)
  expect(screen.queryByText('Eligibility result')).not.toBeInTheDocument()
  expect(screen.queryByText('Why')).not.toBeInTheDocument()
  expect(screen.queryByText('Sources')).not.toBeInTheDocument()
  expect(screen.queryByText('What we still need to know')).not.toBeInTheDocument()
})

it('shows a loading message, then an error with retry that works', async () => {
  await i18n.changeLanguage('en')
  let n = 0
  let release: () => void = () => {}
  const gate = new Promise<void>((r) => (release = r))
  mockApi({
    'POST /explanations': async () => {
      if (++n === 1) {
        await gate
        return { status: 404, body: { detail: 'not_found' } }
      }
      return { body: out() }
    },
  })
  render(<ExplanationPanel request={request} />)
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: 'Explain in simple words' }))
  expect(screen.getByRole('status')).toHaveTextContent('Writing a simple explanation')
  expect(screen.getByRole('button', { name: 'Explain in simple words' })).toBeDisabled()
  release()
  expect(await screen.findByRole('alert')).toHaveTextContent('We could not find that.')
  await user.click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByText(/You meet the rules we could check/)).toBeInTheDocument()
  expect(n).toBe(2)
})

it('shows a network error with retry', async () => {
  await i18n.changeLanguage('en')
  mockApi({ 'POST /explanations': 'network-error' })
  render(<ExplanationPanel request={request} />)
  await userEvent.click(screen.getByRole('button', { name: 'Explain in simple words' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not reach the server')
  expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
})

it('forgets an old explanation when the request changes', async () => {
  await i18n.changeLanguage('en')
  mockApi({ 'POST /explanations': { body: out() } })
  const { rerender } = render(<ExplanationPanel request={request} />)
  await userEvent.click(screen.getByRole('button', { name: 'Explain in simple words' }))
  await screen.findByText(/You meet the rules we could check/)
  rerender(<ExplanationPanel request={{ kind: 'eligibility', evaluation_id: 'e2' }} />)
  expect(screen.getByRole('button', { name: 'Explain in simple words' })).toBeInTheDocument()
  expect(screen.queryByText(/You meet the rules we could check/)).not.toBeInTheDocument()
})

it('works in Tamil and asks for a Tamil explanation', async () => {
  await i18n.changeLanguage('ta')
  const api = mockApi({ 'POST /explanations': { body: out({ source: 'ai', language: 'ta' }) } })
  render(<ExplanationPanel request={request} />)
  await userEvent.click(screen.getByRole('button', { name: 'எளிய சொற்களில் விளக்கு' }))
  expect(await screen.findByText('சரிபார்த்த உண்மைகளிலிருந்து AI எழுதியது')).toBeInTheDocument()
  expect(screen.getByText('நாங்கள் சரிபார்த்த விதிகளுக்குப் பொருந்துகிறது')).toBeInTheDocument()
  expect(api.calls[0].body).toMatchObject({ language: 'ta' })
})
