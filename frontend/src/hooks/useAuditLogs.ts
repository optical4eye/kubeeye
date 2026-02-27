import { useState, useCallback } from 'react';
import type { MessageInstance } from 'antd/es/message/interface';
import { useTranslation } from 'react-i18next';
import { getAuditLogs, getAuditLog, getAuditStats, cleanupAuditLogs } from '../services/api';

export interface AuditLog {
  id: string;
  user_id: number;
  username: string;
  action: string;
  resource_type?: string;
  resource_id?: string;
  resource_name?: string;
  details?: any;
  ip_address?: string;
  user_agent?: string;
  status: string;
  error_message?: string;
  created_at: string;
}

export interface AuditStats {
  total: number;
  by_action: Record<string, number>;
  by_user: Record<string, number>;
  by_status: Record<string, number>;
  by_resource: Record<string, number>;
}

export interface AuditLogsParams {
  offset?: number;
  limit?: number;
  user_id?: string;
  username?: string;
  action?: string;
  resource_type?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
}

interface UseAuditLogsOptions {
  /** Message API instance from App.useApp() */
  messageApi?: MessageInstance;
}

export const useAuditLogs = (options?: UseAuditLogsOptions) => {
  const { t } = useTranslation();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);

  const fetchAuditLogs = useCallback(async (params: AuditLogsParams = {}) => {
    setLoading(true);
    try {
      const response = await getAuditLogs(params);
      setLogs(response.data.logs);
      setTotal(response.data.total);
    } catch (error) {
      options?.messageApi?.error(t('auditLogs.title') + ': ' + t('errors.loadClusters'));
      console.error('Error fetching audit logs:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchAuditLog = useCallback(async (logId: string) => {
    setLoading(true);
    try {
      const response = await getAuditLog(logId);
      return response.data;
    } catch (error) {
      options?.messageApi?.error(t('auditLogs.title') + ': ' + t('errors.loadClusters'));
      console.error('Error fetching audit log:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchAuditStats = useCallback(async (dateFrom?: string, dateTo?: string) => {
    setLoading(true);
    try {
      const response = await getAuditStats(dateFrom, dateTo);
      return response.data;
    } catch (error) {
      options?.messageApi?.error(t('auditLogs.statistics') + ': ' + t('errors.loadClusters'));
      console.error('Error fetching audit stats:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  const cleanupLogs = useCallback(async () => {
    setLoading(true);
    try {
      const response = await cleanupAuditLogs();
      options?.messageApi?.success(
        t('auditLogs.messages.cleanupSuccess', { count: response.data.deleted_count })
      );
      await fetchAuditLogs();
      return response.data;
    } catch (error) {
      options?.messageApi?.error(t('auditLogs.messages.cleanupError'));
      console.error('Error cleaning up logs:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, [fetchAuditLogs]);

  return {
    logs,
    loading,
    total,
    fetchAuditLogs,
    fetchAuditLog,
    fetchAuditStats,
    cleanupLogs,
  };
};
