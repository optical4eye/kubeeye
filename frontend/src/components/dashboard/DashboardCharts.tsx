import React from 'react';
import { Card, Row, Col } from 'antd';
import { useTranslation } from 'react-i18next';
import {
  AreaChart,
  Area,
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

  // Custom Tooltip component with percentages
  const CustomTooltip = React.useCallback(
    ({ active, payload, label }: any) => {
      if (active && payload && payload.length) {
        const total = payload.reduce((sum: number, entry: any) => sum + entry.value, 0);
        return (
          <div
            style={{
              backgroundColor: 'var(--ant-color-bg-layout)',
              color: 'var(--ant-color-text)',
              border: '1px solid var(--ant-color-border)',
              borderRadius: '4px',
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
              padding: '10px',
            }}
          >
            <p>{`${t('charts.date')}: ${label}`}</p>
            {payload.map((entry: any, index: number) => {
              const percentage = total > 0 ? ((entry.value / total) * 100).toFixed(1) : '0';
              return (
                <p key={index} style={{ color: entry.color }}>
                  {`${entry.name}: ${entry.value} (${percentage}%)`}
                </p>
              );
            })}
          </div>
        );
      }
      return null;
    },
    [t]
  );

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
              <AreaChart data={trendData} aria-label={t('charts.errorTrends')}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip content={<CustomTooltip />} />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="critical"
                  stackId="1"
                  stroke="var(--ant-color-error)"
                  fill="var(--ant-color-error)"
                  name={t('charts.critical')}
                  aria-label={t('charts.critical')}
                  role="img"
                />
                <Area
                  type="monotone"
                  dataKey="warning"
                  stackId="1"
                  stroke="var(--ant-color-warning)"
                  fill="var(--ant-color-warning)"
                  name={t('charts.warning')}
                  aria-label={t('charts.warning')}
                  role="img"
                />
                <Area
                  type="monotone"
                  dataKey="info"
                  stackId="1"
                  stroke="var(--ant-color-info)"
                  fill="var(--ant-color-info)"
                  name={t('charts.other')}
                  aria-label={t('charts.other')}
                  role="img"
                />
                <Area
                  type="monotone"
                  dataKey="passed"
                  stackId="1"
                  stroke="var(--ant-color-success)"
                  fill="var(--ant-color-success)"
                  name={t('charts.successful')}
                  aria-label={t('charts.successful')}
                  role="img"
                />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>
    </>
  );
};

export default DashboardCharts;
