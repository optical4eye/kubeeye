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
  Breadcrumb,
  Button,
  Drawer,
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
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  HomeOutlined,
  MenuOutlined,
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
const AddCluster = lazy(() => import('./pages/AddCluster'));
const Inspection = lazy(() => import('./pages/Inspection'));
const ScheduledInspection = lazy(() => import('./pages/ScheduledInspection'));
const Rules = lazy(() => import('./pages/Rules'));
const PopeyeScan = lazy(() => import('./pages/PopeyeScan'));
const Reports = lazy(() => import('./pages/Reports'));
const Help = lazy(() => import('./pages/Help'));
const HelpIntroduction = lazy(() => import('./pages/HelpIntroduction'));
const HelpExamples = lazy(() => import('./pages/HelpExamples'));
const HelpSecurity = lazy(() => import('./pages/HelpSecurity'));
const HelpKubeconfig = lazy(() => import('./pages/HelpKubeconfig'));
const HelpApi = lazy(() => import('./pages/HelpApi'));
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

  // Collapsible sidebar state with localStorage persistence
  const [collapsed, setCollapsed] = useState(() => {
    const saved = localStorage.getItem('sidebarCollapsed');
    return saved ? JSON.parse(saved) : false;
  });

  // Menu open keys state with localStorage persistence
  const [openKeys, setOpenKeys] = useState<string[]>(() => {
    const saved = localStorage.getItem('menuOpenKeys');
    return saved ? JSON.parse(saved) : [];
  });

  // Mobile drawer state
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);

  // Save collapsed state to localStorage
  useEffect(() => {
    localStorage.setItem('sidebarCollapsed', JSON.stringify(collapsed));
  }, [collapsed]);

  // Save open keys to localStorage
  useEffect(() => {
    localStorage.setItem('menuOpenKeys', JSON.stringify(openKeys));
  }, [openKeys]);

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
          key: '/add-cluster',
          label: t('menu.addCluster'),
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
          key: '/scheduled-inspection',
          label: t('menu.scheduledInspection'),
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
          key: '/help/introduction',
          label: t('menu.helpIntroduction'),
        },
        {
          key: '/help/examples',
          label: t('menu.helpExamples'),
        },
        {
          key: '/help/security',
          label: t('menu.helpSecurity'),
        },
        {
          key: '/help/kubeconfig',
          label: t('menu.helpKubeconfig'),
        },
        {
          key: '/help/api',
          label: t('menu.helpApi'),
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

    // Auto-open menu group on route change
    useEffect(() => {
      const keys = getOpenKeys();
      if (keys.length > 0 && !openKeys.includes(keys[0])) {
        setOpenKeys(keys);
      }
    }, [location.pathname]);

    return (
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        trigger={null}
        width={200}
        collapsedWidth={64}
        className="sidebar-sider"
      >
        <div className="logo logo-container">
          {collapsed ? <span>KE</span> : <span>KubeEye</span>}
        </div>
        {!collapsed && <VersionDisplay version="3.3" />}
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          openKeys={openKeys}
          onOpenChange={setOpenKeys}
          items={menuItems}
          onClick={({ key }) => {
            // Only navigate if it's a leaf node (not a group)
            const isLeaf = menuItems.some((item: any) =>
              item.children?.some((child: any) => child.key === key)
            );
            if (isLeaf) {
              navigate(key);
              // Close mobile drawer after navigation
              setMobileDrawerOpen(false);
            }
          }}
        />
      </Sider>
    );
  };

  // Mobile Navigation Drawer Component
  const MobileDrawer = () => {
    const location = useLocation();
    const navigate = useNavigate();

    return (
      <Drawer
        title={<span className="kube-font-semibold">KubeEye</span>}
        placement="left"
        onClose={() => setMobileDrawerOpen(false)}
        open={mobileDrawerOpen}
        width={250}
        styles={{ body: { padding: 0 } }}
      >
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          openKeys={openKeys}
          onOpenChange={setOpenKeys}
          items={menuItems}
          onClick={({ key }) => {
            const isLeaf = menuItems.some((item: any) =>
              item.children?.some((child: any) => child.key === key)
            );
            if (isLeaf) {
              navigate(key);
              setMobileDrawerOpen(false);
            }
          }}
        />
      </Drawer>
    );
  };

  // Header Component with Breadcrumbs
  const AppHeader = () => {
    const location = useLocation();

    // Generate breadcrumb items based on current path
    const getBreadcrumbItems = () => {
      const items: any[] = [{ title: <HomeOutlined />, href: '/' }];

      for (const group of menuItems) {
        if (group.children) {
          const child = group.children.find((c: any) => c.key === location.pathname);
          if (child) {
            items.push({ title: group.label });
            items.push({ title: child.label });
            break;
          }
        }
      }

      return items;
    };

    return (
      <Header className="header-bg">
        <div className="header-content">
          <div className="kube-display-flex kube-align-center kube-gap-8">
            {/* Mobile menu button */}
            <Button
              type="text"
              icon={<MenuOutlined />}
              onClick={() => setMobileDrawerOpen(true)}
              className="mobile-menu-button"
            />
            {/* Collapse/Expand button */}
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              className="desktop-collapse-button"
            />
          </div>

          {/* Breadcrumbs */}
          <div className="kube-margin-left-8 kube-margin-right-8">
            <Breadcrumb items={getBreadcrumbItems()} />
          </div>

          <div className="header-title">{t('header.title')}</div>

          <div className="kube-margin-left-auto kube-display-flex kube-align-center kube-gap-16">
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
              className="kube-width-60px"
              size="small"
            />
          </div>
        </div>
      </Header>
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
                            <AppHeader />
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
                                  <Route path="/add-cluster" element={<AddCluster />} />
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
                                    path="/scheduled-inspection"
                                    element={<ScheduledInspection />}
                                  />
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
                                  <Route path="/help/introduction" element={<HelpIntroduction />} />
                                  <Route path="/help/examples" element={<HelpExamples />} />
                                  <Route path="/help/security" element={<HelpSecurity />} />
                                  <Route path="/help/kubeconfig" element={<HelpKubeconfig />} />
                                  <Route path="/help/api" element={<HelpApi />} />
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

                {/* Mobile Navigation Drawer */}
                <MobileDrawer />
              </div>
            </Router>
          );
        })()}
      </AntdApp>
    </ConfigProvider>
  );
}

export default App;
