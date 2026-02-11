import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useClusters } from '../hooks/useClusters';
import { useClusterForm } from '../hooks/useClusterForm';
import { ClusterList, ClusterModalManager } from '../components/cluster';
import { Form, Card } from 'antd';
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

  // Modal state management
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [detailsModalVisible, setDetailsModalVisible] = useState(false);

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
    setDetailsModalVisible(true);
  };

  const onEdit = (cluster: Cluster) => {
    setSelectedCluster(cluster);
    setEditModalVisible(true);
  };

  const onCloseEditModal = () => {
    setEditModalVisible(false);
    setSelectedCluster(null);
    editForm.resetFields();
  };

  const onCloseDetailsModal = () => {
    setDetailsModalVisible(false);
    setSelectedCluster(null);
    setClusterDetails(null);
    setClusterNodes([]);
    setNodeFilter('all');
  };

  const onEditSubmit = (values: any) => {
    handleEditCluster(values);
    setEditModalVisible(false);
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

      <Card>
        <ClusterList
          clusters={clusters}
          loading={loading}
          onViewDetails={onViewDetails}
          onEdit={onEdit}
          onDelete={handleDeleteCluster}
          onRefresh={loadClusters}
        />
      </Card>

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
