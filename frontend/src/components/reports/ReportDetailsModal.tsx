import React from 'react';
import { useTranslation } from 'react-i18next';
import {
  Modal,
  Button,
  Descriptions,
  Row,
  Col,
  Tabs,
  Table,
  Tooltip,
  Spin,
  Typography,
  Card,
  Progress,
} from 'antd';
import {
  ExclamationCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { getStatusTag, getSeverityTag } from '../ui/statusUtils';

interface ReportDetail {
  result_id: string;
  cluster_name: string;
  timestamp: string;
  inspection_type: string;
  critical: number;
  warning: number;
  info: number;
  passed: number;
  inspection_results?: any;
  items?: any[];
}

interface ReportDetailsModalProps {
  open: boolean;
  onClose: () => void;
  reportDetail: ReportDetail | null;
  loading?: boolean;
}

const getInspectionItems = (reportDetail: ReportDetail) => {
  if (!reportDetail) return [];

  // Handle new data structure with inspection_results
  if (reportDetail.inspection_results) {
    const allItems: any[] = [];
    Object.values(reportDetail.inspection_results).forEach((inspectorResult: any) => {
      if (inspectorResult.items) {
        allItems.push(...inspectorResult.items);
      }
    });
    return allItems;
  }

  // Handle current data structure with direct items field
  if (reportDetail.items) {
    const allItems: any[] = [];

    reportDetail.items.forEach((item: any) => {
      // If item has results (node rules), flatten them
      if (item.results && Array.isArray(item.results)) {
        allItems.push(...item.results);
      } else {
        // Otherwise, add the item directly (OPA rules, SSH errors)
        allItems.push(item);
      }
    });

    return allItems;
  }

  return [];
};

const groupItemsBySeverity = (items: any[]) => {
  const groups: Record<string, any[]> = {
    critical: [],
    warning: [],
    other: [],
    passed: [],
  };

  items.forEach(item => {
    const severity = item.severity || 'info';
    const status = item.status || 'unknown';

    if (status === 'passed') {
      groups.passed.push(item);
    } else if (severity === 'critical') {
      groups.critical.push(item);
    } else if (severity === 'warning') {
      groups.warning.push(item);
    } else {
      groups.other.push(item);
    }
  });

  return groups;
};

const getSeverityIcon = (severity: string) => {
  switch (severity) {
    case 'critical':
      return <ExclamationCircleOutlined style={{ color: 'var(--ant-color-error)' }} />;
    case 'warning':
      return <WarningOutlined style={{ color: 'var(--ant-color-warning)' }} />;
    case 'other':
    case 'info':
      return <InfoCircleOutlined style={{ color: 'var(--ant-color-info)' }} />;
    case 'passed':
      return <CheckCircleOutlined style={{ color: 'var(--ant-color-success)' }} />;
    default:
      return <InfoCircleOutlined style={{ color: 'var(--ant-color-info)' }} />;
  }
};

const InspectionDetails: React.FC<{ items: any[]; severity?: string }> = React.memo(
  ({ items, severity }) => {
    const { t } = useTranslation();
    const [filteredItems, setFilteredItems] = React.useState(items);
    const [sortOrder, setSortOrder] = React.useState<'ascend' | 'descend' | null>(null);
    const [sortField, setSortField] = React.useState<string | null>(null);

    React.useEffect(() => {
      let filtered = items;

      if (sortField && sortOrder) {
        filtered = [...filtered].sort((a, b) => {
          const aVal = a[sortField] || '';
          const bVal = b[sortField] || '';
          if (sortOrder === 'ascend') {
            return aVal.localeCompare(bVal);
          } else {
            return bVal.localeCompare(aVal);
          }
        });
      }

      setFilteredItems(filtered);
    }, [items, sortField, sortOrder]);

    const handleTableChange = (pagination: any, filters: any, sorter: any) => {
      setSortField(sorter.field);
      setSortOrder(sorter.order);
    };

    const columns = [
      {
        title: t('reports.reportDetailsModal.table.checkName'),
        dataIndex: 'name',
        key: 'name',
        sorter: true,
        sortOrder: sortField === 'name' ? sortOrder : null,
      },
      {
        title: t('reports.status'),
        dataIndex: 'status',
        key: 'status',
        render: (status: string) => getStatusTag(status),
      },
      {
        title: t('reports.reportDetailsModal.table.severity'),
        dataIndex: 'severity',
        key: 'severity',
        render: (severity: string) => getSeverityTag(severity),
        sorter: true,
        sortOrder: sortField === 'severity' ? sortOrder : null,
      },
      {
        title: t('reports.reportDetailsModal.table.description'),
        dataIndex: 'description',
        key: 'description',
        ellipsis: {
          showTitle: false,
        },
        render: (text: string) => (
          <Tooltip title={text} styles={{ content: { maxWidth: '400px' } }}>
            <span style={{ cursor: 'pointer' }}>{text}</span>
          </Tooltip>
        ),
      },
      {
        title: t('reports.reportDetailsModal.table.details'),
        dataIndex: 'details',
        key: 'details',
        ellipsis: {
          showTitle: false,
        },
        render: (text: string) => (
          <Tooltip title={text} styles={{ content: { maxWidth: '400px' } }}>
            <span style={{ cursor: 'pointer' }}>{text}</span>
          </Tooltip>
        ),
      },
      {
        title: t('reports.reportDetailsModal.table.solution'),
        dataIndex: 'solution',
        key: 'solution',
        ellipsis: {
          showTitle: false,
        },
        render: (text: string) => (
          <Tooltip title={text} styles={{ content: { maxWidth: '400px' } }}>
            <span style={{ cursor: 'pointer' }}>{text}</span>
          </Tooltip>
        ),
      },
    ];

    return (
      <Table
        columns={columns}
        dataSource={filteredItems}
        rowKey={(record, index) => index || 0}
        pagination={{ pageSize: 20, showSizeChanger: true }}
        size="small"
        scroll={{ x: 'max-content' }}
        style={{ width: '100%' }}
        virtual={true}
        onChange={handleTableChange}
        aria-label={t('reports.reportDetailsModal.table.ariaLabel', {
          severity: severity || t('reports.reportDetailsModal.tabs.all'),
        })}
      />
    );
  }
);

InspectionDetails.displayName = 'InspectionDetails';

const ReportDetailsModal: React.FC<ReportDetailsModalProps> = React.memo(
  ({ open, onClose, reportDetail, loading = false }) => {
    const { t } = useTranslation();
    return (
      <Modal
        title={t('reports.reportDetailsModal.title')}
        open={open}
        onCancel={onClose}
        width="90vw"
        footer={[
          <Button
            key="close"
            onClick={onClose}
            aria-label={t('reports.reportDetailsModal.closeAriaLabel')}
          >
            {t('reports.reportDetailsModal.close')}
          </Button>,
        ]}
      >
        {loading ? (
          <Spin size="large" />
        ) : (
          reportDetail && (
            <div>
              <Descriptions bordered column={2}>
                <Descriptions.Item label={t('reports.reportDetailsModal.reportId')}>
                  <Typography.Text>{reportDetail.result_id}</Typography.Text>
                </Descriptions.Item>
                <Descriptions.Item label={t('reports.cluster')}>
                  <Typography.Text>{reportDetail.cluster_name}</Typography.Text>
                </Descriptions.Item>
                <Descriptions.Item label={t('reports.time')}>
                  <Typography.Text>
                    {new Date(reportDetail.timestamp).toLocaleString()}
                  </Typography.Text>
                </Descriptions.Item>
                <Descriptions.Item label={t('reports.type')}>
                  <Typography.Text>
                    {reportDetail.inspection_type === 'immediate'
                      ? t('reports.immediate')
                      : t('reports.scheduled')}
                  </Typography.Text>
                </Descriptions.Item>
              </Descriptions>

              <Card
                title={t('reports.reportDetailsModal.statistics')}
                className="margin-top-space-4"
              >
                {(() => {
                  const total =
                    (reportDetail.critical || 0) +
                    (reportDetail.warning || 0) +
                    (reportDetail.info || 0) +
                    (reportDetail.passed || 0);
                  return (
                    <Row gutter={16}>
                      <Col xs={24} sm={12} md={6}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <ExclamationCircleOutlined
                            style={{ color: 'var(--ant-color-error)', fontSize: '20px' }}
                          />
                          <div style={{ flex: 1 }}>
                            <div
                              style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                              }}
                            >
                              <span>{t('statistics.critical')}</span>
                              <span>{reportDetail.critical || 0}</span>
                            </div>
                            <Progress
                              percent={
                                total > 0
                                  ? Math.round(((reportDetail.critical || 0) / total) * 100)
                                  : 0
                              }
                              strokeColor="var(--ant-color-error)"
                              size="small"
                            />
                          </div>
                        </div>
                      </Col>
                      <Col xs={24} sm={12} md={6}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <WarningOutlined
                            style={{ color: 'var(--ant-color-warning)', fontSize: '20px' }}
                          />
                          <div style={{ flex: 1 }}>
                            <div
                              style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                              }}
                            >
                              <span>{t('statistics.warning')}</span>
                              <span>{reportDetail.warning || 0}</span>
                            </div>
                            <Progress
                              percent={
                                total > 0
                                  ? Math.round(((reportDetail.warning || 0) / total) * 100)
                                  : 0
                              }
                              strokeColor="var(--ant-color-warning)"
                              size="small"
                            />
                          </div>
                        </div>
                      </Col>
                      <Col xs={24} sm={12} md={6}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <InfoCircleOutlined
                            style={{ color: 'var(--ant-color-info)', fontSize: '20px' }}
                          />
                          <div style={{ flex: 1 }}>
                            <div
                              style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                              }}
                            >
                              <span>{t('statistics.info')}</span>
                              <span>{reportDetail.info || 0}</span>
                            </div>
                            <Progress
                              percent={
                                total > 0 ? Math.round(((reportDetail.info || 0) / total) * 100) : 0
                              }
                              strokeColor="var(--ant-color-info)"
                              size="small"
                            />
                          </div>
                        </div>
                      </Col>
                      <Col xs={24} sm={12} md={6}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <CheckCircleOutlined
                            style={{ color: 'var(--ant-color-success)', fontSize: '20px' }}
                          />
                          <div style={{ flex: 1 }}>
                            <div
                              style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                              }}
                            >
                              <span>{t('statistics.passed')}</span>
                              <span>{reportDetail.passed || 0}</span>
                            </div>
                            <Progress
                              percent={
                                total > 0
                                  ? Math.round(((reportDetail.passed || 0) / total) * 100)
                                  : 0
                              }
                              strokeColor="var(--ant-color-success)"
                              size="small"
                            />
                          </div>
                        </div>
                      </Col>
                    </Row>
                  );
                })()}
              </Card>

              <div className="margin-top-space-6">
                {(() => {
                  const allItems = getInspectionItems(reportDetail);
                  const groupedItems = groupItemsBySeverity(allItems);

                  const tabItems = [
                    {
                      key: 'all',
                      label: (
                        <span>
                          {t('reports.reportDetailsModal.tabs.all')}
                          <span style={{ marginLeft: '8px' }}>{allItems.length}</span>
                        </span>
                      ),
                      children: <InspectionDetails items={allItems} />,
                    },
                    {
                      key: 'critical',
                      label: (
                        <span>
                          {getSeverityIcon('critical')}
                          <span style={{ marginLeft: '8px' }}>{t('statistics.critical')}</span>
                          <span style={{ marginLeft: '8px' }}>{groupedItems.critical.length}</span>
                        </span>
                      ),
                      children: (
                        <InspectionDetails items={groupedItems.critical} severity="critical" />
                      ),
                    },
                    {
                      key: 'warning',
                      label: (
                        <span>
                          {getSeverityIcon('warning')}
                          <span style={{ marginLeft: '8px' }}>{t('statistics.warning')}</span>
                          <span style={{ marginLeft: '8px' }}>{groupedItems.warning.length}</span>
                        </span>
                      ),
                      children: (
                        <InspectionDetails items={groupedItems.warning} severity="warning" />
                      ),
                    },
                    {
                      key: 'other',
                      label: (
                        <span>
                          {getSeverityIcon('other')}
                          <span style={{ marginLeft: '8px' }}>{t('statistics.Info')}</span>
                          <span style={{ marginLeft: '8px' }}>{groupedItems.other.length}</span>
                        </span>
                      ),
                      children: <InspectionDetails items={groupedItems.other} severity="other" />,
                    },
                    {
                      key: 'passed',
                      label: (
                        <span>
                          {getSeverityIcon('passed')}
                          <span style={{ marginLeft: '8px' }}>{t('statistics.passed')}</span>
                          <span style={{ marginLeft: '8px' }}>{groupedItems.passed.length}</span>
                        </span>
                      ),
                      children: <InspectionDetails items={groupedItems.passed} severity="passed" />,
                    },
                  ];

                  return <Tabs defaultActiveKey="all" items={tabItems} />;
                })()}
              </div>
            </div>
          )
        )}
      </Modal>
    );
  }
);

ReportDetailsModal.displayName = 'ReportDetailsModal';

export default ReportDetailsModal;
