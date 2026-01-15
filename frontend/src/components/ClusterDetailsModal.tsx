import React from 'react';
import { Modal, Button, Space, Select } from 'antd';
import NodeTable from './NodeTable';

const ClusterDetailsModal = ({
  open,
  cluster,
  nodes,
  nodesLoading,
  nodeFilter,
  onClose,
  onRefreshNodes,
  onFilterChange,
}) => {
  return (
    <Modal
      title={`Детали кластера: ${cluster?.name}`}
      open={open}
      onCancel={onClose}
      footer={null}
      width={1200}
      className="modal-large"
      aria-label={`Детали кластера: ${cluster?.name}`}
    >
      {cluster && (
        <div>
          <div style={{ marginBottom: '20px' }}>
            <h3 aria-label={`Кластер: ${cluster.name}`}>Кластер: {cluster.name}</h3>
            <p aria-label={`Узлов: ${cluster.nodes?.length || 0}`}>
              Узлов: {cluster.nodes?.length || 0}
            </p>
            <p aria-label={`Kubeconfig: ${cluster.kubeconfig ? 'Настроен' : 'Не настроен'}`}>
              Kubeconfig: {cluster.kubeconfig ? 'Настроен' : 'Не настроен'}
            </p>
          </div>

          <div style={{ marginBottom: '20px' }}>
            <Space wrap>
              <Button onClick={onRefreshNodes} loading={nodesLoading} aria-label="Обновить узлы">
                Обновить узлы
              </Button>
              <Select
                value={nodeFilter}
                onChange={onFilterChange}
                style={{ width: 150 }}
                aria-label="Фильтр узлов по статусу"
                options={[
                  { value: 'all', label: 'Все статусы' },
                  { value: 'ready', label: 'Ready' },
                  { value: 'notready', label: 'NotReady' },
                  { value: 'unknown', label: 'Unknown' },
                ]}
              />
            </Space>
          </div>

          <NodeTable nodes={nodes} loading={nodesLoading} aria-label="Таблица узлов кластера" />
        </div>
      )}
    </Modal>
  );
};

export default ClusterDetailsModal;
