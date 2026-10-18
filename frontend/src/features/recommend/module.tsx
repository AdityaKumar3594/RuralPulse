import type { FeatureModule } from '../../app/registry'
import { RecommendPage } from './RecommendPage'

const recommend: FeatureModule = {
  id: 'recommend',
  studentRoutes: [{ path: '/recommendations', element: <RecommendPage /> }],
  navItems: [{ to: '/recommendations', labelKey: 'recommend.nav', roles: ['student'], order: 25 }],
}

export default recommend
