import React from 'react';
import { Table, Button, Space, Tag, Modal } from 'antd';
import { EyeOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';

const ClusterList = ({
  clusters,
  loading,
  onViewDetails,
  onEdit,
  onDelete,
  onRefresh: _onRefresh,
}) => {
  const clusterColumns = [
    { title: 'Имя кластера', dataIndex: 'name', key: 'name', width: 150, ellipsis: true },
    {
      title: 'Узлы',
      dataIndex: 'nodes',
      key: 'nodes',
      width: 80,
      responsive: ['md'],
      render: nodes => nodes?.length || 0,
    },
    {
      title: 'Версия k8s',
      dataIndex: 'k8s_version',
      key: 'k8s_version',
      width: 120,
      responsive: ['lg'],
      render: k8s_version =>
        k8s_version ? (
          <Tag className="status-configured" aria-label={`Версия Kubernetes: ${k8s_version}`}>
            {k8s_version}
          </Tag>
        ) : (
          <Tag className="status-not-configured" aria-label="Версия Kubernetes не определена">
            Не настроен
          </Tag>
        ),
    },
    {
      title: 'Сертификат истекает через',
      dataIndex: 'cert_expiry_days',
      key: 'cert_expiry',
      width: 150,
      responsive: ['xl'],
      render: days => {
        if (days === null || days === undefined) {
          return (
            <Tag className="status-unknown" aria-label="Срок действия сертификата неизвестен">
              Неизвестно
            </Tag>
          );
        }
        if (days < 0) {
          return (
            <Tag className="status-expired" aria-label="Срок действия сертификата истек">
              Истек
            </Tag>
          );
        }
        if (days <= 7) {
          return (
            <Tag
              className="status-expired"
              aria-label={`Срок действия сертификата истекает через ${days} дней`}
            >
              {days} дней
            </Tag>
          );
        }
        if (days <= 30) {
          return (
            <Tag
              className="status-expires-soon"
              aria-label={`Срок действия сертификата истекает через ${days} дней`}
            >
              {days} дней
            </Tag>
          );
        }
        return (
          <Tag
            className="status-valid"
            aria-label={`Срок действия сертификата истекает через ${days} дней`}
          >
            {days} дней
          </Tag>
        );
      },
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space wrap>
          <Button
            className="action-button"
            icon={<EyeOutlined />}
            onClick={() => onViewDetails(record)}
            aria-label={`Просмотреть детали кластера ${record.name}`}
          >
            Детали
          </Button>
          <Button
            className="action-button"
            icon={<EditOutlined />}
            onClick={() => onEdit(record)}
            aria-label={`Редактировать кластер ${record.name}`}
          >
            Редактировать
          </Button>
          <Button
            className="action-button"
            icon={<DeleteOutlined />}
            danger
            onClick={() =>
              Modal.confirm({
                title: 'Удалить кластер?',
                content: `Вы уверены, что хотите удалить кластер ${record.name}?`,
                onOk: () => onDelete(record.name),
              })
            }
            aria-label={`Удалить кластер ${record.name}`}
          >
            Удалить
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <Table
      columns={clusterColumns}
      dataSource={clusters}
      loading={loading}
      rowKey="name"
      scroll={{ y: 600 }}
      virtual
    />
  );
};

export default ClusterList;
