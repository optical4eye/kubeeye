import React from 'react';
import {
  Modal,
  Button,
  Space,
  Select,
  Descriptions,
  Statistic,
  Row,
  Col,
  Typography,
  Card,
  Spin,
} from 'antd';
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation();
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
      title={t('clusters.clusterDetails', { name: cluster?.name })}
      open={open}
      onCancel={onClose}
      footer={null}
      width="90vw"
      className="modal-large"
      aria-label={t('clusters.clusterDetails', { name: cluster?.name })}
    >
      {cluster ? (
        <div>
          <Card title={t('clusters.clusterInfo')} className="margin-bottom-space-4">
            <Descriptions bordered column={2}>
              <Descriptions.Item label={t('clusters.clusterNameLabel')}>
                <Typography.Text>{cluster.name}</Typography.Text>
              </Descriptions.Item>
              <Descriptions.Item label={t('clusters.nodeCount')}>
                <Typography.Text>{cluster.nodes?.length || 0}</Typography.Text>
              </Descriptions.Item>
              <Descriptions.Item label={t('clusters.k8sVersion')}>
                <Typography.Text>
                  {cluster.k8s_version || t('clusters.notConfigured')}
                </Typography.Text>
              </Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title={t('clusters.nodeStats')} className="margin-bottom-space-4">
            <Row gutter={16}>
              <Col xs={24} sm={12} md={6}>
                <Statistic title={t('clusters.totalNodes')} value={nodeStats.total} />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title={t('clusters.ready')}
                  value={nodeStats.ready}
                  valueStyle={{ color: 'var(--ant-color-success)' }}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title={t('clusters.notReady')}
                  value={nodeStats.notready}
                  valueStyle={{ color: 'var(--ant-color-error)' }}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title={t('clusters.unknownStatus')}
                  value={nodeStats.unknown}
                  valueStyle={{ color: 'var(--ant-color-warning)' }}
                />
              </Col>
            </Row>
          </Card>

          <Card title={t('clusters.nodeManagement')}>
            <div style={{ marginBottom: '20px' }}>
              <Space wrap>
                <Button
                  onClick={onRefreshNodes}
                  loading={nodesLoading}
                  aria-label={t('clusters.refreshNodes')}
                >
                  {t('clusters.refreshNodes')}
                </Button>
                <Select
                  value={nodeFilter}
                  onChange={onFilterChange}
                  style={{ width: 150 }}
                  aria-label={t('clusters.filterByStatus')}
                  options={[
                    { value: 'all', label: t('clusters.allStatuses') },
                    { value: 'ready', label: t('clusters.ready') },
                    { value: 'notready', label: t('clusters.notReady') },
                    { value: 'unknown', label: t('clusters.unknownStatus') },
                  ]}
                />
              </Space>
            </div>

            {nodesLoading ? (
              <Spin size="large" />
            ) : (
              <NodeTable nodes={nodes} loading={false} aria-label={t('clusters.nodeManagement')} />
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
