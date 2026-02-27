import { useState, useEffect } from 'react';
import dayjs, { Dayjs } from 'dayjs';

export interface Filters {
  cluster: string;
  inspectionType: string;
  dateRange: [Dayjs | null, Dayjs | null] | null;
  search: string;
}

export const useReportsFilters = (reports: any[]) => {
  const [filteredReports, setFilteredReports] = useState<any[]>([]);
  const [filters, setFilters] = useState<Filters>({
    cluster: 'All',
    inspectionType: 'All',
    dateRange: null,
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

    // Фильтр по типу инспекции
    if (filters.inspectionType !== 'All') {
      filtered = filtered.filter(report => report.inspection_type === filters.inspectionType);
    }

    // Фильтр по диапазону дат
    if (filters.dateRange && filters.dateRange[0] && filters.dateRange[1]) {
      const [startDate, endDate] = filters.dateRange;
      filtered = filtered.filter(report => {
        const reportDate = dayjs(report.timestamp);
        return reportDate.isAfter(startDate, 'day') && reportDate.isBefore(endDate, 'day');
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
