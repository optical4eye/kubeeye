import React, { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useClusters } from '../hooks/useClusters';
import { useClusterForm } from '../hooks/useClusterForm';
import { useClusterModals } from '../hooks/useClusterModals';
import { ClusterListContainer, ClusterModalManager } from '../components/cluster';
import { Form } from 'antd';
import { Cluster } from '../types/cluster';

const ClusterManagement = () => {
  const { t } = useTranslation();
  const {
    clusters,
    loading,
    selectedCluster,
    clusterDetails,
    nodesLoading,
    nodeFilter,
    setSelectedCluster,
    setClusterDetails,
    setClusterNodes,
    setNodeFilter,
    loadClusters,
    handleDeleteCluster,
    loadClusterDetails,
    handleEditCluster,
    loadClusterNodes,
    handleShowClusterDetails,
    filteredNodes,
  } = useClusters();

  const { handleTestNodes, handleTestKubeconfig, handleGetNodesFromKubeconfig } =
    useClusterForm(selectedCluster);

  const {
    editModalVisible,
    detailsModalVisible,
    openEditModal,
    closeEditModal,
    openDetailsModal,
    closeDetailsModal,
  } = useClusterModals();

  const [editForm] = Form.useForm();

  useEffect(() => {
    if (editModalVisible && selectedCluster) {
      loadClusterDetails(selectedCluster.name).then(formData => {
        editForm.setFieldsValue(formData);
      });
    }
  }, [editModalVisible, selectedCluster, editForm, loadClusterDetails]);

  const onViewDetails = (cluster: Cluster) => {
    handleShowClusterDetails(cluster);
    openDetailsModal();
  };

  const onEdit = (cluster: Cluster) => {
    setSelectedCluster(cluster);
    openEditModal();
  };

  const onCloseEditModal = () => {
    closeEditModal();
    setSelectedCluster(null);
    editForm.resetFields();
  };

  const onCloseDetailsModal = () => {
    closeDetailsModal();
    setSelectedCluster(null);
    setClusterDetails(null);
    setClusterNodes([]);
    setNodeFilter('all');
  };

  const onEditSubmit = (values: any) => {
    handleEditCluster(values);
    closeEditModal();
    setSelectedCluster(null);
    editForm.resetFields();
  };

  return (
    <div>
      <h1 className="page-title" aria-label={t('clusters.title')}>
        {t('clusters.title')}
      </h1>
      <p className="page-subtitle" aria-label={t('clusters.subtitle')}>
        {t('clusters.subtitle')}
      </p>

      <ClusterListContainer
        clusters={clusters}
        loading={loading}
        onViewDetails={onViewDetails}
        onEdit={onEdit}
        onDelete={handleDeleteCluster}
        onRefresh={loadClusters}
      />

      <ClusterModalManager
        editModalVisible={editModalVisible}
        detailsModalVisible={detailsModalVisible}
        selectedCluster={selectedCluster}
        clusterDetails={clusterDetails}
        filteredNodes={filteredNodes}
        nodesLoading={nodesLoading}
        nodeFilter={nodeFilter}
        editForm={editForm}
        onEditSubmit={onEditSubmit}
        onTestNodes={handleTestNodes}
        onTestKubeconfig={handleTestKubeconfig}
        onGetNodesFromKubeconfig={handleGetNodesFromKubeconfig}
        onCloseEditModal={onCloseEditModal}
        onCloseDetailsModal={onCloseDetailsModal}
        onRefreshNodes={() => selectedCluster && loadClusterNodes(selectedCluster.name)}
        onFilterChange={setNodeFilter}
      />
    </div>
  );
};

export default ClusterManagement;
