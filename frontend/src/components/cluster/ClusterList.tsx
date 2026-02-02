import React from 'react';
import { Table, Button, Space, Tag, App } from 'antd';
import { EyeOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const ClusterList = ({
  clusters,
  loading,
  onViewDetails,
  onEdit,
  onDelete,
  onRefresh: _onRefresh,
}) => {
  const { t } = useTranslation();
  const { modal } = App.useApp();
  const clusterColumns = [
    {
      title: t('clusters.clusterName'),
      dataIndex: 'name',
      key: 'name',
      width: 150,
      ellipsis: true,
    },
    {
      title: t('clusters.nodes'),
      dataIndex: 'nodes',
      key: 'nodes',
      width: 80,
      responsive: ['md'],
      render: nodes => nodes?.length || 0,
    },
    {
      title: t('clusters.k8sVersion'),
      dataIndex: 'k8s_version',
      key: 'k8s_version',
      width: 120,
      responsive: ['lg'],
      render: k8s_version =>
        k8s_version ? (
          <Tag color="success" aria-label={`Kubernetes version: ${k8s_version}`}>
            {k8s_version}
          </Tag>
        ) : (
          <Tag color="error" aria-label={t('clusters.notConfigured')}>
            {t('clusters.notConfigured')}
          </Tag>
        ),
    },
    {
      title: t('clusters.certExpiry'),
      dataIndex: 'cert_expiry_days',
      key: 'cert_expiry',
      width: 150,
      responsive: ['xl'],
      render: days => {
        if (days === null || days === undefined) {
          return (
            <Tag color="default" aria-label={t('clusters.unknown')}>
              {t('clusters.unknown')}
            </Tag>
          );
        }
        if (days < 0) {
          return (
            <Tag color="error" aria-label={t('clusters.expired')}>
              {t('clusters.expired')}
            </Tag>
          );
        }
        if (days <= 7) {
          return (
            <Tag
              color="error"
              aria-label={`${t('clusters.certExpiry')} ${days} ${t('clusters.days')}`}
            >
              {days} {t('clusters.days')}
            </Tag>
          );
        }
        if (days <= 30) {
          return (
            <Tag
              color="warning"
              aria-label={`${t('clusters.certExpiry')} ${days} ${t('clusters.days')}`}
            >
              {days} {t('clusters.days')}
            </Tag>
          );
        }
        return (
          <Tag
            color="success"
            aria-label={`${t('clusters.certExpiry')} ${days} ${t('clusters.days')}`}
          >
            {days} {t('clusters.days')}
          </Tag>
        );
      },
    },
    {
      title: t('clusters.actions'),
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space wrap>
          <Button
            className="action-button"
            icon={<EyeOutlined />}
            onClick={() => onViewDetails(record)}
            aria-label={`${t('clusters.details')} ${record.name}`}
          >
            {t('clusters.details')}
          </Button>
          <Button
            className="action-button"
            icon={<EditOutlined />}
            onClick={() => onEdit(record)}
            aria-label={`${t('clusters.edit')} ${record.name}`}
          >
            {t('clusters.edit')}
          </Button>
          <Button
            className="action-button"
            icon={<DeleteOutlined />}
            danger
            onClick={() =>
              modal.confirm({
                title: t('clusters.deleteConfirm'),
                description: t('clusters.deleteConfirmText', { name: record.name }),
                onOk: () => onDelete(record.name),
              })
            }
            aria-label={`${t('clusters.delete')} ${record.name}`}
          >
            {t('clusters.delete')}
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
