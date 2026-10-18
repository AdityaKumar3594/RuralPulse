import type { FeatureModule } from '../../app/registry'
import { FacilitatorModuleFormPage } from './FacilitatorModuleFormPage'
import { FacilitatorModulesPage } from './FacilitatorModulesPage'
import { ModuleDetailPage } from './ModuleDetailPage'
import { ModulesPage } from './ModulesPage'

const training: FeatureModule = {
  id: 'training',
  studentRoutes: [
    { path: '/modules', element: <ModulesPage /> },
    { path: '/modules/:id', element: <ModuleDetailPage /> },
  ],
  staffRoutes: [
    {
      roles: ['facilitator'],
      routes: [
        { path: '/facilitator/modules', element: <FacilitatorModulesPage /> },
        { path: '/facilitator/modules/new', element: <FacilitatorModuleFormPage /> },
        { path: '/facilitator/modules/:id', element: <FacilitatorModuleFormPage /> },
      ],
    },
  ],
  navItems: [
    { to: '/modules', labelKey: 'training.nav', roles: ['student'], order: 55 },
    { to: '/facilitator/modules', labelKey: 'training.navMine', roles: ['facilitator'], order: 70 },
  ],
}

export default training
