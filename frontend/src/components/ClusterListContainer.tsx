import React from 'react';
import { Card } from 'antd';
import ClusterList from './ClusterList';
import { Cluster } from '../types/cluster';

interface ClusterListContainerProps {
  clusters: Cluster[];
  loading: boolean;
  onViewDetails: (cluster: Cluster) => void;
  onEdit: (cluster: Cluster) => void;
  onDelete: (clusterName: string) => void;
  onRefresh: () => void;
}

const ClusterListContainer: React.FC<ClusterListContainerProps> = React.memo(({
  clusters,
  loading,
  onViewDetails,
  onEdit,
  onDelete,
  onRefresh,
}) => {
  return (
    <Card>
      <ClusterList
        clusters={clusters}
        loading={loading}
        onViewDetails={onViewDetails}
        onEdit={onEdit}
        onDelete={onDelete}
        onRefresh={onRefresh}
      />
    </Card>
  );
});

ClusterListContainer.displayName = 'ClusterListContainer';

export default ClusterListContainer;