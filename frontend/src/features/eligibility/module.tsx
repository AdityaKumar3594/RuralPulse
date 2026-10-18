import type { FeatureModule } from '../../app/registry'
import { EligibilityPage } from './EligibilityPage'

const eligibility: FeatureModule = {
  id: 'eligibility',
  studentRoutes: [{ path: '/eligibility/:slug', element: <EligibilityPage /> }],
}

export default eligibility
