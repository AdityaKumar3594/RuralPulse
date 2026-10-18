import type { FeatureModule } from '../../app/registry'
import { ApplicationsPage } from './ApplicationsPage'
import { PartnerShell } from './PartnerShell'
import { ProviderPage } from './ProviderPage'
import { SubmissionFormPage } from './SubmissionFormPage'
import { SubmissionsPage } from './SubmissionsPage'

const partner: FeatureModule = {
  id: 'partner',
  staffRoutes: [
    {
      roles: ['partner'],
      routes: [
        {
          path: '/partner',
          element: <PartnerShell />,
          children: [
            { index: true, element: <ProviderPage /> },
            { path: 'submissions', element: <SubmissionsPage /> },
            { path: 'submissions/new', element: <SubmissionFormPage /> },
            { path: 'submissions/:id', element: <SubmissionFormPage /> },
            { path: 'applications', element: <ApplicationsPage /> },
          ],
        },
      ],
    },
  ],
  navItems: [{ to: '/partner', labelKey: 'partner.nav', roles: ['partner'], order: 85 }],
}

export default partner
