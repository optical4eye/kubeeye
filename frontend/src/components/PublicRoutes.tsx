import React, { Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Spin } from 'antd';
import { publicRoutes } from '../config/routes';

/**
 * Component that renders all public routes with Suspense wrapper
 */
const PublicRoutes = () => {
  return (
    <Suspense fallback={<Spin size="large" />}>
      <Routes>
        {publicRoutes.map(route => (
          <Route key={route.path} path={route.path} element={<route.component />} />
        ))}
      </Routes>
    </Suspense>
  );
};

export default PublicRoutes;
