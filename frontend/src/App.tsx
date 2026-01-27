import React, { Suspense, lazy, useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation, useNavigate } from 'react-router-dom';
import {
  Layout,
  Menu,
  Spin,
  ConfigProvider,
  theme as antdTheme,
  Switch,
  message as antdMessage,
  Select,
} from 'antd';
import { useTranslation } from 'react-i18next';
import {
  DashboardOutlined,
  ClusterOutlined,
  SearchOutlined,
  FileTextOutlined,
  QuestionCircleOutlined,
  WifiOutlined,
  ScanOutlined,
  LockOutlined,
  SunOutlined,
  MoonOutlined,
  AntDesignOutlined,
} from '@ant-design/icons';
import VersionDisplay from './components/ui/VersionDisplay';
import LoadingScreen from './components/ui/LoadingScreen';
import { useUIStore } from './stores/uiStore';
import { getThemeConfig } from './theme/themeConfig';
import { useSystemStatusWebSocket } from './hooks/useSystemStatusWebSocket';

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
const { Header, Sider, Content } = Layout;

function App() {
  const { theme, setTheme, language, setLanguage } = useUIStore();
  const { t, i18n } = useTranslation();
  const [minLoadingTimePassed, setMinLoadingTimePassed] = useState(false);

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

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: t('menu.dashboard'),
    },
    {
      key: '/clusters',
      icon: <ClusterOutlined />,
      label: t('menu.clusters'),
    },
    {
      key: '/secrets',
      icon: <LockOutlined />,
      label: t('menu.secrets'),
    },
    {
      key: '/network',
      icon: <WifiOutlined />,
      label: t('menu.network'),
    },
    {
      key: '/popeye',
      icon: <ScanOutlined />,
      label: t('menu.popeye'),
    },
    {
      key: '/inspection',
      icon: <SearchOutlined />,
      label: t('menu.inspection'),
    },
    {
      key: '/reports',
      icon: <FileTextOutlined />,
      label: t('menu.reports'),
    },
    {
      key: '/rules',
      icon: <AntDesignOutlined />,
      label: t('menu.rules'),
    },
    {
      key: '/help',
      icon: <QuestionCircleOutlined />,
      label: t('menu.help'),
    },
  ];

  const Sidebar = () => {
    const location = useLocation();
    const navigate = useNavigate();
    return (
      <Sider>
        <div className="logo logo-container">
          <span>KubeEye</span>
        </div>
        <VersionDisplay version="3.3" />
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
    );
  };

  const [, contextHolder] = antdMessage.useMessage();

  return (
    <ConfigProvider
      theme={{
        ...getThemeConfig(theme === 'dark'),
        algorithm: theme === 'dark' ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
      }}
    >
      {contextHolder}
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
                        <Route path="/secrets" element={<SecretManagement />} />
                        <Route path="/network" element={<NetworkConnectivity />} />
                        <Route path="/inspection" element={<Inspection />} />
                        <Route path="/rules" element={<Rules />} />
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
        );
      })()}
    </ConfigProvider>
  );
}

export default App;
