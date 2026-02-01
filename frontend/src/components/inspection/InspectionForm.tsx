import React, { useCallback } from 'react';
import { Card, Select, Button, Space, theme } from 'antd';
import { PlayCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { RuleSelector } from '../rules';
import { Cluster, Rule } from '../../types';

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
    availableTags,
    selectedTags,
    setSelectedTags,
    loading,
    onRunInspection,
    handleRuleSelection,
  }) => {
    const { t } = useTranslation();
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
            <div aria-label={t('inspection.selectClusterLabel')}>
              {t('inspection.selectClusterLabel')}
            </div>
            <Select
              className="margin-top-space-2"
              style={{ width: '100%' }}
              placeholder={t('inspection.selectClusterPlaceholder')}
              onChange={setSelectedCluster}
              value={selectedCluster}
              options={clusters.map(cluster => ({
                value: cluster.name,
                label: `${cluster.name} (${cluster.nodes?.length || 0} узлов)`,
              }))}
            />
          </div>

          {/* Tag Filter */}
          {getAllTags().length > 0 && (
            <div>
              <div aria-label={t('inspection.filterByTagsAria')}>
                {t('inspection.filterByTagsLabel')}
              </div>
              <Select
                mode="multiple"
                className="margin-top-space-2"
                style={{ width: '100%' }}
                placeholder={t('inspection.filterByTagsPlaceholder')}
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

          <div className="inspection-form-rules-container">
            <div className="inspection-form-rule-column">
              <RuleSelector
                ruleType="node"
                title={t('inspection.nodeRulesTitle')}
                availableRules={rules.node || []}
                selectedRules={selectedRules}
                onRuleSelection={handleRuleSelection}
              />
            </div>
            <div className="inspection-form-rule-column">
              <RuleSelector
                ruleType="opa"
                title={t('inspection.kubernetesRulesTitle')}
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
                  <strong>{t('inspection.selectedRules')}</strong>
                  <div className="margin-top-space-2">
                    {Object.entries(selectedRules).map(
                      ([type, rules]) =>
                        rules.length > 0 && (
                          <div key={type} className="inspection-form-rules-summary-item">
                            <span className="inspection-form-rules-summary-label">
                              {type === 'node'
                                ? t('inspection.nodeLabel')
                                : t('inspection.kubernetesLabel')}
                              :
                            </span>{' '}
                            {rules.length} {t('inspection.totalRules')}
                          </div>
                        )
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-bold text-accent">{totalSelectedRules}</div>
                  <div className="text-xs text-secondary">{t('inspection.totalRules')}</div>
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
            {t('inspection.runInspection')}
          </Button>
        </Space>
      </Card>
    );
  }
);

InspectionForm.displayName = 'InspectionForm';

export default InspectionForm;
