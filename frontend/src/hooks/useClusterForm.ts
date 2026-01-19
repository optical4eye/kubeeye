import { useCallback } from 'react';
import { message } from 'antd';
import { testClusterNodes, testClusterKubeconfig, getNodesFromKubeconfig } from '../services/api';
import { parseNodesFromText } from '../utils/nodeParser';
import { Cluster } from '../types/cluster';

export const useClusterForm = (selectedCluster: Cluster | null) => {
  const handleTestNodes = async (editForm: any, createForm: any) => {
    let nodesToTest = null;
    let clusterName = selectedCluster?.name;

    try {
      if (editForm) {
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
    } catch (error: unknown) {
      let errorMessage = 'Неизвестная ошибка';
      const err = error as any;
      if (err.response?.data) {
        const data = err.response.data;
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
      } else if (err.message) {
        errorMessage = err.message;
      }
      message.error(`Ошибка проверки узлов: ${errorMessage}`);
    }
  };

  const handleTestKubeconfig = async (editForm: any, createForm: any) => {
    try {
      let kubeconfigToTest = null;
      let clusterName = selectedCluster?.name;

      if (editForm) {
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
    } catch (error: unknown) {
      const errorMessage =
        (error as any).response?.data?.detail || (error as Error).message || 'Неизвестная ошибка';
      message.error(`Ошибка проверки kubeconfig: ${errorMessage}`);
    }
  };

  const handleGetNodesFromKubeconfig = async (editForm: any, createForm: any) => {
    try {
      let kubeconfigToUse = null;

      if (editForm) {
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
        if (editForm) {
          editForm.setFieldsValue({ nodes_text: nodesText });
        } else if (createForm) {
          createForm.setFieldsValue({ nodes_text: nodesText });
        }

        message.success(`Получено ${nodesData.nodes.length} узлов из кластера`);
      } else {
        message.error('Ошибка получения узлов из кластера');
      }
    } catch (error: unknown) {
      const errorMessage =
        (error as any).response?.data?.detail ||
        (error as any).response?.data?.error ||
        (error as Error).message ||
        'Неизвестная ошибка';
      message.error(`Ошибка получения узлов: ${errorMessage}`);
    }
  };

  return {
    handleTestNodes,
    handleTestKubeconfig,
    handleGetNodesFromKubeconfig,
  };
};
