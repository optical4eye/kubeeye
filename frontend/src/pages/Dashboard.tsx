import React, { useEffect } from 'react';
import { Card, Table, App, Skeleton } from 'antd';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { getDashboardData } from '../services/api';
import { DashboardStatistics, DashboardCharts } from '../components/dashboard';
import { getStatusTag } from '../components/ui/statusUtils';

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
  const { message: messageApi } = App.useApp();

  const { data: dashboardData, isLoading: loading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: getDashboardData,
    staleTime: 2 * 60 * 1000, // 2 minutes for dashboard
    onError: _error => {
      messageApi.error(t('dashboard.errorLoading'));
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

  const getStatusText = (status: string): string => {
    const statusMap: Record<string, string> = {
      healthy: t('status.healthy'),
      ok: t('status.ok'),
      warning: t('status.warning'),
      critical: t('status.critical'),
      error: t('status.error'),
      unknown: t('status.unknown'),
      pending: t('status.pending'),
      running: t('status.running'),
    };

    const normalizedStatus = status?.toLowerCase() || 'unknown';
    return statusMap[normalizedStatus] || statusMap.unknown;
  };

  const clusterColumns = [
    { title: t('dashboard.cluster'), dataIndex: 'name', key: 'name' },
    {
      title: t('dashboard.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => getStatusTag(status, getStatusText(status)),
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
        text
          ? new Date(text)
              .toLocaleString('ru-RU', {
                day: '2-digit',
                month: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                hour12: false,
              })
              .replace(', ', '-')
          : t('dashboard.notChecked'),
    },
  ];

  return (
    <div>
      <div className="page-title">{t('dashboard.title')}</div>
      <div className="page-subtitle">{t('dashboard.subtitle')}</div>

      <DashboardStatistics dashboardData={data} />

      <DashboardCharts dashboardData={data} />

      <Card title={t('dashboard.clusterDetails')}>
        {loading ? (
          <Skeleton active paragraph={{ rows: 8 }} />
        ) : (
          <Table
            columns={clusterColumns}
            dataSource={cluster_statuses}
            rowKey="name"
            pagination={{ pageSize: 10 }}
            scroll={{ y: 400 }}
            virtual={true}
            aria-label={t('dashboard.clusterTableAria')}
          />
        )}
      </Card>
    </div>
  );
};

export default Dashboard;
