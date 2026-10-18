import type { FeatureModule } from '../../app/registry'
import { DashboardPage } from './DashboardPage'
import { StudentPage } from './StudentPage'

const facilitator: FeatureModule = {
  id: 'facilitator',
  staffRoutes: [
    {
      roles: ['facilitator'],
      routes: [
        { path: '/facilitator', element: <DashboardPage /> },
        { path: '/facilitator/students/:id', element: <StudentPage /> },
      ],
    },
  ],
  navItems: [{ to: '/facilitator', labelKey: 'facilitator.nav', roles: ['facilitator'], order: 10 }],
}

export default facilitator
