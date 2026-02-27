import React from 'react';
import { Card, Table, Button, Dropdown, Tooltip, Popconfirm } from 'antd';
import { DownloadOutlined, DeleteOutlined, EyeOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { getStatusTag, getSeverityBadge } from '../ui/statusUtils';
import { Report } from '../../types';
import { formatDate } from '../../utils/dateFormat';

interface ReportsTableProps {
  filteredReports: Report[];
  loading: boolean;
  onView: (reportId: string) => void;
  onDelete: (reportId: string) => void;
  onExport: (reportId: string, format: string) => void;
  onSelectionChange: (selectedRows: Report[]) => void;
}

const ReportsTable: React.FC<ReportsTableProps> = React.memo(
  ({ filteredReports, loading, onView, onDelete, onExport, onSelectionChange }) => {
    const { t } = useTranslation();
    const columns = [
      {
        title: t('reports.id'),
        dataIndex: 'result_id',
        key: 'result_id',
        width: 200,
      },
      {
        title: t('reports.cluster'),
        dataIndex: 'cluster_name',
        key: 'cluster_name',
      },
      {
        title: t('reports.time'),
        dataIndex: 'timestamp',
        key: 'timestamp',
        render: (timestamp: string) => formatDate(timestamp),
      },
      {
        title: t('reports.type'),
        dataIndex: 'inspection_type',
        key: 'inspection_type',
      },
      {
        title: t('reports.status'),
        key: 'status',
        render: (_: unknown, record: Report) => getStatusTag(record.status || ''),
      },
      {
        title: t('reports.critical'),
        dataIndex: 'critical',
        key: 'critical',
        render: (value: number) => getSeverityBadge(value || 0, 'critical'),
      },
      {
        title: t('reports.warning'),
        dataIndex: 'warning',
        key: 'warning',
        render: (value: number) => getSeverityBadge(value || 0, 'warning'),
      },
      {
        title: t('reports.other'),
        dataIndex: 'info',
        key: 'info',
        render: (value: number) => getSeverityBadge(value || 0, 'other'),
      },
      {
        title: t('reports.successful'),
        dataIndex: 'passed',
        key: 'passed',
        render: (value: number) => getSeverityBadge(value || 0, 'passed'),
      },
      {
        title: t('reports.actions'),
        key: 'actions',
        render: (_: unknown, record: Report) => {
          return (
            <Button.Group>
              <Tooltip title={t('reports.viewReport')}>
                <Button icon={<EyeOutlined />} onClick={() => onView(record.result_id)} />
              </Tooltip>
              <Tooltip title={t('reports.exportReport')}>
                <Dropdown
                  menu={{
                    items: (() => {
                      const exportItems = [];
                      if (record.inspection_type === 'popeye') {
                        exportItems.push({
                          key: 'export-html',
                          label: t('reports.html'),
                          onClick: () => onExport(record.result_id, 'html'),
                        });
                      } else if (record.inspection_type === 'network') {
                        exportItems.push({
                          key: 'export-json',
                          label: t('reports.json'),
                          onClick: () => onExport(record.result_id, 'json'),
                        });
                      } else {
                        // cluster
                        exportItems.push(
                          {
                            key: 'export-json',
                            label: t('reports.json'),
                            onClick: () => onExport(record.result_id, 'json'),
                          },
                          {
                            key: 'export-pdf',
                            label: t('reports.pdf'),
                            onClick: () => onExport(record.result_id, 'pdf'),
                          }
                        );
                      }
                      return exportItems;
                    })(),
                  }}
                  trigger={['click']}
                  placement="bottomRight"
                >
                  <Button icon={<DownloadOutlined />} />
                </Dropdown>
              </Tooltip>
              <Popconfirm
                title={t('reports.deleteConfirm')}
                description={t('reports.deleteDescription')}
                onConfirm={() => onDelete(record.result_id)}
                okText={t('reports.yes')}
                cancelText={t('reports.no')}
              >
                <Tooltip title={t('reports.deleteReport')}>
                  <Button icon={<DeleteOutlined />} danger />
                </Tooltip>
              </Popconfirm>
            </Button.Group>
          );
        },
      },
    ];

    return (
      <Card>
        <Table
          columns={columns}
          dataSource={filteredReports}
          loading={loading}
          rowKey="result_id"
          pagination={{ pageSize: 10 }}
          scroll={{ y: 400 }}
          virtual={true}
          aria-label={t('reports.reportsTableAria')}
          rowSelection={{
            onChange: (_, selectedRows) => onSelectionChange(selectedRows),
          }}
        />
      </Card>
    );
  }
);

ReportsTable.displayName = 'ReportsTable';

export default ReportsTable;
