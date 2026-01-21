import React from 'react';
import { Modal, Button, Space, Select, Descriptions, Statistic, Row, Col, Typography, Card, Spin } from 'antd';
import NodeTable from './NodeTable';
import { Cluster, ClusterNode } from '../../types';

interface ClusterDetailsModalProps {
  open: boolean;
  cluster: Cluster | null;
  nodes: ClusterNode[];
  nodesLoading: boolean;
  nodeFilter: string;
  onClose: () => void;
  onRefreshNodes: () => void;
  onFilterChange: (value: string) => void;
}

const ClusterDetailsModal: React.FC<ClusterDetailsModalProps> = ({
  open,
  cluster,
  nodes,
  nodesLoading,
  nodeFilter,
  onClose,
  onRefreshNodes,
  onFilterChange,
}) => {
  // Calculate node statistics
  const nodeStats = React.useMemo(() => {
    const stats = { ready: 0, notready: 0, unknown: 0, total: nodes.length };
    nodes.forEach(node => {
      const status = node.status?.toLowerCase();
      if (status === 'ready') stats.ready++;
      else if (status === 'notready') stats.notready++;
      else stats.unknown++;
    });
    return stats;
  }, [nodes]);

  return (
    <Modal
      title={`Детали кластера: ${cluster?.name}`}
      open={open}
      onCancel={onClose}
      footer={null}
      width="90vw"
      className="modal-large"
      aria-label={`Детали кластера: ${cluster?.name}`}
    >
      {cluster ? (
        <div>
          <Card title="Информация о кластере" className="margin-bottom-space-4">
            <Descriptions bordered column={2}>
              <Descriptions.Item label="Название кластера">
                <Typography.Text>{cluster.name}</Typography.Text>
              </Descriptions.Item>
              <Descriptions.Item label="Количество узлов">
                <Typography.Text>{cluster.nodes?.length || 0}</Typography.Text>
              </Descriptions.Item>
              <Descriptions.Item label="Версия k8s">
                <Typography.Text>{cluster.k8s_version || 'Не настроен'}</Typography.Text>
              </Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title="Статистика узлов" className="margin-bottom-space-4">
            <Row gutter={16}>
              <Col xs={24} sm={12} md={6}>
                <Statistic title="Всего узлов" value={nodeStats.total} />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Ready"
                  value={nodeStats.ready}
                  valueStyle={{ color: 'var(--ant-color-success)' }}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="NotReady"
                  value={nodeStats.notready}
                  valueStyle={{ color: 'var(--ant-color-error)' }}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Unknown"
                  value={nodeStats.unknown}
                  valueStyle={{ color: 'var(--ant-color-warning)' }}
                />
              </Col>
            </Row>
          </Card>

          <Card title="Управление узлами">
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

            {nodesLoading ? (
              <Spin size="large" />
            ) : (
              <NodeTable nodes={nodes} loading={false} aria-label="Таблица узлов кластера" />
            )}
          </Card>
        </div>
      ) : (
        <Spin size="large" />
      )}
    </Modal>
  );
};

export default ClusterDetailsModal;
