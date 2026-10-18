import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it } from 'vitest'
import { consentStatus, loginAs, mockApi, renderApp, session } from '../../test/utils'

const noConsent = (given: 'self' | 'guardian') =>
  consentStatus({ required_given_by: given, active: null })

/** Consent status that turns valid once POST /consents has been called, like the real server. */
function statefulConsent(given: 'self' | 'guardian') {
  let granted = false
  return {
    'GET /consents/me': () => ({
      body: granted ? consentStatus({ required_given_by: given, active: { ...consentStatus().active, given_by: given } }) : noConsent(given),
    }),
    'POST /consents': () => {
      granted = true
      return { status: 201, body: {} }
    },
  }
}

it('adults give their own consent (no guardian fields)', async () => {
  loginAs()
  const api = mockApi({
    ...statefulConsent('self'),
    'POST /interview/sessions': { body: session() },
  })
  await renderApp('/consent')
  await screen.findByRole('heading', { name: 'Your permission' })
  expect(screen.queryByLabelText(/Parent or guardian/)).not.toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: 'Continue' }))
  expect(screen.getByText('Please tick the box to continue.')).toBeInTheDocument()
  expect(api.count('POST /consents')).toBe(0)

  await userEvent.click(screen.getByLabelText('I agree to this'))
  await userEvent.click(screen.getByRole('button', { name: 'Continue' }))
  expect(await screen.findByText('Which class or course are you in now?')).toBeInTheDocument()
  expect(api.calls.find((c) => c.path === '/consents')?.body).toEqual({ given_by: 'self' })
})

it('students under 18 need guardian details and a guardian agreement', async () => {
  loginAs()
  const api = mockApi({
    ...statefulConsent('guardian'),
    'POST /interview/sessions': { body: session() },
  })
  await renderApp('/consent')
  expect(await screen.findByText(/You are under 18/)).toBeInTheDocument()

  await userEvent.click(screen.getByLabelText('I am the parent or guardian and I agree'))
  await userEvent.click(screen.getByRole('button', { name: 'Continue' }))
  expect(screen.getByText("Please enter the parent or guardian's name.")).toBeInTheDocument()
  expect(screen.getByText(/10-digit mobile number/)).toBeInTheDocument()
  expect(api.count('POST /consents')).toBe(0)

  await userEvent.type(screen.getByLabelText("Parent or guardian's name"), 'Meena')
  await userEvent.type(screen.getByLabelText("Parent or guardian's mobile number"), '9123456789')
  await userEvent.click(screen.getByRole('button', { name: 'Continue' }))
  await screen.findByText('Which class or course are you in now?')
  expect(api.calls.find((c) => c.path === '/consents')?.body).toEqual({
    given_by: 'guardian',
    guardian_name: 'Meena',
    guardian_phone: '9123456789',
  })
})

it('does not claim the guardian was verified', async () => {
  loginAs()
  mockApi({ 'GET /consents/me': { body: noConsent('guardian') } })
  await renderApp('/consent')
  await screen.findByText(/You are under 18/)
  expect(screen.queryByText(/verified/i)).not.toBeInTheDocument()
})

it('consent made by the wrong person does not unlock the app', async () => {
  loginAs()
  // A minor whose active consent was somehow given by "self" is still sent to the consent page.
  mockApi({
    'GET /consents/me': {
      body: consentStatus({ required_given_by: 'guardian' }), // active.given_by === 'self'
    },
  })
  await renderApp('/interview')
  expect(await screen.findByRole('heading', { name: 'Your permission' })).toBeInTheDocument()
})

it('guards: logged-out visitors are sent to login, and consent is checked before the interview', async () => {
  const api = mockApi({})
  await renderApp('/interview')
  expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
  expect(api.calls).toHaveLength(0)
})

it('guards: with consent the interview opens', async () => {
  loginAs()
  mockApi({
    'GET /consents/me': { body: consentStatus() },
    'POST /interview/sessions': { body: session() },
  })
  await renderApp('/interview')
  expect(await screen.findByText('Which class or course are you in now?')).toBeInTheDocument()
})

it('an expired session (401 with a token) logs the student out and returns to login', async () => {
  loginAs()
  mockApi({ 'GET /consents/me': { status: 401, body: { detail: 'Not authenticated' } } })
  await renderApp('/interview')
  expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
  expect(sessionStorage.getItem('Ruralpulse.token')).toBeNull()
})
