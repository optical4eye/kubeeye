import React, { useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { useRBAC } from '../hooks/useRBAC';
import { getRequiredRole } from '../config/rbac';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: 'admin' | 'operator';
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, requiredRole }) => {
  const { isAuthenticated, user, isLoading, checkAuth } = useAuthStore();
  const location = useLocation();
  const { canAccessRoute } = useRBAC();

  useEffect(() => {
    // Check auth on mount
    if (!checkAuth()) {
      // Redirect to login if not authenticated
      return;
    }
  }, [checkAuth]);

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Get required role from centralized config or use the provided requiredRole
  const configRequiredRole = getRequiredRole(location.pathname);
  const effectiveRequiredRole = requiredRole ?? configRequiredRole;

  // Check role if required
  if (effectiveRequiredRole && user) {
    const hasRequiredRole = canAccessRoute(location.pathname);

    if (!hasRequiredRole) {
      return <Navigate to="/unauthorized" replace />;
    }
  }

  return <>{children}</>;
};

export default ProtectedRoute;
