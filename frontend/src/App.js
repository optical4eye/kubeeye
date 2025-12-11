import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import { Layout, Menu, Spin } from 'antd';
import {
  DashboardOutlined,
  ClusterOutlined,
  SearchOutlined,
  FileTextOutlined,
  QuestionCircleOutlined,
  WifiOutlined
} from '@ant-design/icons';
import './App.css';

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
        <div className="logo" style={{ padding: '16px', fontSize: '18px', fontWeight: 'bold' }}>
          <span style={{ color: '#f8f8f2 !important' }}>Kube</span><span style={{ color: '#7359f8 !important' }}>Eye</span>
        </div>
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
    <Router>
      <div className="app-container">
        <Layout className="main-layout">
          <Sidebar />
          <Layout style={{ background: '#282a36' }}>
            <Header style={{ padding: 0, background: '#7359f8' }}>
              <div style={{ padding: '0 24px', fontSize: '18px', fontWeight: 'bold', color: '#f8f8f2' }}>
                Kubernetes Cluster Inspection Tool
              </div>
            </Header>
            <Content className="content-area">
              <Suspense fallback={<div style={{ textAlign: 'center', padding: '50px' }}><Spin size="large" /></div>}>
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
  );
}

export default App;