import React from 'react';
import { Modal, Button, Descriptions, Statistic, Row, Col, Tabs, Table, Tooltip } from 'antd';
import { getStatusTag, getSeverityTag } from './statusUtils';

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
  visible: boolean;
  onClose: () => void;
  reportDetail: ReportDetail | null;
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

const InspectionDetails: React.FC<{ items: any[] }> = React.memo(({ items }) => {
  const columns = [
    {
      title: 'Название проверки',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => getStatusTag(status),
    },
    {
      title: 'Уровень серьезности',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity: string) => getSeverityTag(severity),
    },
    {
      title: 'Описание',
      dataIndex: 'description',
      key: 'description',
      ellipsis: {
        showTitle: false,
      },
      render: (text: string) => (
        <Tooltip title={text} overlayStyle={{ maxWidth: '400px' }}>
          <span style={{ cursor: 'pointer' }}>{text}</span>
        </Tooltip>
      ),
    },
    {
      title: 'Детали',
      dataIndex: 'details',
      key: 'details',
      ellipsis: {
        showTitle: false,
      },
      render: (text: string) => (
        <Tooltip title={text} overlayStyle={{ maxWidth: '400px' }}>
          <span style={{ cursor: 'pointer' }}>{text}</span>
        </Tooltip>
      ),
    },
    {
      title: 'Решение',
      dataIndex: 'solution',
      key: 'solution',
      ellipsis: {
        showTitle: false,
      },
      render: (text: string) => (
        <Tooltip title={text} overlayStyle={{ maxWidth: '400px' }}>
          <span style={{ cursor: 'pointer' }}>{text}</span>
        </Tooltip>
      ),
    },
  ];

  return (
    <Table
      columns={columns}
      dataSource={items}
      rowKey={(record, index) => index || 0}
      pagination={{ pageSize: 20 }}
      size="small"
      scroll={{ x: 'max-content' }}
      style={{ width: '100%' }}
      virtual={true}
      aria-label="Таблица деталей результатов инспекции"
    />
  );
});

InspectionDetails.displayName = 'InspectionDetails';

const ReportDetailsModal: React.FC<ReportDetailsModalProps> = React.memo(
  ({ visible, onClose, reportDetail }) => {
    return (
      <Modal
        title="Детали отчета"
        open={visible}
        onCancel={onClose}
        width={2500}
        footer={[
          <Button key="close" onClick={onClose} aria-label="Закрыть детали отчета">
            Закрыть
          </Button>,
        ]}
      >
        {reportDetail && (
          <div>
            <Descriptions bordered column={2}>
              <Descriptions.Item label="ID отчета">{reportDetail.result_id}</Descriptions.Item>
              <Descriptions.Item label="Кластер">{reportDetail.cluster_name}</Descriptions.Item>
              <Descriptions.Item label="Время">
                {new Date(reportDetail.timestamp).toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="Тип инспекции">
                {reportDetail.inspection_type === 'immediate' ? 'Немедленная' : 'Запланированная'}
              </Descriptions.Item>
            </Descriptions>

            <Row gutter={16} className="margin-top-space-4">
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Критические"
                  value={reportDetail.critical || 0}
                  valueStyle={{ color: 'var(--ant-color-error)' }}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Предупреждения"
                  value={reportDetail.warning || 0}
                  valueStyle={{ color: 'var(--ant-color-warning)' }}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Другие ошибки"
                  value={reportDetail.info || 0}
                  valueStyle={{ color: 'var(--ant-color-info)' }}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Успешно"
                  value={reportDetail.passed || 0}
                  valueStyle={{ color: 'var(--ant-color-success)' }}
                />
              </Col>
            </Row>

            <div className="margin-top-space-6">
              <Tabs
                defaultActiveKey="details"
                items={[
                  {
                    key: 'details',
                    label: 'Детали результатов инспекции',
                    children: <InspectionDetails items={getInspectionItems(reportDetail)} />,
                  },
                ]}
              />
            </div>
          </div>
        )}
      </Modal>
    );
  }
);

ReportDetailsModal.displayName = 'ReportDetailsModal';

export default ReportDetailsModal;
