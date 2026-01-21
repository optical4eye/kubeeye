import React from 'react';
import { Card, Row, Col } from 'antd';
import { useTranslation } from 'react-i18next';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface DashboardChartsProps {
  dashboardData: {
    recent_results?: Array<{
      timestamp: string;
      critical?: number;
      warning?: number;
      info?: number;
    }>;
    total_rules?: number;
  } | null;
}

const DashboardCharts: React.FC<DashboardChartsProps> = ({ dashboardData }) => {
  const { t } = useTranslation();
  // Подготовка данных для линейного графика трендов с мемоизацией
  const trendData = React.useMemo(() => {
    if (!dashboardData || !dashboardData.recent_results) return [];
    return dashboardData.recent_results
      .slice(0, 7)
      .map((result: { timestamp: string; critical?: number; warning?: number; info?: number }) => ({
        date: new Date(result.timestamp).toLocaleDateString(),
        critical: result.critical || 0,
        warning: result.warning || 0,
        info: result.info || 0,
        passed:
          (dashboardData.total_rules || 0) -
          (result.critical || 0) -
          (result.warning || 0) -
          (result.info || 0),
      }));
  }, [dashboardData]);

  if (!trendData || trendData.length === 0) {
    return (
      <Row gutter={16} className="dashboard-row">
        <Col span={24}>
          <Card title={t('charts.errorTrends')}>
            <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-secondary)' }}>
              {t('charts.noData')}
            </div>
          </Card>
        </Col>
      </Row>
    );
  }

  return (
    <>
      <Row gutter={16} className="dashboard-row">
        <Col span={24}>
          <Card title={t('charts.errorTrends')}>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--ant-color-bg-layout)',
                    color: 'var(--ant-color-text)',
                    border: '1px solid var(--ant-color-border)',
                    borderRadius: '4px',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
                  }}
                  formatter={(value: number, name: string) => [`${value}`, name]}
                  labelFormatter={(label: string) => `${t('charts.date')}: ${label}`}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="critical"
                  stroke="var(--ant-color-error)"
                  name={t('charts.critical')}
                />
                <Line
                  type="monotone"
                  dataKey="warning"
                  stroke="var(--ant-color-warning)"
                  name={t('charts.warning')}
                />
                <Line type="monotone" dataKey="info" stroke="var(--ant-color-info)" name={t('charts.other')} />
                <Line
                  type="monotone"
                  dataKey="passed"
                  stroke="var(--ant-color-success)"
                  name={t('charts.successful')}
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>
    </>
  );
};

export default DashboardCharts;
