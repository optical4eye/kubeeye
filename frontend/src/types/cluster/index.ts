// Типы для кластеров

export interface Cluster {
  id?: number;
  name: string;
  nodes: Node[];
  kubeconfig?: string;
  password_secret_id?: number;
  ssh_key_secret_id?: number;
  kubeconfig_secret_id?: number;
  last_inspection?: string;
  status: 'healthy' | 'warning' | 'critical' | 'unknown';
  created_at?: string;
  updated_at?: string;
}

export interface Node {
  ip: string;
  port: number;
  user: string;
  auth_type: 'password' | 'key';
  password?: string;
  ssh_key?: string;
  status?: string;
  [key: string]: any; // Для дополнительных полей
}

export interface ClusterFormData {
  name: string;
  nodes_text: string;
  kubeconfig?: string;
}

export interface ClusterCreateRequest {
  name: string;
  nodes: Record<string, any>[];
  kubeconfig?: string;
}

export interface NodesTestRequest {
  nodes: Record<string, any>[];
}

export interface KubeconfigTestRequest {
  kubeconfig: string;
}

export interface GetNodesFromKubeconfigRequest {
  kubeconfig: string;
}
