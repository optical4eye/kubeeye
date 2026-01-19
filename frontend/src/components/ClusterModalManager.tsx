import React from 'react';
import { Modal } from 'antd';
import ClusterForm from './ClusterForm';
import ClusterDetailsModal from './ClusterDetailsModal';
import { Cluster, ClusterFormValues, ClusterNode } from '../types/cluster';

interface ClusterModalManagerProps {
  editModalVisible: boolean;
  detailsModalVisible: boolean;
  selectedCluster: Cluster | null;
  clusterDetails: Cluster | null;
  filteredNodes: ClusterNode[];
  nodesLoading: boolean;
  nodeFilter: string;
  editForm: any;
  onEditSubmit: (values: ClusterFormValues) => void;
  onTestNodes: (editForm: any, createForm: any) => void;
  onTestKubeconfig: (editForm: any, createForm: any) => void;
  onGetNodesFromKubeconfig: (editForm: any, createForm: any) => void;
  onCloseEditModal: () => void;
  onCloseDetailsModal: () => void;
  onRefreshNodes: () => void;
  onFilterChange: (filter: string) => void;
}

const ClusterModalManager: React.FC<ClusterModalManagerProps> = React.memo(({
  editModalVisible,
  detailsModalVisible,
  selectedCluster,
  clusterDetails,
  filteredNodes,
  nodesLoading,
  nodeFilter,
  editForm,
  onEditSubmit,
  onTestNodes,
  onTestKubeconfig,
  onGetNodesFromKubeconfig,
  onCloseEditModal,
  onCloseDetailsModal,
  onRefreshNodes,
  onFilterChange,
}) => {
  return (
    <>
      <Modal
        title={`Редактировать кластер: ${selectedCluster?.name}`}
        open={editModalVisible}
        onCancel={onCloseEditModal}
        footer={null}
        className="modal-medium"
      >
        <ClusterForm
          form={editForm}
          onSubmit={onEditSubmit}
          onTestNodes={() => onTestNodes(editForm, null)}
          onTestKubeconfig={() => onTestKubeconfig(editForm, null)}
          onGetNodesFromKubeconfig={() => onGetNodesFromKubeconfig(editForm, null)}
          isEditMode={true}
        />
      </Modal>

      <ClusterDetailsModal
        open={detailsModalVisible}
        cluster={clusterDetails}
        nodes={filteredNodes}
        nodesLoading={nodesLoading}
        nodeFilter={nodeFilter}
        onClose={onCloseDetailsModal}
        onRefreshNodes={onRefreshNodes}
        onFilterChange={onFilterChange}
      />
    </>
  );
});

ClusterModalManager.displayName = 'ClusterModalManager';

export default ClusterModalManager;