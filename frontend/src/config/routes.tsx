import React, { lazy } from 'react';

/**
 * Lazy-loaded page components
 */
export const Dashboard = lazy(() => import('../pages/Dashboard'));
export const Login = lazy(() => import('../pages/Login'));
export const ChangePassword = lazy(() => import('../pages/ChangePassword'));
export const ClusterManagement = lazy(() => import('../pages/ClusterManagement'));
export const AddCluster = lazy(() => import('../pages/AddCluster'));
export const Inspection = lazy(() => import('../pages/Inspection'));
export const ScheduledInspection = lazy(() => import('../pages/ScheduledInspection'));
// Use RuleManagement component directly instead of Rules wrapper
export const Rules = lazy(() => import('../components/rules/RuleManagement'));
export const PopeyeScan = lazy(() => import('../pages/PopeyeScan'));
export const Reports = lazy(() => import('../pages/Reports'));
export const Help = lazy(() => import('../pages/Help'));
export const HelpIntroduction = lazy(() => import('../pages/HelpIntroduction'));
export const HelpExamples = lazy(() => import('../pages/HelpExamples'));
export const HelpSecurity = lazy(() => import('../pages/HelpSecurity'));
export const HelpKubeconfig = lazy(() => import('../pages/HelpKubeconfig'));
export const HelpApi = lazy(() => import('../pages/HelpApi'));
export const NetworkConnectivity = lazy(() => import('../pages/NetworkConnectivity'));
export const SecretManagement = lazy(() => import('../pages/SecretManagement'));
export const UserManagement = lazy(() => import('../pages/UserManagement'));
export const AuditLogs = lazy(() => import('../pages/AuditLogs'));

/**
 * Route configuration
 */
export interface RouteConfig {
  path: string;
  component: React.LazyExoticComponent<React.ComponentType>;
  isPublic?: boolean;
  requiresAuth?: boolean;
  protected?: boolean;
}

/**
 * Public routes (no authentication required)
 */
export const publicRoutes: RouteConfig[] = [
  {
    path: '/login',
    component: Login,
    isPublic: true,
  },
];

/**
 * Protected routes (authentication required)
 */
export const protectedRoutes: RouteConfig[] = [
  { path: '/', component: Dashboard, requiresAuth: true },
  { path: '/clusters', component: ClusterManagement, requiresAuth: true },
  { path: '/add-cluster', component: AddCluster, requiresAuth: true },
  { path: '/secrets', component: SecretManagement, requiresAuth: true, protected: true },
  { path: '/network', component: NetworkConnectivity, requiresAuth: true },
  { path: '/inspection', component: Inspection, requiresAuth: true },
  { path: '/scheduled-inspection', component: ScheduledInspection, requiresAuth: true },
  { path: '/rules', component: Rules, requiresAuth: true, protected: true },
  { path: '/popeye', component: PopeyeScan, requiresAuth: true },
  { path: '/reports', component: Reports, requiresAuth: true },
  { path: '/help', component: Help, requiresAuth: true },
  { path: '/help/introduction', component: HelpIntroduction, requiresAuth: true },
  { path: '/help/examples', component: HelpExamples, requiresAuth: true },
  { path: '/help/security', component: HelpSecurity, requiresAuth: true },
  { path: '/help/kubeconfig', component: HelpKubeconfig, requiresAuth: true },
  { path: '/help/api', component: HelpApi, requiresAuth: true },
  { path: '/change-password', component: ChangePassword, requiresAuth: true },
  { path: '/users', component: UserManagement, requiresAuth: true, protected: true },
  { path: '/audit-logs', component: AuditLogs, requiresAuth: true, protected: true },
];

/**
 * All routes combined
 */
export const allRoutes: RouteConfig[] = [...publicRoutes, ...protectedRoutes];
