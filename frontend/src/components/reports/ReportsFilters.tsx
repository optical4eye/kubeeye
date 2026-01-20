import React from 'react';
import { Card, Select, Input, Space } from 'antd';
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
    return (
      <Card className="margin-bottom-space-4">
        <Space wrap>
          <Select
            placeholder="Кластер"
            className="width-200"
            onChange={value => setFilters(prev => ({ ...prev, cluster: value }))}
            value={filters.cluster}
          >
            <Option value="All">Все кластеры</Option>
            {clusters.map(cluster => (
              <Option key={cluster} value={cluster}>
                {cluster}
              </Option>
            ))}
          </Select>

          <Select
            placeholder="Период"
            className="width-150"
            onChange={value => setFilters(prev => ({ ...prev, period: value }))}
            value={filters.period}
          >
            <Option value="All">Все время</Option>
            <Option value="Today">Сегодня</Option>
            <Option value="Last 7 days">Последние 7 дней</Option>
            <Option value="Last 30 days">Последние 30 дней</Option>
          </Select>

          <Search
            placeholder="Поиск по кластеру или ID"
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
