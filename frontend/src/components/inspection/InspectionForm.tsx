import React, { useCallback } from 'react';
import { Card, Select, Button, Space, Tag, theme } from 'antd';
import { PlayCircleOutlined } from '@ant-design/icons';
import { RuleSelector } from '../rules';
import { Cluster, Rule } from '../../types';

const { Option } = Select;

interface TagInfo {
  tag: string;
  count: number;
}

interface RulesByType {
  node?: Rule[];
  opa?: Rule[];
}

interface InspectionFormProps {
  clusters: Cluster[];
  rules: RulesByType;
  selectedCluster: string | null;
  setSelectedCluster: (value: string | null) => void;
  selectedRules: Record<string, number[]>;
  setSelectedRules: React.Dispatch<React.SetStateAction<Record<string, number[]>>>;
  availableTags: TagInfo[];
  selectedTags: string[];
  setSelectedTags: (tags: string[]) => void;
  loading: boolean;
  onRunInspection: () => void;
  handleRuleSelection: (ruleType: string, ruleIds: number[]) => void;
}

const InspectionForm: React.FC<InspectionFormProps> = React.memo(
  ({
    clusters,
    rules,
    selectedCluster,
    setSelectedCluster,
    selectedRules,
    setSelectedRules,
    availableTags,
    selectedTags,
    setSelectedTags,
    loading,
    onRunInspection,
    handleRuleSelection,
  }) => {
    const { token } = theme.useToken();

    const getAllTags = useCallback(() => {
      return availableTags;
    }, [availableTags]);

    const totalSelectedRules = Object.values(selectedRules).reduce(
      (sum, arr) => sum + (arr as number[]).length,
      0
    );

    return (
      <Card>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <div aria-label="Выберите кластер для инспекции">Выберите кластер для инспекции:</div>
            <Select
              className="margin-top-space-2"
              style={{ width: '100%' }}
              placeholder="Выберите кластер"
              onChange={setSelectedCluster}
              value={selectedCluster}
            >
              {clusters.map(cluster => (
                <Option key={cluster.name} value={cluster.name}>
                  {cluster.name} ({cluster.nodes?.length || 0} узлов)
                </Option>
              ))}
            </Select>
          </div>

          {/* Tag Filter */}
          {getAllTags().length > 0 && (
            <div>
              <div aria-label="Фильтр по тегам правил">Фильтр по тегам правил (опционально):</div>
              <Select
                mode="multiple"
                className="margin-top-space-2"
                style={{ width: '100%' }}
                placeholder="Выберите теги для фильтрации правил"
                onChange={setSelectedTags}
                value={selectedTags}
                allowClear
                options={getAllTags().map(({ tag, count }) => ({
                  value: tag,
                  label: `${tag} (${count})`,
                }))}
              />
            </div>
          )}

          <div style={{ display: 'flex', gap: 'var(--space-4)' }}>
            <div style={{ flex: 1 }}>
              <RuleSelector
                ruleType="node"
                title="Правила узлов"
                availableRules={rules.node || []}
                selectedRules={selectedRules}
                onRuleSelection={handleRuleSelection}
              />
            </div>
            <div style={{ flex: 1 }}>
              <RuleSelector
                ruleType="opa"
                title="Правила Kubernetes"
                availableRules={rules.opa || []}
                selectedRules={selectedRules}
                onRuleSelection={handleRuleSelection}
              />
            </div>
          </div>

          {/* Summary of selected rules */}
          {Object.values(selectedRules).some(arr => (arr as number[]).length > 0) && (
            <Card size="small" className="margin-top-space-4">
              <div className="flex-space-between">
                <div>
                  <strong>Выбранные правила:</strong>
                  <div className="margin-top-space-2">
                    {Object.entries(selectedRules).map(
                      ([type, rules]) =>
                        rules.length > 0 && (
                          <div key={type} style={{ marginBottom: token.marginXXS }}>
                            <span style={{ fontWeight: 'bold' }}>
                              {type === 'node' ? 'Узлы' : 'Kubernetes'}:
                            </span>{' '}
                            {rules.length} правил
                          </div>
                        )
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-bold text-accent">{totalSelectedRules}</div>
                  <div className="text-xs text-secondary">всего правил</div>
                </div>
              </div>
            </Card>
          )}

          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={onRunInspection}
            loading={loading}
            disabled={!selectedCluster || totalSelectedRules === 0}
            size="large"
            className="margin-top-space-4"
          >
            Запустить инспекцию
          </Button>
        </Space>
      </Card>
    );
  }
);

InspectionForm.displayName = 'InspectionForm';

export default InspectionForm;
