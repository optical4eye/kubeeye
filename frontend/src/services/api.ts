import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { tokenStorage } from '../utils/tokenStorage';

const baseConfig = {
  baseURL: '',
  timeout: 15000, // Reasonable timeout for async operations (15 seconds)
};

const api = axios.create(baseConfig);

// Request interceptor - add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = tokenStorage.getAccessToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - handle 401 errors
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    // If error is 401, clear token
    if (error.response?.status === 401) {
      tokenStorage.clearTokens();
      // Redirect to login page will be handled by ProtectedRoute
    }
    return Promise.reject(error);
  }
);

// Factory function to create axios instances with different timeouts
const createApiWithTimeout = (timeout: number) => {
  const instance = axios.create({ ...baseConfig, timeout });

  // Add request interceptor to include auth token
  instance.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      const token = tokenStorage.getAccessToken();
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // Add response interceptor to handle 401 errors
  instance.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      if (error.response?.status === 401) {
        tokenStorage.clearTokens();
      }
      return Promise.reject(error);
    }
  );

  return instance;
};

// Helper function to build API paths
const apiPath = path => `/api${path}`;

// Dashboard
export const getDashboardData = () => {
  // Use shorter timeout for dashboard to avoid long waits on unavailable clusters
  const dashboardApi = createApiWithTimeout(10000);
  return dashboardApi.get(apiPath('/dashboard'));
};

// Clusters
export const getClusters = () => {
  // Use shorter timeout for cluster list to avoid long waits on unavailable clusters
  const clustersApi = createApiWithTimeout(10000);
  return clustersApi.get(apiPath('/clusters'));
};
export const createCluster = clusterData => api.post(apiPath('/clusters'), clusterData);
export const updateCluster = (clusterName, clusterData) =>
  api.put(apiPath(`/clusters/${clusterName}`), clusterData);
export const deleteCluster = clusterName => api.delete(apiPath(`/clusters/${clusterName}`));
export const getClusterDetails = clusterName => api.get(apiPath(`/clusters/${clusterName}`));
export const getClusterNodes = clusterName => api.get(apiPath(`/clusters/${clusterName}/nodes`));
export const testClusterNodes = (clusterName, nodes = null) => {
  // Use extended timeout for node testing
  const testApi = createApiWithTimeout(30000);

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

export const getNodesFromKubeconfig = kubeconfig =>
  api.post(apiPath('/clusters/get-nodes-from-kubeconfig'), { kubeconfig });

// Inspections
export const runInspection = inspectionData => api.post(apiPath('/inspection'), inspectionData);

// Async inspections
export const runInspectionAsync = inspectionData => {
  // Use extended timeout for async inspections
  const inspectionApi = createApiWithTimeout(30000);

  return inspectionApi.post(apiPath('/inspection/async'), inspectionData);
};
export const getInspectionTaskStatus = taskId => api.get(apiPath(`/inspection/task/${taskId}`));
export const cancelInspectionTask = taskId => api.delete(apiPath(`/inspection/task/${taskId}`));

// Queue management
export const getQueueStatus = () => api.get(apiPath('/queue/status'));
export const getQueueTasks = (limit = 50) => api.get(apiPath(`/queue/tasks?limit=${limit}`));

// Health check
export const getHealthStatus = () => {
  // Use shorter timeout for health checks
  const healthApi = createApiWithTimeout(5000);
  return healthApi.get(apiPath('/health'));
};

// Reports
export const getReports = (limit = 100) => api.get(apiPath(`/reports?limit=${limit}`));
export const getReport = reportId => api.get(apiPath(`/reports/${reportId}`));
export const deleteReport = reportId => api.delete(apiPath(`/reports/${reportId}`));
export const exportReport = (reportId, format) =>
  api.get(apiPath(`/reports/${reportId}/export/${format}`), {
    responseType: 'blob',
  });
export const createImmediateReport = () => api.post(apiPath('/reports/immediate'));

// Rules
// GitOps
export const getGitopsConfig = () => api.get(apiPath('/gitops/config'));
export const syncGitopsRepository = () => api.post(apiPath('/gitops/sync'));
export const getRules = (tags: string[] | null = null) => {
  const params = new URLSearchParams();
  if (tags && tags.length > 0) {
    params.append('tags', tags.join(','));
  }
  const queryString = params.toString();
  return api.get(apiPath(`/rules${queryString ? `?${queryString}` : ''}`));
};
export const getRuleTags = () => api.get(apiPath('/rules/tags'));

// Scheduled tasks
export const getScheduledTasks = () => api.get(apiPath('/scheduled-tasks'));
export const createScheduledTask = taskData => api.post(apiPath('/scheduled-tasks'), taskData);
export const updateScheduledTask = (taskId, taskData) =>
  api.put(apiPath(`/scheduled-tasks/${taskId}`), taskData);
export const deleteScheduledTask = taskId => api.delete(apiPath(`/scheduled-tasks/${taskId}`));
export const runScheduledTask = taskId => api.post(apiPath(`/scheduled-tasks/${taskId}/run`));

// Cleanup config
export const getCleanupConfig = () => api.get(apiPath('/cleanup/config'));

// Network connectivity
export const checkNetworkConnectivity = checkData => api.post(apiPath('/network-check'), checkData);
export const getClustersForNetworkCheck = () => api.get(apiPath('/network-check/clusters'));
export const getNetworkCheckResults = (clusterName = null, limit = 50) => {
  const params = new URLSearchParams();
  if (clusterName) params.append('cluster_name', clusterName);
  params.append('limit', limit);
  return api.get(apiPath(`/network-check/results?${params.toString()}`));
};
export const getNetworkCheckResult = resultId =>
  api.get(apiPath(`/network-check/results/${resultId}`));
export const deleteNetworkCheckResult = resultId =>
  api.delete(apiPath(`/network-check/results/${resultId}`));
export const exportNetworkCheckResult = (resultId, format) =>
  api.get(apiPath(`/network-check/results/${resultId}/export/${format}`), {
    responseType: 'blob',
  });

// Popeye scanning
export const startPopeyeScan = scanData => {
  // Use extended timeout for Popeye scans
  const popeyeApi = createApiWithTimeout(30000);

  return popeyeApi.post(apiPath('/popeye/scan'), scanData);
};
export const getPopeyeNamespaces = clusterName =>
  api.get(apiPath(`/popeye/namespaces/${clusterName}`));
export const getPopeyeTaskStatus = taskId => api.get(apiPath(`/popeye/task/${taskId}`));
export const cancelPopeyeTask = taskId => api.delete(apiPath(`/popeye/task/${taskId}`));

export default api;
