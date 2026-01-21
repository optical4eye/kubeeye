import React from 'react';
import { Card, Table, Button, Dropdown, Tooltip, Popconfirm } from 'antd';
import { DownloadOutlined, DeleteOutlined, EyeOutlined } from '@ant-design/icons';
import { getStatusTag, getSeverityBadge } from '../ui/statusUtils';
import { Report } from '../../types';

interface ReportsTableProps {
  filteredReports: Report[];
  loading: boolean;
  onView: (reportId: string) => void;
  onDelete: (reportId: string) => void;
  onExport: (reportId: string, format: string) => void;
  onSelectionChange: (selectedRows: Report[]) => void;
}

const ReportsTable: React.FC<ReportsTableProps> = React.memo(
  ({ filteredReports, loading, onView, onDelete, onExport }) => {
    const columns = [
      {
        title: 'ID',
        dataIndex: 'result_id',
        key: 'result_id',
        width: 200,
      },
      {
        title: 'Кластер',
        dataIndex: 'cluster_name',
        key: 'cluster_name',
      },
      {
        title: 'Время',
        dataIndex: 'timestamp',
        key: 'timestamp',
        render: (timestamp: string) => new Date(timestamp).toLocaleString(),
      },
      {
        title: 'Тип',
        dataIndex: 'inspection_type',
        key: 'inspection_type',
        render: (type: string) => (type === 'immediate' ? 'Немедленная' : 'Запланированная'),
      },
      {
        title: 'Статус',
        key: 'status',
        render: (_: unknown, record: Report) => getStatusTag(record.status),
      },
      {
        title: 'Critical',
        dataIndex: 'critical',
        key: 'critical',
        render: (value: number) => getSeverityBadge(value || 0, 'critical'),
      },
      {
        title: 'Warning',
        dataIndex: 'warning',
        key: 'warning',
        render: (value: number) => getSeverityBadge(value || 0, 'warning'),
      },
      {
        title: 'Other',
        dataIndex: 'info',
        key: 'info',
        render: (value: number) => getSeverityBadge(value || 0, 'other'),
      },
      {
        title: 'Successful',
        dataIndex: 'passed',
        key: 'passed',
        render: (value: number) => getSeverityBadge(value || 0, 'passed'),
      },
      {
        title: 'Действия',
        key: 'actions',
        render: (_: unknown, record: Report) => {
          return (
            <Button.Group>
              <Tooltip title="Просмотр отчета">
                <Button icon={<EyeOutlined />} onClick={() => onView(record.result_id)} />
              </Tooltip>
              <Tooltip title="Экспорт отчета">
                <Dropdown
                  menu={{
                    items: (() => {
                      const exportItems = [];
                      if (record.inspection_type === 'popeye') {
                        exportItems.push({
                          key: 'export-html',
                          label: 'HTML',
                          onClick: () => onExport(record.result_id, 'html'),
                        });
                      } else if (record.inspection_type === 'network') {
                        exportItems.push({
                          key: 'export-json',
                          label: 'JSON',
                          onClick: () => onExport(record.result_id, 'json'),
                        });
                      } else {
                        // cluster
                        exportItems.push(
                          {
                            key: 'export-json',
                            label: 'JSON',
                            onClick: () => onExport(record.result_id, 'json'),
                          },
                          {
                            key: 'export-pdf',
                            label: 'PDF',
                            onClick: () => onExport(record.result_id, 'pdf'),
                          },
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
                title="Удалить отчет?"
                description="Это действие нельзя отменить"
                onConfirm={() => onDelete(record.result_id)}
                okText="Да"
                cancelText="Нет"
              >
                <Tooltip title="Удалить отчет">
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
          aria-label="Таблица отчетов инспекций"
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
