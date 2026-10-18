import { useRoutes } from 'react-router'
import { featureModules } from '../app/registry'
import { Layout } from '../components/Layout'
import { RequireAuth, RequireConsent, RequireRole } from '../components/Guards'
import { LoginPage } from '../features/auth/LoginPage'
import { RegisterPage } from '../features/auth/RegisterPage'
import { ConsentPage } from '../features/consent/ConsentPage'
import { InterviewPage } from '../features/interview/InterviewPage'
import { ProfilePage } from '../features/profile/ProfilePage'
import { HomePage } from './HomePage'
import { LanguageSelectPage } from './LanguageSelectPage'
import { NotFoundPage } from './NotFoundPage'

/**
 * Core routes live here; everything else is contributed by feature modules
 * (src/features/<name>/module.tsx, collected in app/registry.ts).
 */
export function AppRoutes() {
  return useRoutes([
    {
      element: <Layout />,
      children: [
        { path: '/', element: <LanguageSelectPage /> },
        { path: '/home', element: <HomePage /> },
        { path: '/register', element: <RegisterPage /> },
        { path: '/login', element: <LoginPage /> },
        ...featureModules.flatMap((m) => m.publicRoutes ?? []),
        {
          element: <RequireAuth />,
          children: [
            { path: '/consent', element: <ConsentPage /> },
            {
              element: <RequireConsent />,
              children: [
                { path: '/interview', element: <InterviewPage /> },
                { path: '/profile', element: <ProfilePage /> },
                ...featureModules.flatMap((m) => m.studentRoutes ?? []),
              ],
            },
            ...featureModules.flatMap((m) =>
              (m.staffRoutes ?? []).map((group) => ({
                element: <RequireRole roles={group.roles} />,
                children: group.routes,
              })),
            ),
          ],
        },
        { path: '*', element: <NotFoundPage /> },
      ],
    },
  ])
}
