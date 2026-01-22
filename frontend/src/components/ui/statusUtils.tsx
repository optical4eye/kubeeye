import React from 'react';
import { Tag } from 'antd';

// Utility functions for status tags
export const getStatusTag = (status: string) => {
  switch (status) {
    case 'passed':
    case 'success':
      return <Tag color="success">Passed</Tag>;
    case 'exception':
      return <Tag color="error">Error</Tag>;
    case 'failed':
      return <Tag color="error">Failed</Tag>;
    case 'warning':
      return <Tag color="warning">Warning</Tag>;
    case 'pending':
      return <Tag color="default">Pending</Tag>;
    case 'running':
      return <Tag color="processing">Running</Tag>;
    case 'completed':
      return <Tag color="success">Completed</Tag>;
    case 'cancelled':
      return <Tag color="default">Cancelled</Tag>;
    case 'unknown':
      return <Tag color="default">Unknown</Tag>;
    default:
      return <Tag color="default">Unknown</Tag>;
  }
};

export const getSeverityTag = (severity: string) => {
  switch (severity) {
    case 'critical':
      return <Tag color="error">Critical</Tag>;
    case 'high':
      return <Tag color="error">High</Tag>;
    case 'medium':
      return <Tag color="warning">Medium</Tag>;
    case 'warning':
      return <Tag color="warning">Warning</Tag>;
    case 'info':
      return <Tag color="processing">Info</Tag>;
    case 'other':
      return <Tag color="default">Other</Tag>;
    case 'passed':
      return <Tag color="success">Passed</Tag>;
    default:
      return <Tag color="default">Unknown</Tag>;
  }
};

export const getSeverityBadge = (
  count: number,
  type: 'critical' | 'warning' | 'other' | 'passed'
) => {
  if (count === 0) return count;

  return <span>{count}</span>;
};

export const getTaskStatusIcon = (status: string) => {
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
