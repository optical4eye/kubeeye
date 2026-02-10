import { useMemo } from 'react';
import { useAuthStore } from '../stores/authStore';
import type { Role } from '../config/rbac';
import {
  hasPermission,
  canAccessRoute,
  getRequiredRole,
  getAccessibleRoutes,
} from '../config/rbac';

/**
 * Hook for RBAC (Role-Based Access Control) checks
 * Provides convenient methods to check permissions and access rights
 */
export function useRBAC() {
  const { user } = useAuthStore();
  const userRole: Role = (user?.role as Role) ?? 'operator';

  /**
   * Check if current user has a specific permission
   */
  const checkPermission = useMemo(
    () => (permission: string) => hasPermission(userRole, permission),
    [userRole]
  );

  /**
   * Check if current user can access a specific route
   */
  const checkRouteAccess = useMemo(
    () => (path: string) => canAccessRoute(userRole, path),
    [userRole]
  );

  /**
   * Get the minimum required role for a route
   */
  const getRouteRequiredRole = useMemo(() => (path: string) => getRequiredRole(path), []);

  /**
   * Get all routes accessible by current user
   */
  const getAccessibleRoutesForUser = useMemo(() => () => getAccessibleRoutes(userRole), [userRole]);

  /**
   * Check if current user is admin
   */
  const isAdmin = useMemo(() => userRole === 'admin', [userRole]);

  /**
   * Check if current user is operator
   */
  const isOperator = useMemo(() => userRole === 'operator', [userRole]);

  return {
    userRole,
    isAdmin,
    isOperator,
    hasPermission: checkPermission,
    canAccessRoute: checkRouteAccess,
    getRequiredRole: getRouteRequiredRole,
    getAccessibleRoutes: getAccessibleRoutesForUser,
  };
}
