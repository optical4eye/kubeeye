export interface Cluster {
  name: string;
  nodes?: any[];
  kubeconfig?: string;
  k8s_version?: string;
  cert_expiry_days?: number;
}

export interface ClusterNode {
  status: string;
  [key: string]: any;
}

export interface ClusterFormValues {
  name: string;
  nodes_text: string;
  kubeconfig: string;
}
