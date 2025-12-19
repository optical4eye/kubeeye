import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Button, Table, Progress, message } from 'antd';
import { ReloadOutlined, ClusterOutlined, CheckCircleOutlined, WarningOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { getDashboardData } from '../services/api';
import { fetchData } from '../utils/apiErrorHandler';

const chartColors = {
  success: 'var(--success-color)',
  warning: 'var(--warning-color)',
  error: 'var(--error-color)',
  info: 'var(--secondary-color)'
};

const COLORS = [chartColors.success, chartColors.warning, chartColors.error, chartColors.info];

const Dashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Утилитарные функции для преобразования статусов
  const getStatusName = React.useCallback((key) => {
    const statusMap = {
      healthy: 'Успешно',
      warning: 'Предупреждения',
      critical: 'Критические ошибки'
    };
    return statusMap[key] || 'Неизвестно';
  }, []);

  // Подготовка данных для круговой диаграммы с мемоизацией
  const pieData = React.useMemo(() => {
    if (!dashboardData) return [];
    return Object.entries(dashboardData.status_counts).map(([key, value]) => ({
      name: getStatusName(key),
      value,
      color: COLORS[Object.keys(dashboardData.status_counts).indexOf(key)]
    }));
  }, [dashboardData, getStatusName]);

  // Подготовка данных для линейного графика трендов с мемоизацией
  const trendData = React.useMemo(() => {
    if (!dashboardData) return [];
    return dashboardData.recent_results.slice(0, 7).map(result => ({
      date: new Date(result.timestamp).toLocaleDateString(),
      critical: result.critical || 0,
      warning: result.warning || 0,
      info: result.info || 0,
      passed: dashboardData.total_rules - (result.critical || 0) - (result.warning || 0) - (result.info || 0)
    }));
  }, [dashboardData]);

  // Расчет общего количества passed проверок с мемоизацией
  const totalPassed = React.useMemo(() => {
    if (!dashboardData) return 0;
    return dashboardData.recent_results.reduce((sum, r) => sum + (dashboardData.total_rules - (r.critical || 0) - (r.warning || 0) - (r.info || 0)), 0);
  }, [dashboardData]);

  // Подготовка данных для столбчатой диаграммы с мемоизацией
  const barData = React.useMemo(() => {
    if (!dashboardData) return [];
    return [
      { name: 'Критические ошибки', value: dashboardData.cluster_statuses.reduce((sum, cs) => sum + (cs.critical_count || 0), 0), color: chartColors.error },
      { name: 'Предупреждения', value: dashboardData.cluster_statuses.reduce((sum, cs) => sum + (cs.warning_count || 0), 0), color: chartColors.warning },
      { name: 'Успешно', value: dashboardData.cluster_statuses.reduce((sum, cs) => sum + (cs.passed_count || 0), 0), color: chartColors.success }
    ];
  }, [dashboardData]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      await fetchData(
        getDashboardData,
        'Ошибка загрузки данных dashboard',
        (data) => setDashboardData(data)
      );
    } catch (error) {
      console.error(error);
      // Set default data to prevent white screen
      setDashboardData({
        status_counts: { healthy: 0, warning: 0, critical: 0, unknown: 0 },
        cluster_statuses: [],
        recent_results: [],
        total_clusters: 0,
        recent_scans: 0,
        recent_issues: 0,
        latest_scan_time: 'Нет данных',
        total_rules: 0
      });
      message.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();

    // Listen for new report events
    const handleNewReport = () => {
      loadDashboardData();
    };

    window.addEventListener('newReportAvailable', handleNewReport);

    return () => {
      window.removeEventListener('newReportAvailable', handleNewReport);
    };
  }, []);

  if (loading || !dashboardData) {
    return <div>Загрузка...</div>;
  }

  const { status_counts, cluster_statuses, recent_results, total_clusters, recent_scans, recent_issues, latest_scan_time, total_rules } = dashboardData;

  const clusterColumns = [
    { title: 'Кластер', dataIndex: 'name', key: 'name' },
    { title: 'Статус', dataIndex: 'status', key: 'status' },
    { title: 'Узлы', dataIndex: 'node_count', key: 'node_count' },
    { title: 'Критические', dataIndex: 'critical_count', key: 'critical_count' },
    { title: 'Предупреждения', dataIndex: 'warning_count', key: 'warning_count' },
    { title: 'Последняя проверка', dataIndex: 'last_scan', key: 'last_scan', render: (text) => text ? new Date(text).toLocaleString() : 'Не проверялся' }
  ];

  return (
    <div>
      <div className="page-title">Обзор кластеров</div>
      <div className="page-subtitle">Мониторинг и инспекция Kubernetes кластеров</div>

      <Row gutter={16} className="dashboard-row">
        <Col span={24}>
          <Button icon={<ReloadOutlined />} onClick={loadDashboardData} loading={loading}>
            Обновить данные
          </Button>
        </Col>
      </Row>

      <Row gutter={16} className="dashboard-row">
        <Col span={3}><Statistic title="Кластеры" value={total_clusters} /></Col>
        <Col span={3}><Statistic title="Инспекций" value={recent_scans} /></Col>
        <Col span={3}><Statistic title="Критические" value={recent_results.reduce((sum, r) => sum + (r.critical || 0), 0)} /></Col>
        <Col span={3}><Statistic title="Предупреждения" value={recent_results.reduce((sum, r) => sum + (r.warning || 0), 0)} /></Col>
        <Col span={3}><Statistic title="Другие" value={recent_results.reduce((sum, r) => sum + (r.info || 0), 0)} /></Col>
        <Col span={3}><Statistic title="Успешно" value={recent_results.reduce((sum, r) => sum + (r.passed || 0), 0)} /></Col>
        <Col span={3}><Statistic title="Последняя" value={latest_scan_time} /></Col>
        <Col span={3}><Statistic title="Правил" value={total_rules} /></Col>
      </Row>



      <Row gutter={16} className="dashboard-row">
        <Col span={24}>
          <Card title="Тренды ошибок (7 дней)">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="critical" stroke="var(--error-color)" name="Критические" />
                <Line type="monotone" dataKey="warning" stroke="var(--warning-color)" name="Предупреждения" />
                <Line type="monotone" dataKey="info" stroke="var(--text-secondary)" name="Другие" />
                <Line type="monotone" dataKey="passed" stroke="var(--success-color)" name="Успешно" />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      <Card title="Детали кластеров">
        <Table
          columns={clusterColumns}
          dataSource={cluster_statuses}
          rowKey="name"
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </div>
  );
};

export default Dashboard;