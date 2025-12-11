import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000, // Reasonable timeout for async operations (15 seconds)
});

// Remove /api prefix if API_BASE_URL already includes it
const shouldPrefixApi = !API_BASE_URL.includes('/api');

// Helper function to build API paths
const apiPath = (path) => shouldPrefixApi ? `/api${path}` : path;

// Dashboard
export const getDashboardData = () => api.get(apiPath('/dashboard'));

// Clusters
export const getClusters = () => api.get(apiPath('/clusters'));
export const createCluster = (clusterData) => api.post(apiPath('/clusters'), clusterData);
export const updateCluster = (clusterName, clusterData) => api.put(apiPath(`/clusters/${clusterName}`), clusterData);
export const deleteCluster = (clusterName) => api.delete(apiPath(`/clusters/${clusterName}`));
export const getClusterDetails = (clusterName) => api.get(apiPath(`/clusters/${clusterName}`));
export const testClusterNodes = (clusterName, nodes = null) => {
  // Use extended timeout for node testing
  const testApi = axios.create({
    ...api.defaults,
    timeout: 30000, // 30 seconds for node testing
  });

  if (nodes === null) {
    return testApi.post(apiPath(`/clusters/${clusterName}/test-nodes`));
  } else {
    return testApi.post(apiPath(`/clusters/${clusterName}/test-nodes`), { nodes });
  }
};

export const testClusterKubeconfig = (clusterName, kubeconfig = null) => {
  if (kubeconfig === null) {
    return api.post(apiPath(`/clusters/${clusterName}/test-kubeconfig`));
  } else {
    return api.post(apiPath(`/clusters/${clusterName}/test-kubeconfig`), { kubeconfig });
  }
};

// Inspections
export const runInspection = (inspectionData) => api.post(apiPath('/inspection'), inspectionData);

// Async inspections
export const runInspectionAsync = (inspectionData) => api.post(apiPath('/inspection/async'), inspectionData);
export const getInspectionTaskStatus = (taskId) => api.get(apiPath(`/inspection/task/${taskId}`));
export const cancelInspectionTask = (taskId) => api.delete(apiPath(`/inspection/task/${taskId}`));

// Queue management
export const getQueueStatus = () => api.get(apiPath('/queue/status'));
export const getQueueTasks = (limit = 50) => api.get(apiPath(`/queue/tasks?limit=${limit}`));

// Health check
export const getHealthStatus = () => api.get(apiPath('/health'));

// Reports
export const getReports = (limit = 100) => api.get(apiPath(`/reports?limit=${limit}`));
export const getReport = (reportId) => api.get(apiPath(`/reports/${reportId}`));
export const deleteReport = (reportId) => api.delete(apiPath(`/reports/${reportId}`));
export const exportReport = (reportId, format) => api.get(apiPath(`/reports/${reportId}/export/${format}`), {
  responseType: 'blob'
});

// Rules
// GitOps
export const getGitopsConfig = () => api.get(apiPath('/gitops/config'));
export const syncGitopsRepository = () => api.post(apiPath('/gitops/sync'));
export const getRules = () => api.get(apiPath('/rules'));

// Scheduled tasks
export const getScheduledTasks = () => api.get(apiPath('/scheduled-tasks'));
export const createScheduledTask = (taskData) => api.post(apiPath('/scheduled-tasks'), taskData);
export const updateScheduledTask = (taskId, taskData) => api.put(apiPath(`/scheduled-tasks/${taskId}`), taskData);
export const deleteScheduledTask = (taskId) => api.delete(apiPath(`/scheduled-tasks/${taskId}`));
export const runScheduledTask = (taskId) => api.post(apiPath(`/scheduled-tasks/${taskId}/run`));

// Cleanup config
export const getCleanupConfig = () => api.get(apiPath('/cleanup-config'));

// Network connectivity
export const checkNetworkConnectivity = (checkData) => api.post(apiPath('/network-check'), checkData);
export const getClustersForNetworkCheck = () => api.get(apiPath('/network-check/clusters'));
export const getNetworkCheckResults = (clusterName = null, limit = 50) => {
  const params = new URLSearchParams();
  if (clusterName) params.append('cluster_name', clusterName);
  params.append('limit', limit);
  return api.get(apiPath(`/network-check/results?${params.toString()}`));
};
export const getNetworkCheckResult = (resultId) => api.get(apiPath(`/network-check/results/${resultId}`));
export const deleteNetworkCheckResult = (resultId) => api.delete(apiPath(`/network-check/results/${resultId}`));
export const exportNetworkCheckResult = (resultId, format) => api.get(apiPath(`/network-check/results/${resultId}/export/${format}`), {
  responseType: 'blob'
});

export default api;