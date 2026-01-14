import React, { Suspense, lazy, useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation, useNavigate } from 'react-router-dom';
import { Layout, Menu, Spin, ConfigProvider, theme as antdTheme } from 'antd';
import {
  DashboardOutlined,
  ClusterOutlined,
  SearchOutlined,
  FileTextOutlined,
  QuestionCircleOutlined,
  WifiOutlined,
  ScanOutlined,
  LockOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import VersionDisplay from './components/VersionDisplay';
import LoadingScreen from './components/LoadingScreen';
import { useUIStore } from './stores/uiStore';
import { getHealthStatus } from './services/api';

// Removed DB health check

const MIN_LOADING_TIME = 200; // Minimum 200ms loading time

const Dashboard = lazy(() => import('./pages/Dashboard'));
const ClusterManagement = lazy(() => import('./pages/ClusterManagement'));
const Inspection = lazy(() => import('./pages/Inspection'));
const PopeyeScan = lazy(() => import('./pages/PopeyeScan'));
const Reports = lazy(() => import('./pages/Reports'));
const Help = lazy(() => import('./pages/Help'));
const NetworkConnectivity = lazy(() => import('./pages/NetworkConnectivity'));
const SecretManagement = lazy(() => import('./pages/SecretManagement'));

const { Header, Sider, Content } = Layout;

function App() {
  const { theme } = useUIStore();
  const [minLoadingTimePassed, setMinLoadingTimePassed] = useState(false);

  // Check backend health continuously
  const { data: healthStatus, error: healthError } = useQuery({
    queryKey: ['backend-health'],
    queryFn: getHealthStatus,
    refetchInterval: 5000, // Check every 5 seconds continuously
    retry: false, // Disable retry to immediately set error state
    staleTime: 2000,
  });

  // Show loading screen if backend is not ready
  const isBackendReady =
    !healthError &&
    (healthStatus?.data?.status === 'healthy' || healthStatus?.data?.status === 'ok');
  const isSystemReady = isBackendReady;

  // Ensure minimum loading time for initial load
  useEffect(() => {
    const timer = setTimeout(() => {
      setMinLoadingTimePassed(true);
    }, MIN_LOADING_TIME);

    return () => clearTimeout(timer);
  }, []);

  // Show loading screen during initial minimum time
  if (!minLoadingTimePassed) {
    return <LoadingScreen message="Подключение к системе..." subMessage="Пожалуйста, подождите" />;
  }

  // Show loading screen if backend is not ready
  if (!isSystemReady) {
    return (
      <LoadingScreen
        message="Проблема с подключением к системе"
        subMessage="Пытаемся восстановить соединение..."
      />
    );
  }

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: 'Dashboard',
    },
    {
      key: '/clusters',
      icon: <ClusterOutlined />,
      label: 'Кластеры',
    },
    {
      key: '/secrets',
      icon: <LockOutlined />,
      label: 'Секреты',
    },
    {
      key: '/network',
      icon: <WifiOutlined />,
      label: 'Сеть',
    },
    {
      key: '/inspection',
      icon: <SearchOutlined />,
      label: 'Инспекция',
    },
    {
      key: '/popeye',
      icon: <ScanOutlined />,
      label: 'Popeye',
    },
    {
      key: '/reports',
      icon: <FileTextOutlined />,
      label: 'Отчеты',
    },
    {
      key: '/help',
      icon: <QuestionCircleOutlined />,
      label: 'Помощь',
    },
  ];

  const Sidebar = () => {
    const location = useLocation();
    const navigate = useNavigate();
    return (
      <Sider theme="dark">
        <div className="logo logo-container">
          <span>Kube</span>
          <span>Eye</span>
        </div>
        <VersionDisplay version="3.2" />
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
    );
  };

  return (
    <ConfigProvider
      theme={{
        algorithm: theme === 'dark' ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
        token: {
          colorPrimary: '#fab005',
          colorBgContainer: theme === 'dark' ? '#495057' : '#ffffff',
          colorBgElevated: theme === 'dark' ? '#495057' : '#ffffff',
          colorText: theme === 'dark' ? '#f8f8f2' : '#000000',
          colorTextSecondary: theme === 'dark' ? '#adb5bd' : '#666666',
          colorBorder: theme === 'dark' ? '#6c757d' : '#d9d9d9',
          colorBorderSecondary: theme === 'dark' ? '#6c757d' : '#d9d9d9',
          colorBgLayout: theme === 'dark' ? '#343a40' : '#f5f5f5',
        },
      }}
    >
      <Router>
        <div className="app-container">
          <Layout className="main-layout">
            <Sidebar />
            <Layout className="main-layout-bg">
              <Header className="header-bg">
                <div className="header-content">
                  <div className="header-title">Kubernetes Cluster Inspection Tool</div>
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
                    <Route path="/secrets" element={<SecretManagement />} />
                    <Route path="/network" element={<NetworkConnectivity />} />
                    <Route path="/inspection" element={<Inspection />} />
                    <Route path="/popeye" element={<PopeyeScan />} />
                    <Route path="/reports" element={<Reports />} />
                    <Route path="/help" element={<Help />} />
                  </Routes>
                </Suspense>
              </Content>
            </Layout>
          </Layout>
        </div>
      </Router>
    </ConfigProvider>
  );
}

export default App;
