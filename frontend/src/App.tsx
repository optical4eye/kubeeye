import React, { Suspense, lazy, useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation, useNavigate } from 'react-router-dom';
import {
  Layout,
  Menu,
  Spin,
  ConfigProvider,
  App as AntdApp,
  theme as antdTheme,
  Switch,
  Select,
} from 'antd';
import { useTranslation } from 'react-i18next';
import {
  DashboardOutlined,
  SearchOutlined,
  FileTextOutlined,
  QuestionCircleOutlined,
  SunOutlined,
  MoonOutlined,
  ApartmentOutlined,
  SettingOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import VersionDisplay from './components/ui/VersionDisplay';
import LoadingScreen from './components/ui/LoadingScreen';
import { useUIStore } from './stores/uiStore';
import { getThemeConfig } from './theme/themeConfig';
import { useSystemStatusWebSocket } from './hooks/useSystemStatusWebSocket';
import { useRBAC } from './hooks/useRBAC';
import Login from './pages/Login';
import ChangePassword from './pages/ChangePassword';
import ProtectedRoute from './components/ProtectedRoute';
import UserMenu from './components/UserMenu';

// Removed DB health check

const MIN_LOADING_TIME = 200; // Minimum 200ms loading time

const Dashboard = lazy(() => import('./pages/Dashboard'));
const ClusterManagement = lazy(() => import('./pages/ClusterManagement'));
const Inspection = lazy(() => import('./pages/Inspection'));
const Rules = lazy(() => import('./pages/Rules'));
const PopeyeScan = lazy(() => import('./pages/PopeyeScan'));
const Reports = lazy(() => import('./pages/Reports'));
const Help = lazy(() => import('./pages/Help'));
const NetworkConnectivity = lazy(() => import('./pages/NetworkConnectivity'));
const SecretManagement = lazy(() => import('./pages/SecretManagement'));
const UserManagement = lazy(() => import('./pages/UserManagement'));
const AuditLogs = lazy(() => import('./pages/AuditLogs'));
const { Header, Sider, Content } = Layout;

function App() {
  const { theme, setTheme, language, setLanguage } = useUIStore();
  const { t, i18n } = useTranslation();
  const [minLoadingTimePassed, setMinLoadingTimePassed] = useState(false);
  const { canAccessRoute } = useRBAC();

  // Configure global theme for message, notification, and other global components
  useEffect(() => {
    const themeConfig = getThemeConfig(theme === 'dark');
    ConfigProvider.config({
      theme: {
        token: themeConfig.token,
        components: themeConfig.components,
        algorithm: theme === 'dark' ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
      },
    });
  }, [theme]);

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

  // Define all menu items
  const allMenuItems = [
    {
      key: 'overview',
      icon: <DashboardOutlined />,
      label: t('menu.groups.overview'),
      children: [
        {
          key: '/',
          label: t('menu.dashboard'),
        },
      ],
    },
    {
      key: 'infrastructure',
      icon: <ApartmentOutlined />,
      label: t('menu.groups.infrastructure'),
      children: [
        {
          key: '/clusters',
          label: t('menu.clusters'),
        },
        {
          key: '/network',
          label: t('menu.network'),
        },
      ],
    },
    {
      key: 'inspections',
      icon: <SearchOutlined />,
      label: t('menu.groups.inspections'),
      children: [
        {
          key: '/inspection',
          label: t('menu.inspection'),
        },
        {
          key: '/popeye',
          label: t('menu.popeye'),
        },
      ],
    },
    {
      key: 'reports',
      icon: <FileTextOutlined />,
      label: t('menu.groups.reports'),
      children: [
        {
          key: '/reports',
          label: t('menu.reports'),
        },
      ],
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: t('menu.groups.settings'),
      children: [
        {
          key: '/rules',
          label: t('menu.rules'),
        },
        {
          key: '/secrets',
          label: t('menu.secrets'),
        },
      ],
    },
    {
      key: 'management',
      icon: <TeamOutlined />,
      label: t('menu.groups.management'),
      children: [
        {
          key: '/users',
          label: t('menu.users'),
        },
        {
          key: '/audit-logs',
          label: t('menu.auditLogs'),
        },
      ],
    },
    {
      key: 'help',
      icon: <QuestionCircleOutlined />,
      label: t('menu.groups.help'),
      children: [
        {
          key: '/help',
          label: t('menu.help'),
        },
      ],
    },
  ];

  // Filter menu items based on user's role
  const menuItems = allMenuItems
    .map(group => ({
      ...group,
      children: group.children?.filter(child => canAccessRoute(child.key)) ?? [],
    }))
    .filter(group => (group.children?.length ?? 0) > 0);

  const Sidebar = () => {
    const location = useLocation();
    const navigate = useNavigate();

    // Find the parent group key for the current path
    const getOpenKeys = () => {
      for (const item of menuItems) {
        if (item.children) {
          const child = item.children.find((child: any) => child.key === location.pathname);
          if (child) {
            return [item.key];
          }
        }
      }
      return [];
    };

    const openKeys = getOpenKeys();

    return (
      <Sider>
        <div className="logo logo-container">
          <span>KubeEye</span>
        </div>
        <VersionDisplay version="3.3" />
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          defaultOpenKeys={openKeys}
          items={menuItems}
          onClick={({ key }) => {
            // Only navigate if it's a leaf node (not a group)
            const isLeaf = menuItems.some((item: any) =>
              item.children?.some((child: any) => child.key === key)
            );
            if (isLeaf) {
              navigate(key);
            }
          }}
        />
      </Sider>
    );
  };

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
                  <Route path="/login" element={<Login />} />

                  {/* Protected routes - with layout */}
                  <Route
                    path="/*"
                    element={
                      <ProtectedRoute>
                        <Layout className="main-layout">
                          <Sidebar />
                          <Layout className="main-layout-bg">
                            <Header className="header-bg">
                              <div className="header-content">
                                <div className="header-title">{t('header.title')}</div>
                                <div
                                  style={{
                                    marginLeft: 'auto',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '16px',
                                  }}
                                >
                                  <UserMenu />
                                  <Switch
                                    checked={theme === 'dark'}
                                    onChange={checked => setTheme(checked ? 'dark' : 'light')}
                                    checkedChildren={<SunOutlined />}
                                    unCheckedChildren={<MoonOutlined />}
                                  />
                                  <Select
                                    value={language}
                                    onChange={value => setLanguage(value)}
                                    options={[
                                      { value: 'ru', label: 'RU' },
                                      { value: 'en', label: 'EN' },
                                    ]}
                                    style={{ width: 60 }}
                                    size="small"
                                  />
                                </div>
                              </div>
                            </Header>
                            <Content className="content-area">
                              <Suspense
                                fallback={
                                  <div className="loading-spinner">
                                    <Spin size="large" />
                                  </div>
                                }
                              >
                                <Routes>
                                  <Route path="/" element={<Dashboard />} />
                                  <Route path="/clusters" element={<ClusterManagement />} />
                                  <Route
                                    path="/secrets"
                                    element={
                                      <ProtectedRoute>
                                        <SecretManagement />
                                      </ProtectedRoute>
                                    }
                                  />
                                  <Route path="/network" element={<NetworkConnectivity />} />
                                  <Route path="/inspection" element={<Inspection />} />
                                  <Route
                                    path="/rules"
                                    element={
                                      <ProtectedRoute>
                                        <Rules />
                                      </ProtectedRoute>
                                    }
                                  />
                                  <Route path="/popeye" element={<PopeyeScan />} />
                                  <Route path="/reports" element={<Reports />} />
                                  <Route path="/help" element={<Help />} />
                                  <Route path="/change-password" element={<ChangePassword />} />
                                  <Route
                                    path="/users"
                                    element={
                                      <ProtectedRoute>
                                        <UserManagement />
                                      </ProtectedRoute>
                                    }
                                  />
                                  <Route
                                    path="/audit-logs"
                                    element={
                                      <ProtectedRoute>
                                        <AuditLogs />
                                      </ProtectedRoute>
                                    }
                                  />
                                </Routes>
                              </Suspense>
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
