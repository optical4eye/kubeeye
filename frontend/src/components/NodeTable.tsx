import React from 'react';
import { Table, Tag } from 'antd';

const NodeTable = ({ nodes, loading, scrollY = 400 }) => {
  const nodeColumns = [
    { title: 'NAME', dataIndex: 'name', key: 'name' },
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
      render: roles => roles?.join(', ') || 'N/A',
    },
    { title: 'AGE', dataIndex: 'age', key: 'age' },
    { title: 'VERSION', dataIndex: 'version', key: 'version' },
    { title: 'INTERNAL-IP', dataIndex: 'internal_ip', key: 'internal_ip' },
    { title: 'EXTERNAL-IP', dataIndex: 'external_ip', key: 'external_ip' },
    { title: 'OS-IMAGE', dataIndex: 'os_image', key: 'os_image' },
    { title: 'KERNEL-VERSION', dataIndex: 'kernel_version', key: 'kernel_version' },
    { title: 'CONTAINER-RUNTIME', dataIndex: 'container_runtime', key: 'container_runtime' },
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
