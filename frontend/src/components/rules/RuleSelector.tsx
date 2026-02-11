import React from 'react';
import { Card, Checkbox, Space } from 'antd';

const RuleSelector = ({ ruleType, title, availableRules, selectedRules, onRuleSelection }) => {
  const selected = selectedRules[ruleType] || [];
  const allSelected = availableRules.length > 0 && selected.length === availableRules.length;
  const someSelected = selected.length > 0 && selected.length < availableRules.length;

  const handleSelectAll = checked => {
    if (checked) {
      onRuleSelection(
        ruleType,
        availableRules.map(rule => rule.id)
      );
    } else {
      onRuleSelection(ruleType, []);
    }
  };

  return (
    <Card title={title} size="small">
      {availableRules.length > 0 && (
        <div className="rule-selector-header">
          <Checkbox
            indeterminate={someSelected}
            checked={allSelected}
            onChange={e => handleSelectAll(e.target.checked)}
          >
            Выбрать все ({availableRules.length})
          </Checkbox>
        </div>
      )}
      <Checkbox.Group
        value={selected}
        onChange={values => onRuleSelection(ruleType, values)}
        style={{ width: '100%' }}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          {availableRules.map(rule => (
            <Checkbox key={rule.id} value={rule.id} style={{ width: '100%', alignItems: 'flex-start' }}>
              <div style={{ marginLeft: '8px', flex: 1 }}>
                <strong>{rule.name}</strong>
                <div className="rule-selector-description">{rule.description}</div>
                {rule.tags && rule.tags.length > 0 && (
                  <div className="rule-selector-tags">Теги: {rule.tags.join(', ')}</div>
                )}
              </div>
            </Checkbox>
          ))}
        </Space>
      </Checkbox.Group>
    </Card>
  );
};

export default RuleSelector;
