import React, { useState, useEffect } from 'react';
import { Card, Tabs, message, Modal, Form } from 'antd';
import {
  getClusters,
  createCluster,
  updateCluster,
  deleteCluster,
  getClusterDetails,
  getClusterNodes,
  testClusterNodes,
  testClusterKubeconfig,
  getNodesFromKubeconfig,
} from '../services/api';
import { parseNodesFromText, formatNodesForText } from '../utils/nodeParser';
import { fetchData } from '../utils/apiErrorHandler';
import ClusterList from '../components/ClusterList';
import ClusterForm from '../components/ClusterForm';
import ClusterDetailsModal from '../components/ClusterDetailsModal';

const ClusterManagement = () => {
  const [clusters, setClusters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [detailsModalVisible, setDetailsModalVisible] = useState(false);
  const [selectedCluster, setSelectedCluster] = useState(null);
  const [clusterDetails, setClusterDetails] = useState(null);
  const [clusterNodes, setClusterNodes] = useState([]);
  const [nodesLoading, setNodesLoading] = useState(false);
  const [nodeFilter, setNodeFilter] = useState('all');
  const [editForm] = Form.useForm();
  const [createForm] = Form.useForm();

  const loadClusters = async () => {
    try {
      setLoading(true);
      await fetchData(getClusters, 'Ошибка загрузки кластеров', data =>
        setClusters(data.clusters || [])
      );
    } catch (error) {
      message.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadClusters();
  }, []);

  const handleCreateCluster = async values => {
    try {
      const nodes = parseNodesFromText(values.nodes_text);
      const clusterData = {
        name: values.name,
        nodes: nodes,
        kubeconfig: values.kubeconfig,
      };

      await createCluster(clusterData);
      message.success('Кластер создан успешно');
      setCreateModalVisible(false);
      createForm.resetFields();
      loadClusters();
    } catch (error) {
      message.error('Ошибка создания кластера');
    }
  };

  const handleDeleteCluster = async clusterName => {
    try {
      await deleteCluster(clusterName);
      message.success('Кластер удален');
      loadClusters();
      setSelectedCluster(null);
      setClusterDetails(null);
      setClusterNodes([]);
    } catch (error) {
      message.error('Ошибка удаления кластера');
    }
  };

  const loadClusterDetails = async clusterName => {
    try {
      await fetchData(
        () => getClusterDetails(clusterName),
        'Ошибка загрузки данных кластера',
        data => {
          const formData = {
            name: data.name,
            nodes_text: formatNodesForText(data.nodes),
            kubeconfig: data.kubeconfig || '',
          };

          editForm.setFieldsValue(formData);
          setEditModalVisible(true);
        }
      );
    } catch (error) {
      message.error(error.message);
      setSelectedCluster(null);
    }
  };

  const handleEditCluster = async values => {
    try {
      const nodes = parseNodesFromText(values.nodes_text);
      const clusterData = {
        name: values.name,
        nodes: nodes,
        kubeconfig: values.kubeconfig,
      };

      await updateCluster(selectedCluster.name, clusterData);
      message.success('Кластер обновлен успешно');

      setEditModalVisible(false);
      setSelectedCluster(null);
      editForm.resetFields();
      loadClusters();
      if (clusterDetails) {
        loadClusterNodes(clusterDetails.name);
      }
    } catch (error) {
      message.error('Ошибка обновления кластера');
    }
  };

  const handleTestNodes = async () => {
    let nodesToTest = null;
    let clusterName = selectedCluster?.name;

    try {
      if (editModalVisible && editForm) {
        const formValues = editForm.getFieldsValue();
        nodesToTest = parseNodesFromText(formValues.nodes_text || '');
      } else if (createForm) {
        const formValues = createForm.getFieldsValue();
        nodesToTest = parseNodesFromText(formValues.nodes_text || '');
        clusterName = null;
      }

      const response = await testClusterNodes(clusterName, nodesToTest);
      const results = response.data.results;

      let successCount = 0;
      let failCount = 0;
      const failedNodes = [];

      results.forEach(result => {
        if (result.success) {
          successCount++;
        } else {
          failCount++;
          failedNodes.push(result.node_name || result.node);
        }
      });

      if (failCount > 0) {
        const failedList = failedNodes.join(', ');
        message.error(`Не удалось подключиться: ${failedList}`);
      } else if (results.length > 0) {
        message.success(`Все узлы доступны (${successCount} успешно)`);
      } else {
        message.warning('Не получено результатов тестирования');
      }
    } catch (error) {
      let errorMessage = 'Неизвестная ошибка';

      if (error.response?.data) {
        const data = error.response.data;
        if (typeof data === 'string') {
          errorMessage = data;
        } else if (data.detail) {
          if (typeof data.detail === 'string') {
            errorMessage = data.detail;
          } else if (typeof data.detail === 'object') {
            errorMessage = data.detail.message || data.detail.error || JSON.stringify(data.detail);
          } else {
            errorMessage = String(data.detail);
          }
        } else if (data.message) {
          errorMessage = data.message;
        } else if (data.error) {
          errorMessage = data.error;
        } else {
          errorMessage = JSON.stringify(data);
        }
      } else if (error.message) {
        errorMessage = error.message;
      }

      message.error(`Ошибка проверки узлов: ${errorMessage}`);
    }
  };

  const handleTestKubeconfig = async () => {
    try {
      let kubeconfigToTest = null;
      let clusterName = selectedCluster?.name;

      if (editModalVisible && editForm) {
        const formValues = editForm.getFieldsValue();
        kubeconfigToTest = formValues.kubeconfig;
      } else if (createForm) {
        const formValues = createForm.getFieldsValue();
        kubeconfigToTest = formValues.kubeconfig;
        clusterName = null;
      }

      const response = await testClusterKubeconfig(clusterName, kubeconfigToTest);
      const { success, message: testMessage } = response.data;

      if (success) {
        message.success(`Kubeconfig проверен: ${testMessage}`);
      } else {
        message.error(`Ошибка проверки kubeconfig: ${testMessage}`);
      }
    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.message || 'Неизвестная ошибка';
      message.error(`Ошибка проверки kubeconfig: ${errorMessage}`);
    }
  };

  const handleGetNodesFromKubeconfig = async () => {
    try {
      let kubeconfigToUse = null;

      if (editModalVisible && editForm) {
        const formValues = editForm.getFieldsValue();
        kubeconfigToUse = formValues.kubeconfig;
      } else if (createForm) {
        const formValues = createForm.getFieldsValue();
        kubeconfigToUse = formValues.kubeconfig;
      }

      if (!kubeconfigToUse) {
        message.error('Kubeconfig не указан');
        return;
      }

      const response = await getNodesFromKubeconfig(kubeconfigToUse);
      const nodesData = response.data;

      if (nodesData.status === 'success' && nodesData.nodes) {
        // Форматируем узлы для текстового поля
        const nodesText = nodesData.nodes
          .map(
            node =>
              `${node.internal_ip || node.external_ip || 'N/A'}:22 root password \${secret:ssh-password}`
          )
          .join('\n');

        // Обновляем поле nodes_text в форме
        if (editModalVisible && editForm) {
          editForm.setFieldsValue({ nodes_text: nodesText });
        } else if (createForm) {
          createForm.setFieldsValue({ nodes_text: nodesText });
        }

        message.success(`Получено ${nodesData.nodes.length} узлов из кластера`);
      } else {
        message.error('Ошибка получения узлов из кластера');
      }
    } catch (error) {
      const errorMessage =
        error.response?.data?.detail ||
        error.response?.data?.error ||
        error.message ||
        'Неизвестная ошибка';
      message.error(`Ошибка получения узлов: ${errorMessage}`);
    }
  };

  const loadClusterNodes = async clusterName => {
    try {
      setNodesLoading(true);
      const response = await getClusterNodes(clusterName);
      const nodesData = response.data;

      if (nodesData.status === 'success') {
        setClusterNodes(nodesData.nodes || []);
      } else {
        message.error('Ошибка получения узлов кластера');
        setClusterNodes([]);
      }
    } catch (error) {
      let errorMessage = 'Не удалось получить информацию об узлах кластера';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.response?.data?.error) {
        errorMessage = error.response.data.error;
      }

      message.error(errorMessage);
      setClusterNodes([]);
    } finally {
      setNodesLoading(false);
    }
  };

  const handleShowClusterDetails = cluster => {
    setSelectedCluster(cluster);
    setClusterDetails(cluster);
    setDetailsModalVisible(true);
    loadClusterNodes(cluster.name);
  };

  const filteredNodes = clusterNodes.filter(node => {
    if (nodeFilter === 'all') return true;
    return node.status.toLowerCase() === nodeFilter.toLowerCase();
  });

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
              <Card>
                <ClusterList
                  clusters={clusters}
                  loading={loading}
                  onViewDetails={handleShowClusterDetails}
                  onEdit={cluster => {
                    setSelectedCluster(cluster);
                    loadClusterDetails(cluster.name);
                  }}
                  onDelete={handleDeleteCluster}
                  onRefresh={() => {}}
                />
              </Card>
            ),
          },
          {
            key: '2',
            label: 'Добавить кластер',
            children: (
              <Card>
                <ClusterForm
                  form={createForm}
                  onSubmit={handleCreateCluster}
                  onTestNodes={handleTestNodes}
                  onTestKubeconfig={handleTestKubeconfig}
                  onGetNodesFromKubeconfig={handleGetNodesFromKubeconfig}
                  isEditMode={false}
                />
              </Card>
            ),
          },
        ]}
      />

      <Modal
        title="Создать кластер"
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        footer={null}
        className="modal-medium"
      >
        <ClusterForm
          form={createForm}
          onSubmit={handleCreateCluster}
          onTestNodes={handleTestNodes}
          onTestKubeconfig={handleTestKubeconfig}
          onGetNodesFromKubeconfig={handleGetNodesFromKubeconfig}
          isEditMode={false}
        />
      </Modal>

      <Modal
        title={`Редактировать кластер: ${selectedCluster?.name}`}
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false);
          setSelectedCluster(null);
          editForm.resetFields();
        }}
        footer={null}
        className="modal-medium"
      >
        <ClusterForm
          form={editForm}
          onSubmit={handleEditCluster}
          onTestNodes={handleTestNodes}
          onTestKubeconfig={handleTestKubeconfig}
          onGetNodesFromKubeconfig={handleGetNodesFromKubeconfig}
          isEditMode={true}
        />
      </Modal>

      <ClusterDetailsModal
        open={detailsModalVisible}
        cluster={clusterDetails}
        nodes={filteredNodes}
        nodesLoading={nodesLoading}
        nodeFilter={nodeFilter}
        onClose={() => {
          setDetailsModalVisible(false);
          setSelectedCluster(null);
          setClusterDetails(null);
          setClusterNodes([]);
          setNodeFilter('all');
        }}
        onRefreshNodes={() => loadClusterNodes(selectedCluster.name)}
        onFilterChange={setNodeFilter}
      />
    </div>
  );
};

export default ClusterManagement;
