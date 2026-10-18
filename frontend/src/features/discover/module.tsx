import type { FeatureModule } from '../../app/registry'
import { CareerDetailPage } from './CareerDetailPage'
import { CareersPage } from './CareersPage'
import { OpportunityDetailPage } from './OpportunityDetailPage'
import { SearchPage } from './SearchPage'

const discover: FeatureModule = {
  id: 'discover',
  publicRoutes: [
    { path: '/search', element: <SearchPage /> },
    { path: '/careers', element: <CareersPage /> },
    { path: '/careers/:slug', element: <CareerDetailPage /> },
    { path: '/opportunities/:slug', element: <OpportunityDetailPage /> },
  ],
  navItems: [
    { to: '/search', labelKey: 'discover.nav.search', roles: ['student'], order: 45 },
    { to: '/careers', labelKey: 'discover.nav.careers', roles: ['student'], order: 55 },
  ],
}

export default discover
