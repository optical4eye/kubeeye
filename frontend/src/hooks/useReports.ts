import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getReports, deleteReport } from '../services/api';

export const useReports = () => {
  const queryClient = useQueryClient();

  // Query for reports with 5 minutes staleTime
  const {
    data: reportsData,
    isLoading: loading,
    error: reportsError,
  } = useQuery({
    queryKey: ['reports'],
    queryFn: async () => {
      const response = await getReports();
      return response.data.reports || [];
    },
    staleTime: 5 * 60 * 1000, // 5 minutes for reports
  });

  const reports = reportsData || [];

  // Mutation for deleting report
  const deleteReportMutation = useMutation({
    mutationFn: deleteReport,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
  });

  const handleDeleteReport = (reportId: string) => {
    deleteReportMutation.mutate(reportId);
  };

  return {
    reports,
    loading,
    error: reportsError,
    handleDeleteReport,
  };
};
