// Shapes from backend/app/modules/applications/schemas.py

export type InternalStatus = 'saved' | 'preparing' | 'documents_ready' | 'applied' | 'withdrawn'
export type ExternalStatus = 'unknown' | 'submitted' | 'under_review' | 'accepted' | 'rejected'
export type ReportableStatus = ExternalStatus

export interface Application {
  id: string
  opportunity: { slug: string; title: string | null; url: string | null; kind: string; freshness: string | null }
  internal_status: InternalStatus
  note: string | null
  documents: Record<string, boolean>
  external_status: ExternalStatus
  external_status_source: 'student_reported' | 'facilitator_confirmed' | 'provider_confirmed' | null
  external_confirmed: boolean
  external_status_at: string | null
  external_status_note: string | null
  reference_code: string
  created_at: string
  updated_at: string
}

export const STEPS: InternalStatus[] = ['saved', 'preparing', 'documents_ready', 'applied']

/** Mirrors the server's allowed moves; the server still has the final say (409). */
export const TRANSITIONS: Record<InternalStatus, InternalStatus[]> = {
  saved: ['preparing', 'withdrawn'],
  preparing: ['saved', 'documents_ready', 'applied', 'withdrawn'],
  documents_ready: ['preparing', 'applied', 'withdrawn'],
  applied: ['withdrawn'],
  withdrawn: ['saved'],
}
