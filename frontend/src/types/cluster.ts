export interface Cluster {
  name: string;
  nodes?: any[];
  kubeconfig?: string;
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