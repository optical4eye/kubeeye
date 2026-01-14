import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UIState {
  theme: 'light' | 'dark';
  language: 'ru' | 'en';
  setTheme: (theme: 'light' | 'dark') => void;
  setLanguage: (language: 'ru' | 'en') => void;
}

export const useUIStore = create<UIState>()(
  persist(
    set => ({
      theme: 'dark',
      language: 'ru',
      setTheme: theme => set({ theme }),
      setLanguage: language => set({ language }),
    }),
    {
      name: 'ui-store',
      partialize: state => ({
        theme: state.theme,
        language: state.language,
      }),
    }
  )
);

// Cluster management store
interface ClusterState {
  selectedCluster: string | null;
  clusters: unknown[];
  loading: boolean;
  setSelectedCluster: (cluster: string | null) => void;
  setClusters: (clusters: unknown[]) => void;
  setLoading: (loading: boolean) => void;
  addCluster: (cluster: unknown) => void;
  updateCluster: (name: string, cluster: unknown) => void;
  removeCluster: (name: string) => void;
}

export const useClusterStore = create<ClusterState>(set => ({
  selectedCluster: null,
  clusters: [],
  loading: false,
  setSelectedCluster: selectedCluster => set({ selectedCluster }),
  setClusters: clusters => set({ clusters }),
  setLoading: loading => set({ loading }),
  addCluster: cluster => set(state => ({ clusters: [...state.clusters, cluster] })),
  updateCluster: (name, updatedCluster) =>
    set(state => ({
      clusters: state.clusters.map(c => (c.name === name ? { ...c, ...updatedCluster } : c)),
    })),
  removeCluster: name =>
    set(state => ({
      clusters: state.clusters.filter(c => c.name !== name),
    })),
}));
