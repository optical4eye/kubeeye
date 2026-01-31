import React, { useMemo, useState } from 'react';
import { Card, Row, Col, theme, Typography, Divider, Checkbox, Modal, Segmented, Skeleton } from 'antd';
import { useTranslation } from 'react-i18next';
import { Area } from '@ant-design/charts';
import { useUIStore } from '../../stores/uiStore';

interface DashboardChartsProps {
  dashboardData: {
    recent_results?: Array<{
      timestamp: string;
      critical?: number;
      warning?: number;
      info?: number;
      passed?: number;
    }>;
    total_rules?: number;
  } | null;
}

const DashboardCharts: React.FC<DashboardChartsProps> = ({ dashboardData }) => {
  const { t } = useTranslation();
  const { theme: uiTheme } = useUIStore();
  const { token } = theme.useToken();

  const { Title } = Typography;

  const selectedCategories = ['critical', 'warning', 'info', 'passed'];

    // Подготовка данных для stacked area chart в long format с фильтрами
  const longData = useMemo(() => {
    if (!dashboardData || !dashboardData.recent_results) return [];
    const sorted = dashboardData.recent_results
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
      .slice(-7);
    const result = [];
    sorted.forEach(resultItem => {
      const date = new Date(resultItem.timestamp).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }).replace(', ', '-');
      const critical = resultItem.critical || 0;
      const warning = resultItem.warning || 0;
      const info = resultItem.info || 0;
      const passed = resultItem.passed || 0;
      if (selectedCategories.includes('critical')) result.push({ date, value: critical, category: 'critical' });
      if (selectedCategories.includes('warning')) result.push({ date, value: warning, category: 'warning' });
      if (selectedCategories.includes('info')) result.push({ date, value: info, category: 'info' });
      if (selectedCategories.includes('passed')) result.push({ date, value: passed, category: 'passed' });
    });
    return result;
  }, [dashboardData, selectedCategories]);

  const categoryTranslations = {
    critical: t('charts.critical'),
    warning: t('charts.warning'),
    info: t('charts.info'),
    passed: t('charts.passed'),
  };

  const config = {
    data: longData,
    xField: 'date',
    yField: 'value',
    colorField: 'category',
    stack: true,
    shapeField: 'smooth',
    theme: uiTheme === 'dark' ? 'dark' : 'light',
    scale: {
      color: {
        domain: ['critical', 'warning', 'info', 'passed'],
        range: [token.colorError, token.colorWarning, token.colorInfo, token.colorSuccess]
      }
    },
    axis: {
      x: {
        labelTransform: 'rotate(0)',
      },
    },
    tooltip: {
      customContent: (title, data) => {
        if (!data || data.length === 0) return null;
        const total = data.reduce((sum, item) => sum + item.value, 0);
        return (
          <div
            className="dashboard-charts-tooltip"
            role="tooltip"
            aria-live="polite"
          >
            <p>{`${t('charts.date')}: ${title}`}</p>
            {data.map((item, index) => {
              const percentage = total > 0 ? ((item.value / total) * 100).toFixed(1) : '0';
              return (
                <p
                  key={index}
                  className="dashboard-charts-tooltip-item kube-text-error"
                  aria-label={`${categoryTranslations[item.category]}: ${item.value} (${percentage}%)`}
                >
                  {`${categoryTranslations[item.category]}: ${item.value} (${percentage}%)`}
                </p>
              );
            })}
          </div>
        );
      },
    },
    legend: true,
    autoFit: true,
    accessibility: {
      enabled: true,
      description: t('charts.errorTrends'),
    },
  };

  if (!longData || longData.length === 0) {
    return (
      <Row gutter={[16, 16]} className="dashboard-row">
        <Col xs={24} sm={24} md={24} lg={24} xl={24}>
          <Card
            title={
              <Title level={4} style={{ margin: 0 }}>
                {t('charts.errorTrends')}
              </Title>
            }
            aria-label={t('charts.errorTrends')}
            role="region"
          >
            <div
              className="dashboard-charts-no-data"
              role="status"
              aria-live="polite"
            >
              {t('charts.noData')}
            </div>
          </Card>
        </Col>
      </Row>
    );
  }

  return (
    <>
      <Row gutter={[16, 16]} className="dashboard-row">
        <Col xs={24} sm={24} md={24} lg={24} xl={24}>
          <Card
            title={
              <Title level={4} style={{ margin: 0 }}>
                {t('charts.errorTrends')}
              </Title>
            }
            aria-label={t('charts.errorTrends')}
            role="region"
            bordered={false}
            style={{ boxShadow: token.boxShadowTertiary }}
          >
            <div
              className="dashboard-charts-container"
              role="img"
              aria-label={`${t('charts.errorTrends')} ${t('charts.chart')}`}
              tabIndex={0}
            >
              <Area {...config} />
            </div>
          </Card>
        </Col>
      </Row>
    </>
  );
};

export default React.memo(DashboardCharts);
