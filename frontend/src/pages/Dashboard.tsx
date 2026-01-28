import React, { useEffect } from 'react';
import { Card, Table, message, Tag } from 'antd';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { getDashboardData } from '../services/api';
import { DashboardStatistics, DashboardCharts } from '../components/dashboard';

interface ClusterStatus {
  name: string;
  status: string;
  node_count: number;
  critical_count: number;
  warning_count: number;
  info_count: number;
  passed_count: number;
  last_scan?: string;
}

interface DashboardData {
  status_counts?: {
    healthy?: number;
    warning?: number;
    critical?: number;
    unknown?: number;
  };
  cluster_statuses?: ClusterStatus[];
  recent_results?: Array<{
    timestamp?: string;
    critical?: number;
    warning?: number;
    info?: number;
  }>;
  total_clusters?: number;
  recent_scans?: number;
  recent_issues?: number;
  latest_scan_time?: string;
  total_rules?: number;
}

const Dashboard = () => {
  const queryClient = useQueryClient();
  const { t } = useTranslation();

  const { data: dashboardData } = useQuery({
    queryKey: ['dashboard'],
    queryFn: getDashboardData,
    staleTime: 2 * 60 * 1000, // 2 minutes for dashboard
    onError: _error => {
      message.error(t('dashboard.errorLoading'));
    },
  });

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
  const defaultData: DashboardData = {
    status_counts: { healthy: 0, warning: 0, critical: 0, unknown: 0 },
    cluster_statuses: [],
    recent_results: [],
    total_clusters: 0,
    recent_scans: 0,
    recent_issues: 0,
    latest_scan_time: t('dashboard.noData'),
    total_rules: 0,
  };

  const data = (dashboardData?.data as DashboardData) || defaultData;
  const cluster_statuses = data.cluster_statuses || defaultData.cluster_statuses;

  const getStatusTag = (status: string): React.ReactNode => {
    const statusMap: Record<string, { className: string; text: string }> = {
      healthy: { className: 'status-ok', text: t('status.healthy') },
      ok: { className: 'status-ok', text: t('status.ok') },
      warning: { className: 'status-warning', text: t('status.warning') },
      critical: { className: 'status-critical', text: t('status.critical') },
      error: { className: 'status-exception', text: t('status.error') },
      unknown: { className: 'status-unknown', text: t('status.unknown') },
      pending: { className: 'status-pending', text: t('status.pending') },
      running: { className: 'status-running', text: t('status.running') },
    };

    const normalizedStatus = status?.toLowerCase() || 'unknown';
    const statusConfig = statusMap[normalizedStatus] || statusMap.unknown;

    return <Tag className={`ant-tag ${statusConfig.className}`}>{statusConfig.text}</Tag>;
  };

  const clusterColumns = [
    { title: t('dashboard.cluster'), dataIndex: 'name', key: 'name' },
    {
      title: t('dashboard.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => getStatusTag(status),
    },
    { title: t('dashboard.nodes'), dataIndex: 'node_count', key: 'node_count' },
    {
      title: t('dashboard.critical'),
      dataIndex: 'critical_count',
      key: 'critical_count',
      render: (count: number) =>
        count > 0 ? (
          <span className="kube-text-error">{count}</span>
        ) : (
          <span className="kube-text-neutral">{count}</span>
        ),
    },
    {
      title: t('dashboard.warning'),
      dataIndex: 'warning_count',
      key: 'warning_count',
      render: (count: number) =>
        count > 0 ? (
          <span className="kube-text-warning">{count}</span>
        ) : (
          <span className="kube-text-neutral">{count}</span>
        ),
    },
    {
      title: t('dashboard.info'),
      dataIndex: 'info_count',
      key: 'info_count',
      render: (count: number) =>
        count > 0 ? (
          <span className="kube-text-info">{count}</span>
        ) : (
          <span className="kube-text-neutral">{count}</span>
        ),
    },
    {
      title: t('dashboard.passed'),
      dataIndex: 'passed_count',
      key: 'passed_count',
      render: (count: number) =>
        count > 0 ? (
          <span className="kube-text-success">{count}</span>
        ) : (
          <span className="kube-text-neutral">{count}</span>
        ),
    },
    {
      title: t('dashboard.lastCheck'),
      dataIndex: 'last_scan',
      key: 'last_scan',
      render: (text: string) =>
        text ? new Date(text).toLocaleString('ru-RU', {
          day: '2-digit',
          month: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          hour12: false
        }).replace(', ', '-') : t('dashboard.notChecked'),
    },
  ];

  return (
    <div>
      <div className="page-title">{t('dashboard.title')}</div>
      <div className="page-subtitle">{t('dashboard.subtitle')}</div>

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
