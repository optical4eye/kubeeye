import React from 'react';
import { Card, Select, Input, Space } from 'antd';
import { DatePicker } from 'antd';
import dayjs from 'dayjs';
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
            placeholder="Тип инспекции"
            className="width-150"
            onChange={value => setFilters(prev => ({ ...prev, inspectionType: value }))}
            value={filters.inspectionType}
          >
            <Option value="All">Все типы</Option>
            <Option value="popeye">Popeye</Option>
            <Option value="network">Network</Option>
            <Option value="cluster">Cluster</Option>
          </Select>

          <DatePicker.RangePicker
            placeholder={['Начальная дата', 'Конечная дата']}
            className="width-300"
            onChange={(dates) => setFilters(prev => ({ ...prev, dateRange: dates }))}
            value={filters.dateRange}
            format="DD.MM.YYYY"
          />

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
