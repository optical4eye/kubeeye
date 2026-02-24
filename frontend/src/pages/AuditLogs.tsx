import React, { useEffect, useState } from 'react';
import {
  Table,
  Button,
  DatePicker,
  Select,
  Input,
  Space,
  Modal,
  Tag,
  Card,
  Statistic,
  Row,
  Col,
  Collapse,
} from 'antd';
import { SearchOutlined, ReloadOutlined, DeleteOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAuditLogs, AuditLogsParams, AuditStats } from '../hooks/useAuditLogs';
import { getAuditCleanupConfig } from '../services/api';
import type { Dayjs } from 'dayjs';

const { RangePicker } = DatePicker;
const { Option } = Select;

const AuditLogsPage: React.FC = () => {
  const { t } = useTranslation();
  const { logs, loading, total, fetchAuditLogs, fetchAuditStats, cleanupLogs } = useAuditLogs();

  const [filters, setFilters] = useState<AuditLogsParams>({ limit: 20, offset: 0 });
  const [isStatsModalVisible, setIsStatsModalVisible] = useState(false);
  const [stats, setStats] = useState<AuditStats | null>(null);
  const [cleanupConfig, setCleanupConfig] = useState<any>(null);

  useEffect(() => {
    fetchAuditLogs(filters);
  }, [fetchAuditLogs, filters]);

  useEffect(() => {
    const loadCleanupConfig = async () => {
      try {
        const response = await getAuditCleanupConfig();
        setCleanupConfig(response.data);
      } catch {
        // Error loading cleanup config
      }
    };
    loadCleanupConfig();
  }, []);

  const handleFilterChange = (key: string, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value, offset: 0 }));
  };

  const handleDateRangeChange = (dates: [Dayjs | null, Dayjs | null] | null) => {
    if (dates && dates[0] && dates[1]) {
      setFilters(prev => ({
        ...prev,
        date_from: dates[0].toISOString(),
        date_to: dates[1].toISOString(),
        offset: 0,
      }));
    } else {
      setFilters(prev => ({
        ...prev,
        date_from: undefined,
        date_to: undefined,
        offset: 0,
      }));
    }
  };

  const handleResetFilters = () => {
    setFilters({ limit: 20, offset: 0 });
  };

  const handleShowStats = async () => {
    try {
      const statsData = await fetchAuditStats(filters.date_from, filters.date_to);
      setStats(statsData);
      setIsStatsModalVisible(true);
    } catch {
      // Error already handled in hook
    }
  };

  const handleCleanup = async () => {
    try {
      await cleanupLogs();
    } catch {
      // Error already handled in hook
    }
  };

  const columns = [
    {
      title: t('auditLogs.date'),
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => new Date(date).toLocaleString('ru-RU'),
    },
    {
      title: t('auditLogs.user'),
      dataIndex: 'username',
      key: 'username',
      width: 150,
    },
    {
      title: t('auditLogs.action'),
      dataIndex: 'action',
      key: 'action',
      width: 120,
      render: (action: string) => {
        const actionLabels: Record<string, string> = {
          login: t('auditLogs.actionTypes.login'),
          logout: t('auditLogs.actionTypes.logout'),
          create: t('auditLogs.actionTypes.create'),
          update: t('auditLogs.actionTypes.update'),
          delete: t('auditLogs.actionTypes.delete'),
          read: t('auditLogs.actionTypes.read'),
          run: t('auditLogs.actionTypes.run'),
          check: t('auditLogs.actionTypes.check'),
          scan: t('auditLogs.actionTypes.scan'),
        };
        return actionLabels[action] || action;
      },
    },
    {
      title: t('auditLogs.resourceType'),
      dataIndex: 'resource_type',
      key: 'resource_type',
      width: 120,
      render: (resourceType: string) => {
        const resourceTypeLabels: Record<string, string> = {
          auth: t('auditLogs.resourceTypes.auth'),
          user: t('auditLogs.resourceTypes.user'),
          cluster: t('auditLogs.resourceTypes.cluster'),
          secret: t('auditLogs.resourceTypes.secret'),
          task: t('auditLogs.resourceTypes.task'),
          report: t('auditLogs.resourceTypes.report'),
          inspection: t('auditLogs.resourceTypes.inspection'),
          inspection_task: t('auditLogs.resourceTypes.inspectionTask'),
          popeye_task: t('auditLogs.resourceTypes.popeyeTask'),
          network_check: t('auditLogs.resourceTypes.networkCheck'),
        };
        return resourceTypeLabels[resourceType] || resourceType;
      },
    },
    {
      title: t('auditLogs.resourceName'),
      dataIndex: 'resource_name',
      key: 'resource_name',
      width: 150,
      render: (name: string | undefined) => name || '-',
    },
    {
      title: t('auditLogs.ipAddress'),
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 130,
      render: (ip: string | undefined) => ip || '-',
    },
    {
      title: t('auditLogs.status'),
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={status === 'success' ? 'green' : 'red'}>
          {status === 'success' ? t('auditLogs.statusSuccess') : t('auditLogs.statusFailure')}
        </Tag>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div
        style={{
          marginBottom: '16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <h2>{t('auditLogs.title')}</h2>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => fetchAuditLogs(filters)}>
            {t('auditLogs.refresh')}
          </Button>
          <Button icon={<DeleteOutlined />} onClick={handleCleanup}>
            {t('auditLogs.cleanup')}
          </Button>
          <Button type="primary" icon={<SearchOutlined />} onClick={handleShowStats}>
            {t('auditLogs.statistics')}
          </Button>
        </Space>
      </div>

      {cleanupConfig && (
        <Collapse
          className="margin-bottom-space-4"
          items={[
            {
              key: 'cleanup-info',
              label: t('auditLogs.cleanupInfo'),
              children: (
                <div>
                  <p>{t('auditLogs.autoDelete')}</p>
                  <ul className="margin-top-space-2">
                    <li>
                      <strong>{t('auditLogs.retentionPeriod')}</strong>{' '}
                      {cleanupConfig.retention_days} {t('clusters.days')}
                    </li>
                  </ul>
                  <p className="margin-top-space-2">
                    <strong>{t('auditLogs.note')}</strong> {t('auditLogs.autoCleanup')}
                  </p>
                </div>
              ),
            },
          ]}
        />
      )}

      <Card style={{ marginBottom: '16px' }}>
        <Space wrap style={{ width: '100%' }}>
          <Input
            placeholder={t('auditLogs.filters.searchUser')}
            prefix={<SearchOutlined />}
            style={{ width: 200 }}
            onChange={e => handleFilterChange('username', e.target.value)}
            allowClear
          />

          <Select
            placeholder={t('auditLogs.filters.action')}
            style={{ width: 150 }}
            onChange={value => handleFilterChange('action', value)}
            allowClear
          >
            <Option value="login">{t('auditLogs.actionTypes.login')}</Option>
            <Option value="logout">{t('auditLogs.actionTypes.logout')}</Option>
            <Option value="create">{t('auditLogs.actionTypes.create')}</Option>
            <Option value="update">{t('auditLogs.actionTypes.update')}</Option>
            <Option value="delete">{t('auditLogs.actionTypes.delete')}</Option>
            <Option value="read">{t('auditLogs.actionTypes.read')}</Option>
            <Option value="run">{t('auditLogs.actionTypes.run')}</Option>
            <Option value="check">{t('auditLogs.actionTypes.check')}</Option>
            <Option value="scan">{t('auditLogs.actionTypes.scan')}</Option>
          </Select>

          <Select
            placeholder={t('auditLogs.filters.resourceType')}
            style={{ width: 150 }}
            onChange={value => handleFilterChange('resource_type', value)}
            allowClear
          >
            <Option value="auth">{t('auditLogs.resourceTypes.auth')}</Option>
            <Option value="user">{t('auditLogs.resourceTypes.user')}</Option>
            <Option value="cluster">{t('auditLogs.resourceTypes.cluster')}</Option>
            <Option value="secret">{t('auditLogs.resourceTypes.secret')}</Option>
            <Option value="task">{t('auditLogs.resourceTypes.task')}</Option>
            <Option value="report">{t('auditLogs.resourceTypes.report')}</Option>
            <Option value="inspection">{t('auditLogs.resourceTypes.inspection')}</Option>
            <Option value="inspection_task">{t('auditLogs.resourceTypes.inspectionTask')}</Option>
            <Option value="popeye_task">{t('auditLogs.resourceTypes.popeyeTask')}</Option>
            <Option value="network_check">{t('auditLogs.resourceTypes.networkCheck')}</Option>
          </Select>

          <Select
            placeholder={t('auditLogs.filters.status')}
            style={{ width: 120 }}
            onChange={value => handleFilterChange('status', value)}
            allowClear
          >
            <Option value="success">{t('auditLogs.statusSuccess')}</Option>
            <Option value="failure">{t('auditLogs.statusFailure')}</Option>
          </Select>

          <RangePicker
            placeholder={[t('auditLogs.filters.dateFrom'), t('auditLogs.filters.dateTo')]}
            onChange={handleDateRangeChange}
            style={{ width: 300 }}
          />

          <Button onClick={handleResetFilters}>{t('auditLogs.filters.resetFilters')}</Button>
        </Space>
      </Card>

      <Table
        columns={columns}
        dataSource={logs}
        rowKey="id"
        loading={loading}
        pagination={{
          total: total,
          pageSize: filters.limit || 20,
          showSizeChanger: true,
          showTotal: total => t('auditLogs.totalRecords', { count: total }),
          current:
            filters.offset && filters.limit ? Math.floor(filters.offset / filters.limit) + 1 : 1,
          onChange: (page, pageSize) => {
            setFilters(prev => ({
              ...prev,
              offset: (page - 1) * pageSize,
              limit: pageSize,
            }));
          },
        }}
      />

      <Modal
        title={t('auditLogs.stats.title')}
        open={isStatsModalVisible}
        onCancel={() => setIsStatsModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setIsStatsModalVisible(false)}>
            {t('auditLogs.close')}
          </Button>,
        ]}
        width={800}
      >
        {stats && (
          <div>
            <Row gutter={16} style={{ marginBottom: '24px' }}>
              <Col span={8}>
                <Card>
                  <Statistic title={t('auditLogs.stats.totalRecords')} value={stats.total} />
                </Card>
              </Col>
              <Col span={8}>
                <Card>
                  <Statistic
                    title={t('auditLogs.stats.successful')}
                    value={stats.by_status?.success || 0}
                    valueStyle={{ color: '#3f8600' }}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card>
                  <Statistic
                    title={t('auditLogs.stats.failed')}
                    value={stats.by_status?.failure || 0}
                    valueStyle={{ color: '#cf1322' }}
                  />
                </Card>
              </Col>
            </Row>

            <Card title={t('auditLogs.stats.byAction')} style={{ marginBottom: '16px' }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                {Object.entries(stats.by_action || {}).map(([action, count]) => (
                  <div key={action} style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>{action}</span>
                    <Tag>{count}</Tag>
                  </div>
                ))}
              </Space>
            </Card>

            <Card title={t('auditLogs.stats.byUser')} style={{ marginBottom: '16px' }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                {Object.entries(stats.by_user || {}).map(([username, count]) => (
                  <div key={username} style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>{username}</span>
                    <Tag>{count}</Tag>
                  </div>
                ))}
              </Space>
            </Card>

            <Card title={t('auditLogs.stats.byResource')}>
              <Space direction="vertical" style={{ width: '100%' }}>
                {Object.entries(stats.by_resource || {}).map(([resourceType, count]) => (
                  <div
                    key={resourceType}
                    style={{ display: 'flex', justifyContent: 'space-between' }}
                  >
                    <span>{resourceType}</span>
                    <Tag>{count}</Tag>
                  </div>
                ))}
              </Space>
            </Card>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default AuditLogsPage;
