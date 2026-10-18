import type { ReactElement } from 'react'
import type { RouteObject } from 'react-router'

export type Role = 'student' | 'facilitator' | 'partner' | 'admin'

export interface NavItem {
  to: string
  /** i18n key for the label */
  labelKey: string
  /** roles that see the link; routes are guarded separately */
  roles: Role[]
  order?: number
}

/**
 * A feature module describes everything a feature adds to the app, so features never edit
 * the shared router or layout. Put it in src/features/<name>/module.tsx (default export).
 */
export interface FeatureModule {
  id: string
  /** open to everyone */
  publicRoutes?: RouteObject[]
  /** signed-in students with valid consent */
  studentRoutes?: RouteObject[]
  /** signed-in facilitators / partners / admins; each route guards its own role via roles[] */
  staffRoutes?: { roles: Role[]; routes: RouteObject[] }[]
  navItems?: NavItem[]
  /** optional element rendered on the home page (e.g. a summary card) */
  homeWidget?: ReactElement
}

const modules = import.meta.glob('../features/*/module.tsx', { eager: true, import: 'default' }) as Record<
  string,
  FeatureModule
>

export const featureModules: FeatureModule[] = Object.values(modules).sort((a, b) =>
  a.id.localeCompare(b.id),
)

const coreNav: NavItem[] = [
  { to: '/interview', labelKey: 'home.interview', roles: ['student'], order: 10 },
  { to: '/profile', labelKey: 'home.profile', roles: ['student'], order: 20 },
]

export const navItems: NavItem[] = [...coreNav, ...featureModules.flatMap((m) => m.navItems ?? [])].sort(
  (a, b) => (a.order ?? 100) - (b.order ?? 100),
)

export const homeWidgets = featureModules.flatMap((m) => (m.homeWidget ? [{ id: m.id, element: m.homeWidget }] : []))
