import React, { useEffect, useState } from 'react';
import { Table, Button, DatePicker, Select, Input, Space, Modal, Descriptions, Tag, message, Card, Statistic, Row, Col, Collapse } from 'antd';
import { SearchOutlined, ReloadOutlined, DeleteOutlined, EyeOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAuditLogs, AuditLog, AuditLogsParams, AuditStats } from '../hooks/useAuditLogs';
import { getAuditCleanupConfig } from '../services/api';
import dayjs, { Dayjs } from 'dayjs';

const { RangePicker } = DatePicker;
const { Option } = Select;

const AuditLogsPage: React.FC = () => {
  const { t } = useTranslation();
  const { logs, loading, total, fetchAuditLogs, fetchAuditLog, fetchAuditStats, cleanupLogs } = useAuditLogs();

  const [filters, setFilters] = useState<AuditLogsParams>({ limit: 20, offset: 0 });
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [isDetailModalVisible, setIsDetailModalVisible] = useState(false);
  const [isStatsModalVisible, setIsStatsModalVisible] = useState(false);
  const [stats, setStats] = useState<AuditStats | null>(null);
  const [cleanupConfig, setCleanupConfig] = useState<any>(null);

  useEffect(() => {
    fetchAuditLogs(filters);
    loadCleanupConfig();
  }, [fetchAuditLogs, filters]);

  const loadCleanupConfig = async () => {
    try {
      const response = await getAuditCleanupConfig();
      setCleanupConfig(response.data);
    } catch {
      // Error loading cleanup config
    }
  };

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

  const handleViewDetails = async (log: AuditLog) => {
    try {
      const logDetails = await fetchAuditLog(log.id);
      setSelectedLog(logDetails);
      setIsDetailModalVisible(true);
    } catch (error) {
      // Error already handled in hook
    }
  };

  const handleShowStats = async () => {
    try {
      const statsData = await fetchAuditStats(filters.date_from, filters.date_to);
      setStats(statsData);
      setIsStatsModalVisible(true);
    } catch (error) {
      // Error already handled in hook
    }
  };

  const handleCleanup = async () => {
    try {
      await cleanupLogs();
    } catch (error) {
      // Error already handled in hook
    }
  };

  const columns = [
    {
      title: t('auditLogs.id'),
      dataIndex: 'id',
      key: 'id',
      width: 250,
      render: (id: string) => <span style={{ fontSize: '12px' }}>{id.substring(0, 8)}...</span>,
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
      width: 150,
      render: (action: string) => {
        const actionLabels: Record<string, string> = {
          login: t('auditLogs.actionTypes.login'),
          logout: t('auditLogs.actionTypes.logout'),
          password_change: t('auditLogs.actionTypes.passwordChange'),
          user_create: t('auditLogs.actionTypes.userCreate'),
          user_update: t('auditLogs.actionTypes.userUpdate'),
          user_delete: t('auditLogs.actionTypes.userDelete'),
          cluster_create: t('auditLogs.actionTypes.clusterCreate'),
          cluster_update: t('auditLogs.actionTypes.clusterUpdate'),
          cluster_delete: t('auditLogs.actionTypes.clusterDelete'),
          inspection_run: t('auditLogs.actionTypes.inspectionRun'),
          inspection_create: t('auditLogs.actionTypes.inspectionCreate'),
          inspection_delete: t('auditLogs.actionTypes.inspectionDelete'),
          report_create: t('auditLogs.actionTypes.reportCreate'),
          report_delete: t('auditLogs.actionTypes.reportDelete'),
          secret_create: t('auditLogs.actionTypes.secretCreate'),
          secret_update: t('auditLogs.actionTypes.secretUpdate'),
          secret_delete: t('auditLogs.actionTypes.secretDelete'),
          task_run: t('auditLogs.actionTypes.taskRun'),
          task_create: t('auditLogs.actionTypes.taskCreate'),
          task_delete: t('auditLogs.actionTypes.taskDelete'),
          network_check: t('auditLogs.actionTypes.networkCheck'),
          popeye_scan: t('auditLogs.actionTypes.popeyeScan'),
        };
        return actionLabels[action] || action;
      },
    },
    {
      title: t('auditLogs.resourceType'),
      dataIndex: 'resource_type',
      key: 'resource_type',
      width: 120,
    },
    {
      title: t('auditLogs.resourceId'),
      dataIndex: 'resource_id',
      key: 'resource_id',
      width: 150,
      render: (id: string | undefined) => id || '-',
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
    {
      title: t('auditLogs.date'),
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => new Date(date).toLocaleString('ru-RU'),
    },
    {
      title: t('auditLogs.actions'),
      key: 'actions',
      width: 100,
      render: (_: any, record: AuditLog) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetails(record)}
          >
            {t('auditLogs.view')}
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>{t('auditLogs.title')}</h2>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => fetchAuditLogs(filters)}
          >
            {t('auditLogs.refresh')}
          </Button>
          <Button
            icon={<DeleteOutlined />}
            onClick={handleCleanup}
          >
            {t('auditLogs.cleanup')}
          </Button>
          <Button
            type="primary"
            icon={<SearchOutlined />}
            onClick={handleShowStats}
          >
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
                      <strong>{t('auditLogs.retentionPeriod')}</strong> {cleanupConfig.retention_days}{' '}
                      {t('clusters.days')}
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
            onChange={(e) => handleFilterChange('username', e.target.value)}
            allowClear
          />

          <Select
            placeholder={t('auditLogs.filters.action')}
            style={{ width: 180 }}
            onChange={(value) => handleFilterChange('action', value)}
            allowClear
          >
            <Option value="login">{t('auditLogs.actionTypes.login')}</Option>
            <Option value="logout">{t('auditLogs.actionTypes.logout')}</Option>
            <Option value="password_change">{t('auditLogs.actionTypes.passwordChange')}</Option>
            <Option value="user_create">{t('auditLogs.actionTypes.userCreate')}</Option>
            <Option value="user_update">{t('auditLogs.actionTypes.userUpdate')}</Option>
            <Option value="user_delete">{t('auditLogs.actionTypes.userDelete')}</Option>
            <Option value="cluster_create">{t('auditLogs.actionTypes.clusterCreate')}</Option>
            <Option value="cluster_update">{t('auditLogs.actionTypes.clusterUpdate')}</Option>
            <Option value="cluster_delete">{t('auditLogs.actionTypes.clusterDelete')}</Option>
            <Option value="inspection_run">{t('auditLogs.actionTypes.inspectionRun')}</Option>
            <Option value="inspection_create">{t('auditLogs.actionTypes.inspectionCreate')}</Option>
            <Option value="inspection_delete">{t('auditLogs.actionTypes.inspectionDelete')}</Option>
            <Option value="report_create">{t('auditLogs.actionTypes.reportCreate')}</Option>
            <Option value="report_delete">{t('auditLogs.actionTypes.reportDelete')}</Option>
            <Option value="secret_create">{t('auditLogs.actionTypes.secretCreate')}</Option>
            <Option value="secret_update">{t('auditLogs.actionTypes.secretUpdate')}</Option>
            <Option value="secret_delete">{t('auditLogs.actionTypes.secretDelete')}</Option>
            <Option value="task_run">{t('auditLogs.actionTypes.taskRun')}</Option>
            <Option value="task_create">{t('auditLogs.actionTypes.taskCreate')}</Option>
            <Option value="task_delete">{t('auditLogs.actionTypes.taskDelete')}</Option>
            <Option value="popeye_scan">{t('auditLogs.actionTypes.popeyeScan')}</Option>
            <Option value="network_check">{t('auditLogs.actionTypes.networkCheck')}</Option>
          </Select>

          <Select
            placeholder={t('auditLogs.filters.status')}
            style={{ width: 120 }}
            onChange={(value) => handleFilterChange('status', value)}
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

          <Button onClick={handleResetFilters}>
            {t('auditLogs.filters.resetFilters')}
          </Button>
        </Space>
      </Card>

      <Table
        columns={columns}
        dataSource={logs}
        rowKey="id"
        loading={loading}
        pagination={{
          pageSize: filters.limit || 20,
          showSizeChanger: true,
          showTotal: (total) => t('auditLogs.totalRecords', { count: total }),
          current: filters.offset && filters.limit ? Math.floor(filters.offset / filters.limit) + 1 : 1,
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
        title={t('auditLogs.details')}
        open={isDetailModalVisible}
        onCancel={() => setIsDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setIsDetailModalVisible(false)}>
            {t('auditLogs.close')}
          </Button>,
        ]}
        width={800}
      >
        {selectedLog && (
          <Descriptions bordered column={2}>
            <Descriptions.Item label={t('auditLogs.id')}>{selectedLog.id}</Descriptions.Item>
            <Descriptions.Item label={t('auditLogs.user')}>{selectedLog.username}</Descriptions.Item>
            <Descriptions.Item label={t('auditLogs.action')}>{selectedLog.action}</Descriptions.Item>
            <Descriptions.Item label={t('auditLogs.resourceType')}>{selectedLog.resource_type || '-'}</Descriptions.Item>
            <Descriptions.Item label={t('auditLogs.resourceId')}>{selectedLog.resource_id || '-'}</Descriptions.Item>
            <Descriptions.Item label={t('auditLogs.status')}>
              <Tag color={selectedLog.status === 'success' ? 'green' : 'red'}>
                {selectedLog.status === 'success' ? t('auditLogs.statusSuccess') : t('auditLogs.statusFailure')}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('auditLogs.ipAddress')}>{selectedLog.ip_address || '-'}</Descriptions.Item>
            <Descriptions.Item label={t('auditLogs.date')}>{new Date(selectedLog.created_at).toLocaleString('ru-RU')}</Descriptions.Item>
            {selectedLog.error_message && (
              <Descriptions.Item label={t('auditLogs.error')} span={2}>
                <span style={{ color: 'red' }}>{selectedLog.error_message}</span>
              </Descriptions.Item>
            )}
            {selectedLog.details && (
              <Descriptions.Item label={t('auditLogs.detailsLabel')} span={2}>
                <pre style={{ maxHeight: '200px', overflow: 'auto' }}>
                  {JSON.stringify(selectedLog.details, null, 2)}
                </pre>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>

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
                  <div key={resourceType} style={{ display: 'flex', justifyContent: 'space-between' }}>
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
