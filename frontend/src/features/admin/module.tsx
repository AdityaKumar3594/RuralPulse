import type { FeatureModule } from '../../app/registry'
import { AdminShell } from './AdminShell'
import { AssignmentsPage } from './AssignmentsPage'
import { OpportunityToolsPage } from './OpportunityToolsPage'
import { ProvidersPage } from './ProvidersPage'
import { ReviewDetailPage } from './ReviewDetailPage'
import { ReviewQueuePage } from './ReviewQueuePage'
import { UsersPage } from './UsersPage'

const admin: FeatureModule = {
  id: 'admin',
  staffRoutes: [
    {
      roles: ['admin'],
      routes: [
        {
          path: '/admin',
          element: <AdminShell />,
          children: [
            { index: true, element: <UsersPage /> },
            { path: 'assignments', element: <AssignmentsPage /> },
            { path: 'providers', element: <ProvidersPage /> },
            { path: 'review', element: <ReviewQueuePage /> },
            { path: 'review/:id', element: <ReviewDetailPage /> },
            { path: 'opportunities', element: <OpportunityToolsPage /> },
          ],
        },
      ],
    },
  ],
  navItems: [{ to: '/admin', labelKey: 'admin.nav', roles: ['admin'], order: 80 }],
}

export default admin
