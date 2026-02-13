import React from 'react';
import { Tag } from 'antd';
import { LockOutlined, KeyOutlined, FileTextOutlined, TagOutlined } from '@ant-design/icons';

// Color mapping for status tags using Ant Design color props
const statusColorMap: Record<string, string> = {
  passed: 'success',
  success: 'success',
  failed: 'error',
  exception: 'error',
  warning: 'warning',
  pending: 'warning',
  running: 'processing',
  completed: 'success',
  cancelled: 'default',
  unknown: 'default',
  error: 'error',
  critical: 'error',
  high: 'error',
  medium: 'warning',
  low: 'processing',
  info: 'processing',
  ok: 'success',
  enabled: 'success',
  disabled: 'error',
  configured: 'success',
  'not-configured': 'error',
  expired: 'error',
  'expires-soon': 'warning',
  valid: 'success',
  ready: 'success',
  'not-ready': 'warning',
};

// Color mapping for secret type tags
const secretTypeColorMap: Record<string, string> = {
  password: 'purple',
  'ssh-key': 'cyan',
  kubeconfig: 'magenta',
  default: 'blue',
};

// Utility functions for status tags
export const getStatusTag = (status: string | null | undefined, text?: string) => {
  const normalizedStatus = status?.toLowerCase() || 'unknown';
  const color = statusColorMap[normalizedStatus] || 'default';
  // Only use text if it's a string, otherwise use status or 'Unknown'
  const displayText = typeof text === 'string' ? text : (status || 'Unknown');
  return <Tag color={color}>{displayText}</Tag>;
};

export const getSeverityTag = (severity: string) => {
  const normalizedSeverity = severity?.toLowerCase() || 'unknown';
  const color = statusColorMap[normalizedSeverity] || 'default';
  const displayText = severity?.charAt(0).toUpperCase() + severity?.slice(1) || 'Unknown';
  return <Tag color={color}>{displayText}</Tag>;
};

export const getSecretTypeTag = (type: string) => {
  const normalizedType = type?.replace('_', '-') || 'default';
  const color = secretTypeColorMap[normalizedType] || 'default';

  const getIcon = (type: string) => {
    switch (type) {
      case 'password':
        return <LockOutlined />;
      case 'ssh_key':
        return <KeyOutlined />;
      case 'kubeconfig':
        return <FileTextOutlined />;
      default:
        return null;
    }
  };

  return (
    <Tag color={color} icon={getIcon(type)}>
      {type}
    </Tag>
  );
};

// Color mapping for inspection rule tags - generates consistent colors based on tag name
const getTagColor = (tag: string): string => {
  const colors = [
    'magenta',
    'red',
    'volcano',
    'orange',
    'gold',
    'lime',
    'green',
    'cyan',
    'blue',
    'geekblue',
    'purple',
  ];

  // Simple hash function to get consistent color for same tag
  let hash = 0;
  for (let i = 0; i < tag.length; i++) {
    hash = tag.charCodeAt(i) + ((hash << 5) - hash);
  }

  const index = Math.abs(hash) % colors.length;
  return colors[index];
};

export const getInspectionRuleTag = (tag: string) => {
  return (
    <Tag color={getTagColor(tag)} icon={<TagOutlined />}>
      {tag}
    </Tag>
  );
};

export const getSeverityBadge = (
  count: number,
  _type: 'critical' | 'warning' | 'other' | 'passed'
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
