import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getRules, syncGitopsRepository } from '../services/api';

export const useRules = () => {
  const queryClient = useQueryClient();

  // Query for rules with 30 minutes staleTime
  const {
    data: rulesData,
    isLoading: loading,
    error: rulesError,
  } = useQuery({
    queryKey: ['rules'],
    queryFn: async () => {
      const response = await getRules();
      return response.data;
    },
    staleTime: 30 * 60 * 1000, // 30 minutes for rules
    refetchOnWindowFocus: false, // Rarely changing data
  });

  const rules = rulesData?.rules || {};
  const useGitops = rulesData?.use_gitops || false;

  // Mutation for syncing GitOps repository
  const syncGitopsMutation = useMutation({
    mutationFn: syncGitopsRepository,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] });
    },
  });

  const syncGitopsRepositoryHandler = () => {
    syncGitopsMutation.mutate();
  };

  return {
    rules,
    useGitops,
    loading,
    error: rulesError,
    syncGitopsRepository: syncGitopsRepositoryHandler,
    syncing: syncGitopsMutation.isPending,
  };
};