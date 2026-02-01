import React from 'react';
import { Card, Select, Input, Space } from 'antd';
import { DatePicker } from 'antd';
import { useTranslation } from 'react-i18next';
import { Filters } from '../hooks/useReportsFilters';

interface ReportsFiltersProps {
  clusters: string[];
  filters: Filters;
  setFilters: React.Dispatch<React.SetStateAction<Filters>>;
}

const ReportsFilters: React.FC<ReportsFiltersProps> = React.memo(
  ({ clusters, filters, setFilters }) => {
    const { t } = useTranslation();

    return (
      <Card className="margin-bottom-space-4">
        <Space wrap>
          <Select
            placeholder={t('reports.filters.clusterPlaceholder')}
            className="width-200"
            onChange={value => setFilters(prev => ({ ...prev, cluster: value }))}
            value={filters.cluster}
            options={[
              { value: 'All', label: t('reports.filters.allClusters') },
              ...clusters.map(cluster => ({ value: cluster, label: cluster })),
            ]}
          />

          <Select
            placeholder={t('reports.filters.inspectionTypePlaceholder')}
            className="width-150"
            onChange={value => setFilters(prev => ({ ...prev, inspectionType: value }))}
            value={filters.inspectionType}
            options={[
              { value: 'All', label: t('reports.filters.allTypes') },
              { value: 'popeye', label: t('reports.filters.inspectionTypes.popeye') },
              { value: 'network', label: t('reports.filters.inspectionTypes.network') },
              { value: 'cluster', label: t('reports.filters.inspectionTypes.cluster') },
            ]}
          />

          <DatePicker.RangePicker
            placeholder={[t('reports.filters.startDate'), t('reports.filters.endDate')]}
            className="width-300"
            onChange={dates => setFilters(prev => ({ ...prev, dateRange: dates }))}
            value={filters.dateRange}
            format="DD.MM.YYYY"
          />

          <Input
            placeholder={t('reports.filters.searchPlaceholder')}
            className="width-250"
            onChange={e => setFilters(prev => ({ ...prev, search: e.target.value }))}
            value={filters.search}
          />
        </Space>
      </Card>
    );
  }
);

ReportsFilters.displayName = 'ReportsFilters';

export default ReportsFilters;
