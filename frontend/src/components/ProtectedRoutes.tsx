import React, { Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Spin } from 'antd';
import ProtectedRoute from './ProtectedRoute';
import { protectedRoutes } from '../config/routes';

/**
 * Component that renders all protected routes with Suspense and ProtectedRoute wrappers
 */
const ProtectedRoutes = () => {
  return (
    <Suspense
      fallback={
        <div className="loading-spinner">
          <Spin size="large" />
        </div>
      }
    >
      <Routes>
        {protectedRoutes.map(route => (
          <Route
            key={route.path}
            path={route.path}
            element={
              route.protected ? (
                <ProtectedRoute>
                  <route.component />
                </ProtectedRoute>
              ) : (
                <route.component />
              )
            }
          />
        ))}
      </Routes>
    </Suspense>
  );
};

export default ProtectedRoutes;
