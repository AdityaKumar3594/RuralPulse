import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it } from 'vitest'
import { mockApi, renderApp } from '../test/utils'

beforeEach(() => {
  localStorage.clear()
  mockApi({ 'GET /health': { body: { status: 'ok', db: 'ok', version: '1' } } })
})

it('shows both languages; choosing Tamil switches text, html lang and storage', async () => {
  await renderApp('/')
  const main = within(screen.getByRole('main'))
  expect(main.getByRole('button', { name: 'English' })).toBeInTheDocument()
  await userEvent.click(main.getByRole('button', { name: 'தமிழ்' }))
  expect(await screen.findByRole('heading', { level: 1, name: 'நாட்டோவுக்கு வரவேற்கிறோம்' })).toBeInTheDocument()
  expect(document.documentElement.lang).toBe('ta')
  expect(localStorage.getItem('Ruralpulse.lang')).toBe('ta')
})
