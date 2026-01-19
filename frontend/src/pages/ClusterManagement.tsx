import React, { useEffect } from 'react';
import { Tabs } from 'antd';
import { useClusters } from '../hooks/useClusters';
import { useClusterForm } from '../hooks/useClusterForm';
import { useClusterModals } from '../hooks/useClusterModals';
import ClusterListContainer from '../components/ClusterListContainer';
import ClusterFormContainer from '../components/ClusterFormContainer';
import ClusterModalManager from '../components/ClusterModalManager';
import { Form } from 'antd';
import { Cluster, ClusterFormValues } from '../types/cluster';

const ClusterManagement = () => {
  const {
    clusters,
    loading,
    selectedCluster,
    clusterDetails,
    clusterNodes,
    nodesLoading,
    nodeFilter,
    setSelectedCluster,
    setClusterDetails,
    setClusterNodes,
    setNodeFilter,
    loadClusters,
    handleCreateCluster,
    handleDeleteCluster,
    loadClusterDetails,
    handleEditCluster,
    loadClusterNodes,
    handleShowClusterDetails,
    filteredNodes,
  } = useClusters();

  const {
    handleTestNodes,
    handleTestKubeconfig,
    handleGetNodesFromKubeconfig,
  } = useClusterForm(selectedCluster);

  const {
    editModalVisible,
    detailsModalVisible,
    openEditModal,
    closeEditModal,
    openDetailsModal,
    closeDetailsModal,
  } = useClusterModals();

  const [editForm] = Form.useForm();
  const [createForm] = Form.useForm();

  useEffect(() => {
    if (editModalVisible && selectedCluster) {
      loadClusterDetails(selectedCluster.name).then((formData) => {
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

  const onCreateSubmit = (values: ClusterFormValues) => {
    handleCreateCluster(values);
    createForm.resetFields();
  };

  const onEditSubmit = (values: ClusterFormValues) => {
    handleEditCluster(values);
    closeEditModal();
    setSelectedCluster(null);
    editForm.resetFields();
  };

  return (
    <div>
      <h1 className="page-title" aria-label="Управление кластерами">
        Управление кластерами
      </h1>
      <p className="page-subtitle" aria-label="Настройка подключений к Kubernetes кластерам">
        Настройка подключений к Kubernetes кластерам
      </p>

      <Tabs
        defaultActiveKey="1"
        items={[
          {
            key: '1',
            label: 'Список кластеров',
            children: (
              <ClusterListContainer
                clusters={clusters}
                loading={loading}
                onViewDetails={onViewDetails}
                onEdit={onEdit}
                onDelete={handleDeleteCluster}
                onRefresh={loadClusters}
              />
            ),
          },
          {
            key: '2',
            label: 'Добавить кластер',
            children: (
              <ClusterFormContainer
                form={createForm}
                onSubmit={onCreateSubmit}
                onTestNodes={() => handleTestNodes(null, createForm)}
                onTestKubeconfig={() => handleTestKubeconfig(null, createForm)}
                onGetNodesFromKubeconfig={() => handleGetNodesFromKubeconfig(null, createForm)}
                isEditMode={false}
              />
            ),
          },
        ]}
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
