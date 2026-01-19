import React from 'react';
import { Row, Col, Statistic } from 'antd';

interface DashboardStatisticsProps {
  dashboardData: unknown;
}

const DashboardStatistics: React.FC<DashboardStatisticsProps> = ({ dashboardData }) => {
  const {
    recent_results = [],
    total_clusters = 0,
    recent_scans = 0,
    latest_scan_time = 'Нет данных',
    total_rules = 0,
  } = dashboardData || {};

  return (
    <Row gutter={16} className="dashboard-row">
      <Col xs={24} sm={12} md={8} lg={6} xl={3}>
        <Statistic title="Кластеры" value={total_clusters} />
      </Col>
      <Col xs={24} sm={12} md={8} lg={6} xl={3}>
        <Statistic title="Инспекций" value={recent_scans} />
      </Col>
      <Col xs={24} sm={12} md={8} lg={6} xl={3}>
        <Statistic
          title="Критические"
          value={recent_results.reduce((sum, r) => sum + (r.critical || 0), 0)}
        />
      </Col>
      <Col xs={24} sm={12} md={8} lg={6} xl={3}>
        <Statistic
          title="Предупреждения"
          value={recent_results.reduce((sum, r) => sum + (r.warning || 0), 0)}
        />
      </Col>
      <Col xs={24} sm={12} md={8} lg={6} xl={3}>
        <Statistic
          title="Другие"
          value={recent_results.reduce((sum, r) => sum + (r.info || 0), 0)}
        />
      </Col>
      <Col xs={24} sm={12} md={8} lg={6} xl={3}>
        <Statistic
          title="Успешно"
          value={recent_results.reduce((sum, r) => sum + (r.passed || 0), 0)}
        />
      </Col>
      <Col xs={24} sm={12} md={8} lg={6} xl={3}>
        <Statistic title="Последняя" value={latest_scan_time} />
      </Col>
      <Col xs={24} sm={12} md={8} lg={6} xl={3}>
        <Statistic title="Правил" value={total_rules} />
      </Col>
    </Row>
  );
};

export default DashboardStatistics;
