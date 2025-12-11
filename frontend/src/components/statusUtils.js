import React from 'react';
import { Tag } from 'antd';

// Utility functions for status tags
export const getStatusTag = (status) => {
  switch (status) {
    case 'passed':
    case 'success':
      return <Tag color="var(--success-color)">Успешно</Tag>;
    case 'exception':
      return <Tag color="var(--error-color)">Ошибка</Tag>;
    case 'failed':
      return <Tag color="var(--error-color)">Неудачно</Tag>;
    case 'warning':
      return <Tag color="var(--warning-color)">Предупреждение</Tag>;
    default:
      return <Tag color="var(--accent-color)">Неизвестно</Tag>;
  }
};

export const getSeverityTag = (severity) => {
  switch (severity) {
    case 'critical':
      return <Tag color="var(--error-color)">Критично</Tag>;
    case 'warning':
      return <Tag color="var(--warning-color)">Предупреждение</Tag>;
    case 'info':
      return <Tag color="var(--accent-color)">Информация</Tag>;
    default:
      return <Tag color="var(--secondary-color)">Неизвестно</Tag>;
  }
};

export const getTaskStatusIcon = (status) => {
  switch (status) {
    case 'pending':
      return <span style={{ color: 'var(--status-pending)' }}>⏳</span>;
    case 'running':
      return <span style={{ color: 'var(--status-running)' }}>🔄</span>;
    case 'completed':
      return <span style={{ color: 'var(--status-completed)' }}>✅</span>;
    case 'failed':
      return <span style={{ color: 'var(--error-color)' }}>❌</span>;
    case 'cancelled':
      return <span style={{ color: 'var(--status-cancelled)' }}>🚫</span>;
    default:
      return <span>⏳</span>;
  }
};

export const getTaskStatusColor = (status) => {
  switch (status) {
    case 'pending':
      return 'orange';
    case 'running':
      return 'blue';
    case 'completed':
      return 'green';
    case 'failed':
      return 'red';
    case 'cancelled':
      return 'default';
    default:
      return 'default';
  }
};

export const getInspectionStatusTag = (report) => {
  const totalIssues = (report.critical || 0) + (report.warning || 0) + (report.info || 0);
  if (totalIssues === 0) {
    return <Tag color="var(--success-color)">OK</Tag>;
  } else if (report.critical > 0) {
    return <Tag color="var(--error-color)">Критические ошибки</Tag>;
  } else if (report.warning > 0) {
    return <Tag color="var(--warning-color)">Предупреждения</Tag>;
  } else {
    return <Tag color="var(--accent-color)">Другие ошибки</Tag>;
  }
};