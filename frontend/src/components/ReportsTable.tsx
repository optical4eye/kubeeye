import React from 'react';
import { Card, Table, Button, Space, Modal } from 'antd';
import { DownloadOutlined, DeleteOutlined, EyeOutlined } from '@ant-design/icons';
import { getStatusTag } from './statusUtils';

interface Report {
  result_id: string;
  cluster_name: string;
  timestamp: string;
  inspection_type: string;
  status: string;
  critical: number;
  warning: number;
  info: number;
  passed: number;
}

interface ReportsTableProps {
  filteredReports: Report[];
  loading: boolean;
  onView: (reportId: string) => void;
  onDelete: (reportId: string) => void;
  onExport: (reportId: string, format: string) => void;
}

const ReportsTable: React.FC<ReportsTableProps> = React.memo(({
  filteredReports,
  loading,
  onView,
  onDelete,
  onExport,
}) => {
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
      render: (_: any, record: Report) => getStatusTag(record.status),
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
      render: (_: any, record: Report) => (
        <Space wrap>
          <Button
            icon={<EyeOutlined />}
            onClick={() => onView(record.result_id)}
            aria-label="Просмотр отчета"
          >
            Просмотр
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => onExport(record.result_id, 'json')}
            disabled={record.inspection_type === 'popeye'}
            aria-label="Экспорт отчета в JSON"
          >
            JSON
          </Button>
          {record.inspection_type === 'popeye' && (
            <Button
              icon={<DownloadOutlined />}
              onClick={() => onExport(record.result_id, 'html')}
              aria-label="Экспорт отчета в HTML"
            >
              HTML
            </Button>
          )}
          {record.inspection_type !== 'popeye' && (
            <Button
              icon={<DownloadOutlined />}
              onClick={() => onExport(record.result_id, 'pdf')}
              disabled={record.inspection_type === 'network'}
              aria-label="Экспорт отчета в PDF"
            >
              PDF
            </Button>
          )}
          <Button
            icon={<DeleteOutlined />}
            danger
            onClick={() =>
              Modal.confirm({
                title: 'Удалить отчет?',
                content: 'Это действие нельзя отменить',
                onOk: () => onDelete(record.result_id),
              })
            }
            aria-label="Удалить отчет"
          >
            Удалить
          </Button>
        </Space>
      ),
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
});

ReportsTable.displayName = 'ReportsTable';

export default ReportsTable;