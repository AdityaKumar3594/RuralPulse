import { apiGet, type ApiGetOptions } from './client'

export interface Health {
  status: 'ok' | 'degraded'
  db: 'ok' | 'error'
  version: string
}

export function getHealth(options?: ApiGetOptions): Promise<Health> {
  return apiGet<Health>('/health', options)
}
