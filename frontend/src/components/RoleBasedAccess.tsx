import React from 'react';
import { useAuthStore } from '../stores/authStore';
import { useRBAC } from '../hooks/useRBAC';
import type { Role } from '../config/rbac';

interface RoleBasedAccessProps {
  children: React.ReactNode;
  allowedRoles?: Role[];
  fallback?: React.ReactNode;
}

const RoleBasedAccess: React.FC<RoleBasedAccessProps> = ({
  children,
  allowedRoles,
  fallback = null,
}) => {
  const { user } = useAuthStore();
  const { userRole } = useRBAC();

  if (!user) {
    return <>{fallback}</>;
  }

  // If allowedRoles is not provided, use the centralized RBAC config
  // Otherwise, check against the provided roles
  const hasAccess = allowedRoles ? allowedRoles.includes(userRole) : true;

  return hasAccess ? <>{children}</> : <>{fallback}</>;
};

export default RoleBasedAccess;
