// Fixtures shaped like the backend responses; used only by tests.
export const source = { id: 'src1', name: 'National Scholarship Portal', publisher: 'Govt of India', base_url: 'https://scholarships.gov.in' }

export const verification = (over: Record<string, unknown> = {}) => ({
  status: 'verified',
  verified_fields: ['url', 'eligibility'],
  verified_at: '2026-09-01',
  verified_by: 'reviewer',
  human_reviewed: false,
  evidence: [],
  ...over,
})

export const hit = (over: Record<string, unknown> = {}) => ({
  type: 'opportunity',
  id: 'merit-scholarship',
  title: 'Merit Scholarship',
  summary: 'Money for students with good marks.',
  match_type: 'exact',
  score: 3,
  group: 'scholarship',
  url: 'https://scholarships.gov.in/merit',
  source,
  freshness: 'fresh',
  verification: verification(),
  eligibility_known: true,
  flags: [],
  language_fallback: false,
  ...over,
})

export const searchResponse = (over: Record<string, unknown> = {}) => ({
  query: 'scholarship',
  language: 'en',
  search_mode: 'keyword',
  status: 'ok',
  message: null,
  results: [hit()],
  ...over,
})

export const opportunity = (over: Record<string, unknown> = {}) => ({
  slug: 'merit-scholarship',
  kind: 'scholarship',
  title: 'Merit Scholarship',
  url: 'https://scholarships.gov.in/merit',
  summary: 'Money for students with good marks.',
  provider: 'Ministry of Education',
  source,
  scope: { level: 'national', states: [] },
  eligibility: { education_stages: ['class_10', 'class_12'], max_family_income_inr_per_year: 250000, other_criteria: ['Studying in a government school'], text: null },
  required_documents: [],
  application_deadline: null,
  expires_on: null,
  benefits: [],
  verification: verification(),
  freshness: 'fresh',
  flags: ['not_human_reviewed', 'deadline_unknown'],
  language: 'en',
  language_fallback: false,
  ...over,
})

export const career = (over: Record<string, unknown> = {}) => ({
  slug: 'electrician',
  family: 'skilled_trades',
  title: 'Electrician',
  description: 'Installs and fixes wiring.',
  activities: ['Fix wiring', 'Read circuit diagrams'],
  skills: ['Safety', 'Measuring'],
  entry: { typical_min_stage: 'class_10', notes: 'Most people join an ITI after Class 10.' },
  routes: [
    { kind: 'iti', title: 'ITI course', min_stage: 'class_10', opportunity: null },
    {
      kind: 'self_learning',
      title: 'Learn online',
      min_stage: null,
      opportunity: { slug: 'national-learning-platform', kind: 'platform', title: 'National Learning Platform', url: 'https://learn.example.gov.in' },
    },
  ],
  related: [{ slug: 'plumber', family: 'skilled_trades', title: 'Plumber' }],
  learning_resources: [{ slug: 'national-learning-platform', kind: 'platform', title: 'National Learning Platform', url: 'https://learn.example.gov.in' }],
  source_refs: [],
  verification_status: 'unverified',
  human_reviewed: false,
  localization_status: 'complete',
  language: 'en',
  language_fallback: false,
  ...over,
})
