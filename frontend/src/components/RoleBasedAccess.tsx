import React from 'react';
import { useAuthStore } from '../stores/authStore';

interface RoleBasedAccessProps {
  children: React.ReactNode;
  allowedRoles?: ('admin' | 'operator')[];
  fallback?: React.ReactNode;
}

const RoleBasedAccess: React.FC<RoleBasedAccessProps> = ({
  children,
  allowedRoles = ['admin', 'operator'],
  fallback = null
}) => {
  const { user } = useAuthStore();

  if (!user) {
    return <>{fallback}</>;
  }

  const hasAccess = allowedRoles.includes(user.role as 'admin' | 'operator');

  return hasAccess ? <>{children}</> : <>{fallback}</>;
};

export default RoleBasedAccess;
