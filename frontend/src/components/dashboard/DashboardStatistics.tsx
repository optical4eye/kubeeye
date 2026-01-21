import React from 'react';
import { Row, Col, Statistic } from 'antd';
import { useTranslation } from 'react-i18next';

interface DashboardStatisticsProps {
  dashboardData: unknown;
}

const DashboardStatistics: React.FC<DashboardStatisticsProps> = ({ dashboardData }) => {
  const { t } = useTranslation();
  const {
    recent_results = [],
    total_clusters = 0,
    recent_scans = 0,
    latest_scan_time = t('dashboard.noData'),
    total_rules = 0,
  } = dashboardData || {};

  return (
    <Row gutter={16} className="dashboard-row">
      <Col xs={24} sm={12} md={8} lg={6} xl={3}>
        <Statistic title={t('statistics.clusters')} value={total_clusters} />
      </Col>
      <Col xs={24} sm={12} md={8} lg={6} xl={3}>
        <Statistic title={t('statistics.inspections')} value={recent_scans} />
      </Col>
      <Col xs={24} sm={12} md={8} lg={6} xl={3}>
        <Statistic
          title={t('statistics.critical')}
          value={recent_results.reduce((sum, r) => sum + (r.critical || 0), 0)}
        />
      </Col>
      <Col xs={24} sm={12} md={8} lg={6} xl={3}>
        <Statistic
          title={t('statistics.warning')}
          value={recent_results.reduce((sum, r) => sum + (r.warning || 0), 0)}
        />
      </Col>
      <Col xs={24} sm={12} md={8} lg={6} xl={3}>
        <Statistic
          title={t('statistics.other')}
          value={recent_results.reduce((sum, r) => sum + (r.info || 0), 0)}
        />
      </Col>
      <Col xs={24} sm={12} md={8} lg={6} xl={3}>
        <Statistic
          title={t('statistics.successful')}
          value={recent_results.reduce((sum, r) => sum + (r.passed || 0), 0)}
        />
      </Col>
      <Col xs={24} sm={12} md={8} lg={6} xl={3}>
        <Statistic title={t('statistics.last')} value={latest_scan_time} />
      </Col>
      <Col xs={24} sm={12} md={8} lg={6} xl={3}>
        <Statistic title={t('statistics.rules')} value={total_rules} />
      </Col>
    </Row>
  );
};

export default DashboardStatistics;
