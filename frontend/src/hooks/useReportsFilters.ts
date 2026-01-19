import { useState, useEffect } from 'react';

export interface Filters {
  cluster: string;
  period: string;
  search: string;
}

export const useReportsFilters = (reports: any[]) => {
  const [filteredReports, setFilteredReports] = useState<any[]>([]);
  const [filters, setFilters] = useState<Filters>({
    cluster: 'All',
    period: 'All',
    search: '',
  });

  useEffect(() => {
    applyFilters();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reports, filters]);

  const applyFilters = () => {
    let filtered = [...reports];

    // Фильтр по кластеру
    if (filters.cluster !== 'All') {
      filtered = filtered.filter(report => report.cluster_name === filters.cluster);
    }

    // Фильтр по периоду
    const now = new Date();
    if (filters.period !== 'All') {
      const cutoffDate = new Date();
      if (filters.period === 'Today') {
        cutoffDate.setHours(0, 0, 0, 0);
      } else if (filters.period === 'Last 7 days') {
        cutoffDate.setDate(now.getDate() - 7);
      } else if (filters.period === 'Last 30 days') {
        cutoffDate.setDate(now.getDate() - 30);
      }

      filtered = filtered.filter(report => {
        const reportDate = new Date(report.timestamp);
        return reportDate >= cutoffDate;
      });
    }

    // Поиск по имени
    if (filters.search) {
      filtered = filtered.filter(
        report =>
          report.cluster_name.toLowerCase().includes(filters.search.toLowerCase()) ||
          report.result_id.toLowerCase().includes(filters.search.toLowerCase())
      );
    }

    setFilteredReports(filtered);
  };

  return { filteredReports, filters, setFilters };
};