import React from 'react';
import { Tag } from 'antd';

// Utility functions for status tags
export const getStatusTag = status => {
  switch (status) {
    case 'passed':
    case 'success':
      return <Tag className="status-passed">Успешно</Tag>;
    case 'exception':
      return <Tag className="status-exception">Ошибка</Tag>;
    case 'failed':
      return <Tag className="status-failed">Неудачно</Tag>;
    case 'warning':
      return <Tag className="status-warning">Предупреждение</Tag>;
    case 'pending':
      return <Tag className="status-pending">Ожидает</Tag>;
    case 'running':
      return <Tag className="status-running">Выполняется</Tag>;
    case 'completed':
      return <Tag className="status-completed">Завершено</Tag>;
    case 'cancelled':
      return <Tag className="status-cancelled">Отменено</Tag>;
    case 'unknown':
      return <Tag className="status-unknown">Неизвестно</Tag>;
    default:
      return <Tag className="status-unknown">Неизвестно</Tag>;
  }
};

export const getSeverityTag = severity => {
  switch (severity) {
    case 'critical':
      return <Tag className="status-critical">Критическая</Tag>;
    case 'high':
      return <Tag className="status-high">Высокая</Tag>;
    case 'medium':
      return <Tag className="status-medium">Средняя</Tag>;
    case 'low':
      return <Tag className="status-low">Низкая</Tag>;
    case 'warning':
      return <Tag className="status-warning">Предупреждение</Tag>;
    case 'info':
      return <Tag className="status-info">Информация</Tag>;
    default:
      return <Tag className="status-unknown">Неизвестная</Tag>;
  }
};

export const getTaskStatusIcon = status => {
  switch (status) {
    case 'pending':
      return <span className="text-status-pending"></span>;
    case 'running':
      return <span className="text-status-running"></span>;
    case 'completed':
      return <span className="text-status-completed"></span>;
    case 'failed':
      return <span className="text-error"></span>;
    case 'cancelled':
      return <span className="text-status-cancelled"></span>;
    default:
      return <span>⏳</span>;
  }
};
