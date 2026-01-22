import React from 'react';
import { Table, Tag } from 'antd';
import { useTranslation } from 'react-i18next';

const NodeTable = ({ nodes, loading, scrollY = 400 }) => {
  const { t } = useTranslation();
  const nodeColumns = [
    { title: t('clusters.nodeTable.name'), dataIndex: 'name', key: 'name', ellipsis: true },
    {
      title: t('clusters.nodeTable.status'),
      dataIndex: 'status',
      key: 'status',
      render: status => {
        let className = 'status-not-ready';
        let ariaLabel = t('clusters.nodeTable.status') + ': ';
        if (status === 'Ready') {
          className = 'status-ready';
          ariaLabel += t('clusters.nodeTable.ready');
        } else if (status === 'NotReady') {
          className = 'status-not-ready';
          ariaLabel += t('clusters.nodeTable.notReady');
        } else {
          ariaLabel += status;
        }
        return (
          <Tag className={className} aria-label={ariaLabel}>
            {status}
          </Tag>
        );
      },
    },
    {
      title: t('clusters.nodeTable.roles'),
      dataIndex: 'roles',
      key: 'roles',
      responsive: ['md'],
      render: roles => roles?.join(', ') || t('clusters.nodeTable.na'),
    },
    { title: t('clusters.nodeTable.age'), dataIndex: 'age', key: 'age', responsive: ['lg'] },
    {
      title: t('clusters.nodeTable.version'),
      dataIndex: 'version',
      key: 'version',
      responsive: ['lg'],
    },
    {
      title: t('clusters.nodeTable.internalIp'),
      dataIndex: 'internal_ip',
      key: 'internal_ip',
      responsive: ['xl'],
    },
    {
      title: t('clusters.nodeTable.externalIp'),
      dataIndex: 'external_ip',
      key: 'external_ip',
      responsive: ['xl'],
    },
    {
      title: t('clusters.nodeTable.osImage'),
      dataIndex: 'os_image',
      key: 'os_image',
      responsive: ['xl'],
    },
    {
      title: t('clusters.nodeTable.kernelVersion'),
      dataIndex: 'kernel_version',
      key: 'kernel_version',
      responsive: ['xl'],
    },
    {
      title: t('clusters.nodeTable.containerRuntime'),
      dataIndex: 'container_runtime',
      key: 'container_runtime',
      responsive: ['xl'],
    },
  ];

  return (
    <Table
      columns={nodeColumns}
      dataSource={nodes}
      loading={loading}
      rowKey="name"
      pagination={{
        pageSize: 10,
        showSizeChanger: true,
        showTotal: (total, range) => `${range[0]}-${range[1]} из ${total}`,
      }}
      scroll={{ y: scrollY, x: 'max-content' }}
      virtual
      aria-label="Таблица узлов кластера"
    />
  );
};

export default NodeTable;
