import { fireEvent, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it } from 'vitest'
import { consentStatus, mockApi, renderApp, USER } from '../../test/utils'

const token = { access_token: 'tok', token_type: 'bearer', user: USER }

async function fillRegister(over: Partial<Record<'name' | 'phone' | 'pin' | 'dob', string>> = {}) {
  const v = { name: 'Asha', phone: '9876543210', pin: '1234', dob: '2000-01-01', ...over }
  await userEvent.type(screen.getByLabelText('Your name'), v.name)
  await userEvent.type(screen.getByLabelText(/Mobile number/), v.phone)
  await userEvent.type(screen.getByLabelText(/^PIN/), v.pin)
  if (v.dob) fireEvent.change(screen.getByLabelText('Date of birth'), { target: { value: v.dob } })
  await userEvent.click(screen.getByRole('button', { name: 'Create account' }))
}

it('register: shows validation errors and does not call the server', async () => {
  const api = mockApi({})
  await renderApp('/register')
  await userEvent.click(screen.getByRole('button', { name: 'Create account' }))
  expect(screen.getByText('Please enter your name.')).toBeInTheDocument()
  expect(screen.getByText(/10-digit mobile number starting with 6, 7, 8 or 9/)).toBeInTheDocument()
  expect(screen.getByText('Enter a PIN with 4 to 6 digits.')).toBeInTheDocument()
  expect(screen.getByText('Please enter your date of birth.')).toBeInTheDocument()
  expect(api.calls).toHaveLength(0)
})

it('register: rejects a phone number that does not start with 6-9 or a short PIN', async () => {
  const api = mockApi({})
  await renderApp('/register')
  await fillRegister({ phone: '1234567890', pin: '12' })
  expect(screen.getByText(/starting with 6, 7, 8 or 9/)).toBeInTheDocument()
  expect(screen.getByText('Enter a PIN with 4 to 6 digits.')).toBeInTheDocument()
  expect(api.calls).toHaveLength(0)
})

it('register: sends the details with the UI language, keeps the token for this tab, and goes to consent', async () => {
  const api = mockApi({
    'POST /auth/register': { status: 201, body: token },
    'GET /consents/me': { body: consentStatus({ active: null }) },
  })
  await renderApp('/register', 'ta')
  await userEvent.type(screen.getByLabelText('உங்கள் பெயர்'), 'Asha')
  await userEvent.type(screen.getByLabelText(/கைபேசி எண்/), '9876543210')
  await userEvent.type(screen.getByLabelText(/^ரகசிய எண்/), '1234')
  fireEvent.change(screen.getByLabelText('பிறந்த தேதி'), { target: { value: '2000-01-01' } })
  await userEvent.click(screen.getByRole('button', { name: 'கணக்கை உருவாக்கு' }))

  expect(await screen.findByRole('heading', { name: 'உங்கள் ஒப்புதல்' })).toBeInTheDocument()
  expect(api.calls[0].body).toEqual({
    display_name: 'Asha',
    phone: '9876543210',
    pin: '1234',
    date_of_birth: '2000-01-01',
    preferred_language: 'ta',
  })
  expect(sessionStorage.getItem('Ruralpulse.token')).toBe('tok')
  expect(localStorage.getItem('Ruralpulse.token')).toBeNull() // not kept after the tab closes
})

it('register: tells the student when the phone number is already registered', async () => {
  mockApi({ 'POST /auth/register': { status: 409, body: { detail: 'phone_already_registered' } } })
  await renderApp('/register')
  await fillRegister()
  expect(await screen.findByText(/already has an account/)).toBeInTheDocument()
  expect(sessionStorage.getItem('Ruralpulse.token')).toBeNull()
})

it('register: a connection failure shows a network message and allows another try', async () => {
  const api = mockApi({ 'POST /auth/register': 'network-error' })
  await renderApp('/register')
  await fillRegister()
  expect(await screen.findByText(/Could not reach the server/)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Create account' })).toBeEnabled()
  expect(api.count('POST /auth/register')).toBe(1) // not auto-retried
})

it('login: success greets the student and switches to their language', async () => {
  mockApi({
    'POST /auth/login': { body: { ...token, user: { ...USER, preferred_language: 'ta' } } },
    'GET /health': { body: { status: 'ok', db: 'ok', version: '1' } },
  })
  await renderApp('/login')
  await userEvent.type(screen.getByLabelText(/Mobile number/), '9876543210')
  await userEvent.type(screen.getByLabelText(/^PIN/), '1234')
  await userEvent.click(screen.getByRole('button', { name: 'Log in' }))
  expect(await screen.findByRole('heading', { level: 1, name: 'வணக்கம், Asha' })).toBeInTheDocument()
})

it.each([
  [401, 'invalid_credentials', 'Wrong mobile number or PIN.'],
  [429, 'account_locked', 'Too many wrong attempts. Please try again in 15 minutes.'],
])('login: %i shows a clear message', async (status, detail, text) => {
  mockApi({ 'POST /auth/login': { status, body: { detail } } })
  await renderApp('/login')
  await userEvent.type(screen.getByLabelText(/Mobile number/), '9876543210')
  await userEvent.type(screen.getByLabelText(/^PIN/), '9999')
  await userEvent.click(screen.getByRole('button', { name: 'Log in' }))
  expect(await screen.findByText(text)).toBeInTheDocument()
  expect(sessionStorage.getItem('Ruralpulse.token')).toBeNull()
})
