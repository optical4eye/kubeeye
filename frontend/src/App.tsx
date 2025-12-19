import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import { Layout, Menu, Spin, ConfigProvider, theme } from 'antd';
import {
  DashboardOutlined,
  ClusterOutlined,
  SearchOutlined,
  FileTextOutlined,
  QuestionCircleOutlined,
  WifiOutlined
} from '@ant-design/icons';
import VersionDisplay from './components/VersionDisplay';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const ClusterManagement = lazy(() => import('./pages/ClusterManagement'));
const Inspection = lazy(() => import('./pages/Inspection'));
const Reports = lazy(() => import('./pages/Reports'));
const Help = lazy(() => import('./pages/Help'));
const NetworkConnectivity = lazy(() => import('./pages/NetworkConnectivity'));

const { Header, Sider, Content } = Layout;

function App() {
  const [collapsed, setCollapsed] = React.useState(false);

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: 'Dashboard',
    },
    {
      key: '/clusters',
      icon: <ClusterOutlined />,
      label: 'Управление кластерами',
    },
    {
      key: '/network',
      icon: <WifiOutlined />,
      label: 'Сетевые подключения',
    },
    {
      key: '/inspection',
      icon: <SearchOutlined />,
      label: 'Инспекция',
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
    return (
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="dark"
      >
        <div className="logo logo-container">
          <span>Kube</span><span>Eye</span>
        </div>
        <VersionDisplay version="3.1" />
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => window.location.href = key}
        />
      </Sider>
    );
  };

  return (
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: '#6366f1',
          colorBgContainer: '#282a36',
          colorBgElevated: '#282a36',
          colorText: '#f8f8f2',
          colorTextSecondary: '#8b94b8',
          colorBorder: '#6272a4',
          colorBorderSecondary: '#6272a4',
          colorBgLayout: '#21222c',
        },
      }}
    >
      <Router>
        <div className="app-container">
          <Layout className="main-layout">
            <Sidebar />
            <Layout className="main-layout-bg">
              <Header className="header-bg">
                <div className="header-title">
                  Kubernetes Cluster Inspection Tool
                </div>
              </Header>
              <Content className="content-area">
                <Suspense fallback={<div className="loading-spinner"><Spin size="large" /></div>}>
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/clusters" element={<ClusterManagement />} />
                    <Route path="/network" element={<NetworkConnectivity />} />
                    <Route path="/inspection" element={<Inspection />} />
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