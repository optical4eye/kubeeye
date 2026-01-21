import React from 'react';
import { Card, Table, Button, Dropdown, Tooltip, Popconfirm } from 'antd';
import { DownloadOutlined, DeleteOutlined, EyeOutlined } from '@ant-design/icons';
import { getStatusTag } from '../ui/statusUtils';
import { Report } from '../../types';

interface ReportsTableProps {
  filteredReports: Report[];
  loading: boolean;
  onView: (reportId: string) => void;
  onDelete: (reportId: string) => void;
  onExport: (reportId: string, format: string) => void;
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
        title: 'Критические',
        dataIndex: 'critical',
        key: 'critical',
        render: (value: number) => value || 0,
      },
      {
        title: 'Предупреждения',
        dataIndex: 'warning',
        key: 'warning',
        render: (value: number) => value || 0,
      },
      {
        title: 'Другие',
        dataIndex: 'info',
        key: 'info',
        render: (value: number) => value || 0,
      },
      {
        title: 'Успешно',
        dataIndex: 'passed',
        key: 'passed',
        render: (value: number) => value || 0,
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
                    items: [
                      {
                        key: 'export-json',
                        label: 'JSON',
                        onClick: () => onExport(record.result_id, 'json'),
                        disabled: record.inspection_type === 'popeye',
                      },
                      ...(record.inspection_type === 'popeye'
                        ? [
                            {
                              key: 'export-html',
                              label: 'HTML',
                              onClick: () => onExport(record.result_id, 'html'),
                            },
                          ]
                        : [
                            {
                              key: 'export-pdf',
                              label: 'PDF',
                              onClick: () => onExport(record.result_id, 'pdf'),
                              disabled: record.inspection_type === 'network',
                            },
                          ]),
                    ],
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
        />
      </Card>
    );
  }
);

ReportsTable.displayName = 'ReportsTable';

export default ReportsTable;
