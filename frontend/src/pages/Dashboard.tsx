import React, { useEffect } from 'react';
import { Card, Row, Col, Button, Table, message } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { getDashboardData } from '../services/api';
import { DashboardStatistics, DashboardCharts } from '../components/dashboard';

const Dashboard = () => {
  const queryClient = useQueryClient();
  const { t } = useTranslation();

  const {
    data: dashboardData,
    isLoading: loading,
    refetch,
  } = useQuery({
    queryKey: ['dashboard'],
    queryFn: getDashboardData,
    staleTime: 2 * 60 * 1000, // 2 minutes for dashboard
    onError: _error => {
      message.error(t('dashboard.errorLoading'));
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
    latest_scan_time: t('dashboard.noData'),
    total_rules: 0,
  };

  const data = dashboardData?.data || defaultData;
  const cluster_statuses = data.cluster_statuses || defaultData.cluster_statuses;

  const clusterColumns = [
    { title: t('dashboard.cluster'), dataIndex: 'name', key: 'name' },
    { title: t('dashboard.status'), dataIndex: 'status', key: 'status' },
    { title: t('dashboard.nodes'), dataIndex: 'node_count', key: 'node_count' },
    { title: t('dashboard.critical'), dataIndex: 'critical_count', key: 'critical_count' },
    { title: t('dashboard.warning'), dataIndex: 'warning_count', key: 'warning_count' },
    {
      title: t('dashboard.lastCheck'),
      dataIndex: 'last_scan',
      key: 'last_scan',
      render: text => (text ? new Date(text).toLocaleString() : t('dashboard.notChecked')),
    },
  ];

  return (
    <div>
      <div className="page-title">{t('dashboard.title')}</div>
      <div className="page-subtitle">{t('dashboard.subtitle')}</div>

      <Row gutter={16} className="dashboard-row">
        <Col span={24}>
          <Button
            icon={<ReloadOutlined />}
            onClick={loadDashboardData}
            loading={loading}
            aria-label={t('dashboard.refreshAria')}
          >
            {t('dashboard.refreshButton')}
          </Button>
        </Col>
      </Row>

      <DashboardStatistics dashboardData={data} />

      <DashboardCharts dashboardData={data} />

      <Card title={t('dashboard.clusterDetails')}>
        <Table
          columns={clusterColumns}
          dataSource={cluster_statuses}
          rowKey="name"
          pagination={{ pageSize: 10 }}
          scroll={{ y: 400 }}
          virtual={true}
          aria-label={t('dashboard.clusterTableAria')}
        />
      </Card>
    </div>
  );
};

export default Dashboard;
