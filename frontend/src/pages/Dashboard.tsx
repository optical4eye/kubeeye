import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Button, Table, message } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { getDashboardData } from '../services/api';
import { fetchData } from '../utils/apiErrorHandler';
import DashboardStatistics from '../components/DashboardStatistics';
import DashboardCharts from '../components/DashboardCharts';


const Dashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);


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

      <DashboardStatistics dashboardData={dashboardData} />

      <DashboardCharts dashboardData={dashboardData} />

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