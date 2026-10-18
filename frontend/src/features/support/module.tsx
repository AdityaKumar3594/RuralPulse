import type { FeatureModule } from '../../app/registry'
import { SupportPage } from './SupportPage'

const support: FeatureModule = {
  id: 'support',
  studentRoutes: [{ path: '/teacher', element: <SupportPage /> }],
  navItems: [{ to: '/teacher', labelKey: 'support.nav', roles: ['student'], order: 60 }],
}

export default support
