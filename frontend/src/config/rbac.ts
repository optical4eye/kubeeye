/**
 * RBAC Configuration for Frontend
 * Centralized role-based access control configuration
 */

export type Role = 'admin' | 'operator';

export interface RoutePermission {
  path: string;
  requiredRole?: Role;
  allowedRoles?: Role[];
}

export interface RoleConfig {
  name: Role;
  label: string;
  permissions: string[];
}

/**
 * Role definitions
 */
export const ROLES: Record<Role, RoleConfig> = {
  admin: {
    name: 'admin',
    label: 'Admin',
    permissions: [
      'view:dashboard',
      'view:clusters',
      'view:network',
      'view:inspection',
      'view:popeye',
      'view:reports',
      'view:rules',
      'view:secrets',
      'view:users',
      'view:audit-logs',
      'view:help',
      'manage:clusters',
      'manage:rules',
      'manage:secrets',
      'manage:users',
      'manage:audit-logs',
    ],
  },
  operator: {
    name: 'operator',
    label: 'Operator',
    permissions: [
      'view:dashboard',
      'view:clusters',
      'view:network',
      'view:inspection',
      'view:popeye',
      'view:reports',
      'view:rules',
      'view:help',
      'manage:clusters',
      'manage:rules',
    ],
  },
};

/**
 * Route permissions configuration
 * Maps routes to required roles
 */
export const ROUTE_PERMISSIONS: RoutePermission[] = [
  { path: '/', allowedRoles: ['admin', 'operator'] },
  { path: '/clusters', allowedRoles: ['admin', 'operator'] },
  { path: '/add-cluster', allowedRoles: ['admin'] },
  { path: '/network', allowedRoles: ['admin', 'operator'] },
  { path: '/inspection', allowedRoles: ['admin', 'operator'] },
  { path: '/scheduled-inspection', allowedRoles: ['admin', 'operator'] },
  { path: '/popeye', allowedRoles: ['admin', 'operator'] },
  { path: '/reports', allowedRoles: ['admin', 'operator'] },
  { path: '/rules', allowedRoles: ['admin', 'operator'] },
  { path: '/secrets', allowedRoles: ['admin'] },
  { path: '/users', allowedRoles: ['admin'] },
  { path: '/audit-logs', allowedRoles: ['admin'] },
  { path: '/help', allowedRoles: ['admin', 'operator'] },
  { path: '/help/introduction', allowedRoles: ['admin', 'operator'] },
  { path: '/help/examples', allowedRoles: ['admin', 'operator'] },
  { path: '/help/security', allowedRoles: ['admin', 'operator'] },
  { path: '/help/kubeconfig', allowedRoles: ['admin', 'operator'] },
  { path: '/help/api', allowedRoles: ['admin', 'operator'] },
];

/**
 * Check if a role has a specific permission
 */
export function hasPermission(role: Role, permission: string): boolean {
  return ROLES[role]?.permissions.includes(permission) ?? false;
}

/**
 * Check if a role can access a specific route
 */
export function canAccessRoute(role: Role, path: string): boolean {
  const routeConfig = ROUTE_PERMISSIONS.find(r => r.path === path);
  if (!routeConfig) {
    // If route is not configured, allow access by default
    return true;
  }
  return routeConfig.allowedRoles?.includes(role) ?? true;
}

/**
 * Get the minimum required role for a route
 */
export function getRequiredRole(path: string): Role | null {
  const routeConfig = ROUTE_PERMISSIONS.find(r => r.path === path);
  if (!routeConfig || !routeConfig.allowedRoles) {
    return null;
  }
  // Return the most restrictive role (admin is more restrictive than operator)
  if (routeConfig.allowedRoles.includes('admin')) {
    return 'admin';
  }
  return routeConfig.allowedRoles[0] ?? null;
}

/**
 * Get all routes accessible by a role
 */
export function getAccessibleRoutes(role: Role): string[] {
  return ROUTE_PERMISSIONS.filter(route => route.allowedRoles?.includes(role) ?? true).map(
    route => route.path
  );
}

/**
 * Get all available roles
 */
export function getAllRoles(): Role[] {
  return Object.keys(ROLES) as Role[];
}

/**
 * Get role display label
 */
export function getRoleLabel(role: string): string {
  return ROLES[role as Role]?.label || role;
}

/**
 * Get role color for display
 */
export function getRoleColor(role: string): string {
  const roleColors: Record<string, string> = {
    admin: 'red',
    operator: 'blue',
  };
  return roleColors[role] || 'default';
}
