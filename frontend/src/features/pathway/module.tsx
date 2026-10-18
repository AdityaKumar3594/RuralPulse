import type { FeatureModule } from '../../app/registry'
import { PathwayDetailPage } from './PathwayDetailPage'
import { PathwayListPage } from './PathwayListPage'

const pathway: FeatureModule = {
  id: 'pathway',
  studentRoutes: [
    { path: '/pathways', element: <PathwayListPage /> },
    { path: '/pathways/:id', element: <PathwayDetailPage /> },
  ],
  navItems: [{ to: '/pathways', labelKey: 'pathway.nav', roles: ['student'], order: 35 }],
}

export default pathway
