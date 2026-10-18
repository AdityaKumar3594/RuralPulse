import type { FeatureModule } from '../../app/registry'
import { ApplicationDetailPage } from './ApplicationDetailPage'
import { ApplicationsPage } from './ApplicationsPage'

const applications: FeatureModule = {
  id: 'applications',
  studentRoutes: [
    { path: '/applications', element: <ApplicationsPage /> },
    { path: '/applications/:id', element: <ApplicationDetailPage /> },
  ],
  navItems: [{ to: '/applications', labelKey: 'applications.nav', roles: ['student'], order: 50 }],
}

export default applications
