// Shapes from backend/app/modules/training/schemas.py

export type PriceType = 'free' | 'per_module' | 'subscription'

export interface Lesson {
  title: string
  body: string
  url?: string | null
}

export interface TrainingModule {
  id: string
  title: string
  description: string
  language: 'ta' | 'en' | string
  status: 'draft' | 'published' | 'withdrawn' | string
  price_type: PriceType | string
  price_inr: number | null
  lesson_titles: string[]
  lessons: Lesson[] | null
  enrolled: boolean
  payment_status: 'not_required' | 'unpaid_no_gateway' | string | null
  access: boolean
  completed_lessons: number[]
  payments_available: boolean
  created_at: string
}

export interface FacilitatorModule {
  module: TrainingModule
  enrollments: number
}

export interface ModuleBody {
  title: string
  description: string
  language: 'ta' | 'en'
  lessons: { title: string; body: string; url: string | null }[]
  price_type: PriceType
  price_inr: number | null
}
