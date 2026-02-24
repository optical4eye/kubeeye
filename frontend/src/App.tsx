import React, { useState, useEffect, useMemo, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Layout, ConfigProvider, App as AntdApp, theme as antdTheme, Spin } from 'antd';
import { useTranslation } from 'react-i18next';
import LoadingScreen from './components/ui/LoadingScreen';
import { useUIStore } from './stores/uiStore';
import { getThemeConfig } from './theme/themeConfig';
import { useSystemStatusWebSocket } from './hooks/useSystemStatusWebSocket';
import { useRBAC } from './hooks/useRBAC';
import { useMenuNavigation } from './hooks/useMenuNavigation';
import { createMenuItems } from './config/menuConfig';
import ProtectedRoute from './components/ProtectedRoute';
import Sidebar from './components/Sidebar';
import AppHeader from './components/AppHeader';
import ProtectedRoutes from './components/ProtectedRoutes';
import { MenuItem } from './types/menu';
import { MIN_LOADING_TIME } from './config/constants';
import { Login } from './config/routes';

const { Content } = Layout;

function App() {
  const { theme, setTheme: _setTheme, language, setLanguage: _setLanguage } = useUIStore();
  const { t, i18n } = useTranslation();
  const [minLoadingTimePassed, setMinLoadingTimePassed] = useState(false);
  const { canAccessRoute } = useRBAC();

  // Create all menu items using configuration
  const allMenuItems = useMemo(() => createMenuItems(t), [t]);

  // Filter menu items based on user's role
  const menuItems = useMemo(
    () =>
      allMenuItems
        .map((group: MenuItem) => ({
          ...group,
          children: group.children?.filter((child: MenuItem) => canAccessRoute(child.key)) ?? [],
        }))
        .filter((group: MenuItem) => (group.children?.length ?? 0) > 0),
    [allMenuItems, canAccessRoute]
  );

  // Use menu navigation hook
  const menuNavigation = useMenuNavigation(menuItems);

  useEffect(() => {
    i18n.changeLanguage(language);
  }, [language, i18n]);

  // Use WebSocket for real-time system status
  const { isReady, message, subMessage, isConnecting } = useSystemStatusWebSocket();

  // Show loading screen if backend is not ready
  const isSystemReady = isReady; // Use only WebSocket status

  // Ensure minimum loading time for initial load
  useEffect(() => {
    const timer = setTimeout(() => {
      setMinLoadingTimePassed(true);
    }, MIN_LOADING_TIME);

    return () => clearTimeout(timer);
  }, []);

  return (
    <ConfigProvider
      theme={{
        ...getThemeConfig(theme === 'dark'),
        algorithm: theme === 'dark' ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
      }}
    >
      <AntdApp>
        {(() => {
          // Show loading screen during initial minimum time
          if (!minLoadingTimePassed) {
            return (
              <LoadingScreen
                message={message || t('loading.connecting')}
                subMessage={subMessage || t('loading.pleaseWait')}
                isConnecting={isConnecting}
              />
            );
          }

          // Show loading screen if backend is not ready
          if (!isSystemReady) {
            return (
              <LoadingScreen
                message={message || t('loading.connectionProblem')}
                subMessage={subMessage || t('loading.restoringConnection')}
                isConnecting={!isReady}
              />
            );
          }

          return (
            <Router>
              <div className="app-container">
                <Routes>
                  {/* Public routes - no layout */}
                  <Route
                    path="/login"
                    element={
                      <Suspense fallback={<Spin size="large" />}>
                        <Login />
                      </Suspense>
                    }
                  />

                  {/* Protected routes - with layout */}
                  <Route
                    path="/*"
                    element={
                      <ProtectedRoute>
                        <Layout className="main-layout">
                          <Sidebar menuItems={menuItems} menuNavigation={menuNavigation} />
                          <Layout className="main-layout-bg">
                            <AppHeader menuItems={menuItems} menuNavigation={menuNavigation} />
                            <Content className="content-area">
                              <ProtectedRoutes />
                            </Content>
                          </Layout>
                        </Layout>
                      </ProtectedRoute>
                    }
                  />
                </Routes>
              </div>
            </Router>
          );
        })()}
      </AntdApp>
    </ConfigProvider>
  );
}

export default App;
