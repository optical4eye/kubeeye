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
    { title: 'Имя кластера', dataIndex: 'name', key: 'name', width: 150 },
    {
      title: 'Узлы',
      dataIndex: 'nodes',
      key: 'nodes',
      width: 80,
      render: nodes => nodes?.length || 0,
    },
    {
      title: 'Kubeconfig',
      dataIndex: 'kubeconfig',
      key: 'kubeconfig',
      width: 120,
      render: kubeconfig =>
        kubeconfig ? (
          <Tag className="status-configured" aria-label="Kubeconfig настроен">
            Настроен
          </Tag>
        ) : (
          <Tag className="status-not-configured" aria-label="Kubeconfig не настроен">
            Не настроен
          </Tag>
        ),
    },
    {
      title: 'Сертификат истекает через',
      dataIndex: 'cert_expiry_days',
      key: 'cert_expiry',
      width: 150,
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
        <Space>
          <Button
            icon={<EyeOutlined />}
            onClick={() => onViewDetails(record)}
            aria-label={`Просмотреть детали кластера ${record.name}`}
          >
            Детали
          </Button>
          <Button
            icon={<EditOutlined />}
            onClick={() => onEdit(record)}
            aria-label={`Редактировать кластер ${record.name}`}
          >
            Редактировать
          </Button>
          <Button
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
