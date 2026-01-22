import React from 'react';
import { Card, Select, Input, Space } from 'antd';
import { DatePicker } from 'antd';
import { useTranslation } from 'react-i18next';
import { Filters } from '../hooks/useReportsFilters';

const { Option } = Select;
const { Search } = Input;

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
          >
            <Option value="All">{t('reports.filters.allClusters')}</Option>
            {clusters.map(cluster => (
              <Option key={cluster} value={cluster}>
                {cluster}
              </Option>
            ))}
          </Select>

          <Select
            placeholder={t('reports.filters.inspectionTypePlaceholder')}
            className="width-150"
            onChange={value => setFilters(prev => ({ ...prev, inspectionType: value }))}
            value={filters.inspectionType}
          >
            <Option value="All">{t('reports.filters.allTypes')}</Option>
            <Option value="popeye">{t('reports.filters.inspectionTypes.popeye')}</Option>
            <Option value="network">{t('reports.filters.inspectionTypes.network')}</Option>
            <Option value="cluster">{t('reports.filters.inspectionTypes.cluster')}</Option>
          </Select>

          <DatePicker.RangePicker
            placeholder={[t('reports.filters.startDate'), t('reports.filters.endDate')]}
            className="width-300"
            onChange={dates => setFilters(prev => ({ ...prev, dateRange: dates }))}
            value={filters.dateRange}
            format="DD.MM.YYYY"
          />

          <Search
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
