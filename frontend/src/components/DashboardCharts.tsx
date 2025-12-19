import React from 'react';
import { Card, Row, Col } from 'antd';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const chartColors = {
  success: 'var(--success-color)',
  warning: 'var(--warning-color)',
  error: 'var(--error-color)',
  info: 'var(--text-secondary)'
};


interface DashboardChartsProps {
  dashboardData: any;
}

const DashboardCharts: React.FC<DashboardChartsProps> = ({
  dashboardData
}) => {


  // Подготовка данных для линейного графика трендов с мемоизацией
  const trendData = React.useMemo(() => {
    if (!dashboardData) return [];
    return dashboardData.recent_results.slice(0, 7).map(result => ({
      date: new Date(result.timestamp).toLocaleDateString(),
      critical: result.critical || 0,
      warning: result.warning || 0,
      info: result.info || 0,
      passed: dashboardData.total_rules - (result.critical || 0) - (result.warning || 0) - (result.info || 0)
    }));
  }, [dashboardData]);

  return (
    <>
      <Row gutter={16} className="dashboard-row">
        <Col span={24}>
          <Card title="Тренды ошибок (7 дней)">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="critical" stroke="var(--error-color)" name="Критические" />
                <Line type="monotone" dataKey="warning" stroke="var(--warning-color)" name="Предупреждения" />
                <Line type="monotone" dataKey="info" stroke="var(--text-secondary)" name="Другие" />
                <Line type="monotone" dataKey="passed" stroke="var(--success-color)" name="Успешно" />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>
    </>
  );
};

export default DashboardCharts;