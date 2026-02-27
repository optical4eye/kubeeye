import { useState, useCallback } from 'react';
import type { MessageInstance } from 'antd/es/message/interface';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getClusters,
  createCluster,
  updateCluster,
  deleteCluster,
  getClusterDetails,
  getClusterNodes,
} from '../services/api';
import { parseNodesFromText, formatNodesForText } from '../utils/nodeParser';
import { Cluster, ClusterNode, ClusterFormValues } from '../types/cluster';

interface UseClustersOptions {
  /** Message API instance from App.useApp() */
  messageApi?: MessageInstance;
}

export const useClusters = (options?: UseClustersOptions) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [selectedCluster, setSelectedCluster] = useState<Cluster | null>(null);
  const [clusterDetails, setClusterDetails] = useState<Cluster | null>(null);
  const [clusterNodes, setClusterNodes] = useState<ClusterNode[]>([]);
  const [nodesLoading, setNodesLoading] = useState(false);
  const [nodeFilter, setNodeFilter] = useState('all');

  // Query for clusters with 10 minutes staleTime
  const { data: clustersData, isLoading: loading } = useQuery({
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
      options?.messageApi?.success(t('clusters.nodeTable.messages.clusterCreated'));
      queryClient.invalidateQueries({ queryKey: ['clusters'] });
    },
    onError: () => {
      options?.messageApi?.error(t('clusters.nodeTable.messages.clusterCreateError'));
    },
  });

  const handleCreateCluster = useCallback(
    (values: ClusterFormValues) => {
      createClusterMutation.mutate(values);
    },
    [createClusterMutation]
  );

  // Mutation for deleting cluster
  const deleteClusterMutation = useMutation({
    mutationFn: deleteCluster,
    onSuccess: () => {
      options?.messageApi?.success(t('clusters.nodeTable.messages.clusterDeleted'));
      queryClient.invalidateQueries({ queryKey: ['clusters'] });
      setSelectedCluster(null);
      setClusterDetails(null);
      setClusterNodes([]);
    },
    onError: () => {
      options?.messageApi?.error(t('clusters.nodeTable.messages.clusterDeleteError'));
    },
  });

  const handleDeleteCluster = useCallback(
    (clusterName: string) => {
      deleteClusterMutation.mutate(clusterName);
    },
    [deleteClusterMutation]
  );

  const loadClusterDetails = useCallback(async (clusterName: string) => {
    try {
      const response = await getClusterDetails(clusterName);
      const data = response.data;
      // Возвращаем данные для формы
      return {
        name: data.name,
        nodes_text: formatNodesForText(data.nodes || []),
        kubeconfig: data.kubeconfig || '',
      };
    } catch (error: unknown) {
      options?.messageApi?.error(t('clusters.nodeTable.messages.clusterLoadError'));
      throw error;
    }
  }, []);

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
      options?.messageApi?.success(t('clusters.nodeTable.messages.clusterUpdated'));
      queryClient.invalidateQueries({ queryKey: ['clusters'] });
      setSelectedCluster(null);
      if (clusterDetails) {
        loadClusterNodes(clusterDetails.name);
      }
    },
    onError: () => {
      options?.messageApi?.error(t('clusters.nodeTable.messages.clusterUpdateError'));
    },
  });

  const handleEditCluster = useCallback(
    (values: ClusterFormValues) => {
      if (selectedCluster) {
        updateClusterMutation.mutate({ clusterName: selectedCluster.name, values });
      }
    },
    [selectedCluster, updateClusterMutation]
  );

  const loadClusterNodes = useCallback(async (clusterName: string) => {
    try {
      setNodesLoading(true);
      const response = await getClusterNodes(clusterName);
      const nodesData = response.data;

      if (nodesData.status === 'success') {
        setClusterNodes(nodesData.nodes || []);
      } else {
        options?.messageApi?.error(t('clusters.nodeTable.messages.clusterNodesError'));
        setClusterNodes([]);
      }
    } catch (error: unknown) {
      let errorMessage = t('clusters.nodeTable.messages.clusterNodesFailed');
      const err = error as any;
      if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      } else if (err.response?.data?.error) {
        errorMessage = err.response.data.error;
      }

      options?.messageApi?.error(errorMessage);
      setClusterNodes([]);
    } finally {
      setNodesLoading(false);
    }
  }, []);

  const handleShowClusterDetails = useCallback(
    (cluster: Cluster) => {
      setSelectedCluster(cluster);
      setClusterDetails(cluster);
      loadClusterNodes(cluster.name);
    },
    [loadClusterNodes]
  );

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
