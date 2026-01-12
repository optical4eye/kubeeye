import React, { useEffect } from 'react';
import { Card, Row, Col, Button, Table, message } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getDashboardData } from '../services/api';
import DashboardStatistics from '../components/DashboardStatistics';
import DashboardCharts from '../components/DashboardCharts';

const Dashboard = () => {
  const queryClient = useQueryClient();

  const {
    data: dashboardData,
    isLoading: loading,
    refetch,
  } = useQuery({
    queryKey: ['dashboard'],
    queryFn: getDashboardData,
    staleTime: 2 * 60 * 1000, // 2 minutes for dashboard
    onError: error => {
      console.error('Dashboard error:', error);
      message.error('Ошибка загрузки данных dashboard');
    },
  });

  const loadDashboardData = () => {
    refetch();
  };

  useEffect(() => {
    // Listen for new report events
    const handleNewReport = () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    };

    window.addEventListener('newReportAvailable', handleNewReport);

    return () => {
      window.removeEventListener('newReportAvailable', handleNewReport);
    };
  }, [queryClient]);

  // Provide default data if loading or error
  const defaultData = {
    status_counts: { healthy: 0, warning: 0, critical: 0, unknown: 0 },
    cluster_statuses: [],
    recent_results: [],
    total_clusters: 0,
    recent_scans: 0,
    recent_issues: 0,
    latest_scan_time: 'Нет данных',
    total_rules: 0,
  };

  const data = dashboardData?.data || defaultData;
  const cluster_statuses = data.cluster_statuses || defaultData.cluster_statuses;

  const clusterColumns = [
    { title: 'Кластер', dataIndex: 'name', key: 'name' },
    { title: 'Статус', dataIndex: 'status', key: 'status' },
    { title: 'Узлы', dataIndex: 'node_count', key: 'node_count' },
    { title: 'Критические', dataIndex: 'critical_count', key: 'critical_count' },
    { title: 'Предупреждения', dataIndex: 'warning_count', key: 'warning_count' },
    {
      title: 'Последняя проверка',
      dataIndex: 'last_scan',
      key: 'last_scan',
      render: text => (text ? new Date(text).toLocaleString() : 'Не проверялся'),
    },
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

      <DashboardStatistics dashboardData={data} />

      <DashboardCharts dashboardData={data} />

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
