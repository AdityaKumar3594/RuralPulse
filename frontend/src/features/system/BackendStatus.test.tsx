import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import i18n from '../../i18n'
import { BackendStatus } from './BackendStatus'

beforeEach(async () => {
  await i18n.changeLanguage('en')
})

it('shows error state, and Retry refetches and renders ok', async () => {
  const fetchMock = vi
    .fn()
    .mockRejectedValue(new TypeError('offline'))
    .mockRejectedValueOnce(new TypeError('offline'))
  vi.stubGlobal('fetch', fetchMock)
  render(<BackendStatus />)

  expect(screen.getByRole('status')).toHaveTextContent('Connecting…')
  expect(await screen.findByText('Could not reach the server. Check your internet connection.', {}, { timeout: 3000 })).toBeInTheDocument()

  fetchMock.mockReset()
  fetchMock.mockResolvedValue(new Response(JSON.stringify({ status: 'ok', db: 'ok', version: '1.2.3' })))
  await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByText('Connected. Everything is working.')).toBeInTheDocument()
  expect(screen.getByText('Version 1.2.3')).toBeInTheDocument()
})

it('shows degraded when db is down', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: 'degraded', db: 'error', version: '1' }))))
  render(<BackendStatus />)
  expect(await screen.findByText(/database has a problem/)).toBeInTheDocument()
})
