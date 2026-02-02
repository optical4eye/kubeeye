import React from 'react';
import { Row, Col, Statistic, theme, Card } from 'antd';
import {
  ClusterOutlined,
  FileSearchOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useUIStore } from '../../stores/uiStore';

interface DashboardData {
  recent_results?: Array<{
    timestamp?: string;
    critical?: number;
    warning?: number;
    info?: number;
    passed?: number;
  }>;
  total_clusters?: number;
  recent_scans?: number;
  recent_issues?: number;
  latest_scan_time?: string;
  total_rules?: number;
}

interface DashboardStatisticsProps {
  dashboardData: DashboardData | null;
}

const formatScanTime = (scanTime: string | undefined, noDataText: string): string => {
  if (!scanTime || scanTime === noDataText) return noDataText;
  try {
    return new Date(scanTime)
      .toLocaleString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      })
      .replace(', ', '-');
  } catch {
    return scanTime;
  }
};

const DashboardStatistics: React.FC<DashboardStatisticsProps> = ({ dashboardData }) => {
  const { t } = useTranslation();
  const { token } = theme.useToken();
  const { theme: uiTheme } = useUIStore();

  const {
    recent_results = [],
    total_clusters = 0,
    recent_scans = 0,
    latest_scan_time: rawScanTime = t('dashboard.noData'),
    total_rules = 0,
  } = dashboardData || {};

  const latest_scan_time = formatScanTime(rawScanTime, t('dashboard.noData'));

  const criticalCount = recent_results.reduce((sum, r) => sum + (r.critical || 0), 0);
  const warningCount = recent_results.reduce((sum, r) => sum + (r.warning || 0), 0);
  const infoCount = recent_results.reduce((sum, r) => sum + (r.info || 0), 0);
  const passedCount = recent_results.reduce((sum, r) => sum + (r.passed || 0), 0);

  const statisticsConfig = [
    {
      title: t('statistics.clusters'),
      value: total_clusters,
      icon: <ClusterOutlined />,
      color: token.colorPrimary,
    },
    {
      title: t('statistics.inspections'),
      value: recent_scans,
      icon: <FileSearchOutlined />,
      color: token.colorInfo,
    },
    {
      title: t('statistics.critical'),
      value: criticalCount,
      icon: <CloseCircleOutlined />,
      color: token.colorError,
      highlight: criticalCount > 0,
    },
    {
      title: t('statistics.warning'),
      value: warningCount,
      icon: <ExclamationCircleOutlined />,
      color: token.colorWarning,
      highlight: warningCount > 0,
    },
    {
      title: t('statistics.info'),
      value: infoCount,
      icon: <InfoCircleOutlined />,
      color: token.colorInfo,
    },
    {
      title: t('statistics.passed'),
      value: passedCount,
      icon: <CheckCircleOutlined />,
      color: token.colorSuccess,
    },
    {
      title: t('statistics.last'),
      value: latest_scan_time,
      icon: <ClockCircleOutlined />,
      color: token.colorTextSecondary,
    },
    {
      title: t('statistics.rules'),
      value: total_rules,
      icon: <SafetyCertificateOutlined />,
      color: token.colorPrimary,
    },
  ];

  return (
    <Row gutter={[16, 16]} className="dashboard-row">
      {statisticsConfig.map((stat, index) => (
        <Col xs={24} sm={12} md={8} lg={6} xl={3} key={index}>
          <Card
            style={{
              backgroundColor: stat.highlight
                ? uiTheme === 'dark'
                  ? 'rgba(255, 77, 79, 0.1)'
                  : 'rgba(255, 77, 79, 0.05)'
                : 'transparent',
              border: stat.highlight ? `1px solid ${token.colorError}` : undefined,
              transition: 'all 0.3s ease',
            }}
            hoverable
            onMouseEnter={e => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = token.boxShadow;
            }}
            onMouseLeave={e => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            <Statistic
              title={
                <span style={{ color: stat.color }}>
                  {stat.icon} {stat.title}
                </span>
              }
              value={stat.value}
              valueStyle={{
                color: stat.highlight ? stat.color : token.colorText,
                fontWeight: stat.highlight ? 'bold' : 'normal',
              }}
            />
          </Card>
        </Col>
      ))}
    </Row>
  );
};

export default DashboardStatistics;
