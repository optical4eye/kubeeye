import React from 'react';
import { Table, Tag } from 'antd';

const NodeTable = ({ nodes, loading, scrollY = 400 }) => {
  const nodeColumns = [
    { title: 'NAME', dataIndex: 'name', key: 'name', ellipsis: true },
    {
      title: 'STATUS',
      dataIndex: 'status',
      key: 'status',
      render: status => {
        let className = 'status-not-ready';
        let ariaLabel = 'Статус: ';
        if (status === 'Ready') {
          className = 'status-ready';
          ariaLabel += 'Готов';
        } else if (status === 'NotReady') {
          className = 'status-not-ready';
          ariaLabel += 'Не готов';
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
      title: 'ROLES',
      dataIndex: 'roles',
      key: 'roles',
      responsive: ['md'],
      render: roles => roles?.join(', ') || 'N/A',
    },
    { title: 'AGE', dataIndex: 'age', key: 'age', responsive: ['lg'] },
    { title: 'VERSION', dataIndex: 'version', key: 'version', responsive: ['lg'] },
    { title: 'INTERNAL-IP', dataIndex: 'internal_ip', key: 'internal_ip', responsive: ['xl'] },
    { title: 'EXTERNAL-IP', dataIndex: 'external_ip', key: 'external_ip', responsive: ['xl'] },
    { title: 'OS-IMAGE', dataIndex: 'os_image', key: 'os_image', responsive: ['xl'] },
    {
      title: 'KERNEL-VERSION',
      dataIndex: 'kernel_version',
      key: 'kernel_version',
      responsive: ['xl'],
    },
    {
      title: 'CONTAINER-RUNTIME',
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
      pagination={false}
      scroll={{ y: scrollY }}
      virtual
      aria-label="Таблица узлов кластера"
    />
  );
};

export default NodeTable;
