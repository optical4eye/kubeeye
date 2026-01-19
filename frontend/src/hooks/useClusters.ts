import { useState } from 'react';
import { message } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getClusters,
  createCluster,
  updateCluster,
  deleteCluster,
  getClusterDetails,
  getClusterNodes,
} from '../services/api';
import { parseNodesFromText } from '../utils/nodeParser';
import { Cluster, ClusterNode, ClusterFormValues } from '../types/cluster';

export const useClusters = () => {
  const queryClient = useQueryClient();
  const [selectedCluster, setSelectedCluster] = useState<Cluster | null>(null);
  const [clusterDetails, setClusterDetails] = useState<Cluster | null>(null);
  const [clusterNodes, setClusterNodes] = useState<ClusterNode[]>([]);
  const [nodesLoading, setNodesLoading] = useState(false);
  const [nodeFilter, setNodeFilter] = useState('all');

  // Query for clusters with 10 minutes staleTime
  const {
    data: clustersData,
    isLoading: loading,
    error: clustersError,
  } = useQuery({
    queryKey: ['clusters'],
    queryFn: async () => {
      const response = await getClusters();
      return response.data.clusters || [];
    },
    staleTime: 10 * 60 * 1000, // 10 minutes for clusters
    refetchOnWindowFocus: false, // Rarely changing data
  });

  const clusters = clustersData || [];

  // Mutation for creating cluster
  const createClusterMutation = useMutation({
    mutationFn: async (values: ClusterFormValues) => {
      const nodes = parseNodesFromText(values.nodes_text);
      const clusterData = {
        name: values.name,
        nodes: nodes,
        kubeconfig: values.kubeconfig,
      };
      return createCluster(clusterData);
    },
    onSuccess: () => {
      message.success('Кластер создан успешно');
      queryClient.invalidateQueries({ queryKey: ['clusters'] });
    },
    onError: () => {
      message.error('Ошибка создания кластера');
    },
  });

  const handleCreateCluster = (values: ClusterFormValues) => {
    createClusterMutation.mutate(values);
  };

  // Mutation for deleting cluster
  const deleteClusterMutation = useMutation({
    mutationFn: deleteCluster,
    onSuccess: () => {
      message.success('Кластер удален');
      queryClient.invalidateQueries({ queryKey: ['clusters'] });
      setSelectedCluster(null);
      setClusterDetails(null);
      setClusterNodes([]);
    },
    onError: () => {
      message.error('Ошибка удаления кластера');
    },
  });

  const handleDeleteCluster = (clusterName: string) => {
    deleteClusterMutation.mutate(clusterName);
  };

  const loadClusterDetails = async (clusterName: string) => {
    try {
      const response = await getClusterDetails(clusterName);
      const data = response.data;
      setSelectedCluster({ name: clusterName } as Cluster);
      // Возвращаем данные для формы
      return {
        name: data.name,
        nodes_text: data.nodes,
        kubeconfig: data.kubeconfig || '',
      };
    } catch (error: unknown) {
      message.error('Ошибка загрузки данных кластера');
      setSelectedCluster(null);
      throw error;
    }
  };

  // Mutation for updating cluster
  const updateClusterMutation = useMutation({
    mutationFn: async ({
      clusterName,
      values,
    }: {
      clusterName: string;
      values: ClusterFormValues;
    }) => {
      const nodes = parseNodesFromText(values.nodes_text);
      const clusterData = {
        name: values.name,
        nodes: nodes,
        kubeconfig: values.kubeconfig,
      };
      return updateCluster(clusterName, clusterData);
    },
    onSuccess: () => {
      message.success('Кластер обновлен успешно');
      queryClient.invalidateQueries({ queryKey: ['clusters'] });
      setSelectedCluster(null);
      if (clusterDetails) {
        loadClusterNodes(clusterDetails.name);
      }
    },
    onError: () => {
      message.error('Ошибка обновления кластера');
    },
  });

  const handleEditCluster = (values: ClusterFormValues) => {
    if (selectedCluster) {
      updateClusterMutation.mutate({ clusterName: selectedCluster.name, values });
    }
  };

  const loadClusterNodes = async (clusterName: string) => {
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
    } catch (error: unknown) {
      let errorMessage = 'Не удалось получить информацию об узлах кластера';
      const err = error as any;
      if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      } else if (err.response?.data?.error) {
        errorMessage = err.response.data.error;
      }

      message.error(errorMessage);
      setClusterNodes([]);
    } finally {
      setNodesLoading(false);
    }
  };

  const handleShowClusterDetails = (cluster: Cluster) => {
    setSelectedCluster(cluster);
    setClusterDetails(cluster);
    loadClusterNodes(cluster.name);
  };

  const filteredNodes = clusterNodes.filter(node => {
    if (nodeFilter === 'all') return true;
    return node.status.toLowerCase() === nodeFilter.toLowerCase();
  });

  return {
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
    handleCreateCluster,
    handleDeleteCluster,
    loadClusterDetails,
    handleEditCluster,
    loadClusterNodes,
    handleShowClusterDetails,
    filteredNodes,
  };
};
