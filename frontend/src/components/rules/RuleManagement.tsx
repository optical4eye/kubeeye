import React, { useState, useEffect } from 'react';
import { Card, Tabs, Table, Button, Select, Input, Space, Tag, Alert, message } from 'antd';
const { Option } = Select;
import { ReloadOutlined, SyncOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import * as api from '../../services/api';
import { getSeverityTag } from '../ui/statusUtils';

const RuleManagement = () => {
  const { t } = useTranslation();
  const [rules, setRules] = useState({});
  const [useGitops, setUseGitops] = useState(false);
  const [gitopsConfig, setGitopsConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [filteredRules, setFilteredRules] = useState([]);
  const [availableTags, setAvailableTags] = useState([]);
  const [filters, setFilters] = useState({
    type: 'all',
    search: '',
    tags: [],
  });

  const loadRules = async () => {
    try {
      setLoading(true);
      const response = await api.getRules();
      setRules(response.data.rules || {});
      setUseGitops(response.data.use_gitops || false);

      // Load GitOps config if GitOps is enabled
      if (response.data.use_gitops) {
        try {
          const gitopsResponse = await api.getGitopsConfig();
          setGitopsConfig(gitopsResponse.data);
        } catch (gitopsError) {
          setGitopsConfig(null);
        }
      } else {
        setGitopsConfig(null);
      }

      // Debug logging
      const totalRules = Object.values(response.data.rules || {}).reduce(
        (sum, rules) => sum + (Array.isArray(rules) ? rules.length : 0),
        0
      );
    } catch (error) {
      message.error(t('rules.errorLoadingRules'));
      // Set fallback data
      setRules({});
      setUseGitops(false);
      setGitopsConfig(null);
    } finally {
      setLoading(false);
    }
  };

  const loadTags = async () => {
    try {
      const response = await api.getRuleTags();
      setAvailableTags(response.data.tags || []);
    } catch (error) {
      setAvailableTags([]);
    }
  };

  const syncGitopsRepository = async () => {
    try {
      setSyncing(true);
      const response = await api.syncGitopsRepository();
      message.success(response.data.message);
      // Reload rules after sync
      await loadRules();
      await loadTags();
    } catch (error) {
      message.error(t('rules.errorSyncGitops'));
    } finally {
      setSyncing(false);
    }
  };

  useEffect(() => {
    loadRules();
    loadTags();
  }, []);

  useEffect(() => {
    applyFilters();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rules, filters]);

  const applyFilters = () => {
    let allRules = [];

    // Собираем все правила
    Object.entries(rules).forEach(([type, typeRules]) => {
      if (Array.isArray(typeRules)) {
        typeRules.forEach(rule => {
          allRules.push({
            ...rule,
            type: type,
          });
        });
      }
    });

    // Применяем фильтры
    let filtered = allRules;

    if (filters.type !== 'all') {
      filtered = filtered.filter(rule => rule.type === filters.type);
    }

    if (filters.tags && filters.tags.length > 0) {
      filtered = filtered.filter(
        rule => rule.tags && filters.tags.some(tag => rule.tags.includes(tag))
      );
    }

    if (filters.search) {
      filtered = filtered.filter(
        rule =>
          rule.name.toLowerCase().includes(filters.search.toLowerCase()) ||
          rule.description.toLowerCase().includes(filters.search.toLowerCase())
      );
    }

    if (!filters.showDisabled) {
      filtered = filtered.filter(rule => rule.enabled !== false);
    }

    setFilteredRules(filtered);
  };

  const getTypeLabel = type => {
    return t(`rules.typeLabels.${type}`, type);
  };

  const columns = [
    {
      title: t('rules.columns.id'),
      dataIndex: 'id',
      key: 'id',
      width: 200,
    },
    {
      title: t('rules.columns.name'),
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: t('rules.columns.type'),
      dataIndex: 'type',
      key: 'type',
      render: type => getTypeLabel(type),
    },
    {
      title: t('rules.columns.tags'),
      dataIndex: 'tags',
      key: 'tags',
      render: tags =>
        tags && tags.length > 0 ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
            {tags.map(tag => (
              <Tag
                key={tag}
                size="small"
                className="inspection-rule-tags"
                onClick={() => {
                  const currentTags = filters.tags || [];
                  const newTags = currentTags.includes(tag)
                    ? currentTags.filter(t => t !== tag)
                    : [...currentTags, tag];
                  setFilters(prev => ({ ...prev, tags: newTags }));
                }}
              >
                {tag}
              </Tag>
            ))}
          </div>
        ) : null,
    },
    {
      title: t('rules.columns.severity'),
      dataIndex: 'severity',
      key: 'severity',
      render: getSeverityTag,
    },
    {
      title: t('rules.columns.description'),
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
  ];

  const ruleStats = () => {
    const stats = { node: 0, opa: 0, total: 0 };
    Object.entries(rules).forEach(([type, typeRules]) => {
      if (Array.isArray(typeRules)) {
        stats[type] = typeRules.length;
        stats.total += typeRules.length;
      }
    });
    return stats;
  };

  const getAllTags = () => {
    return availableTags;
  };

  const stats = ruleStats();

  const items = [
    {
      key: '1',
      label: `${t('rules.tabs.all')} (${stats.total})`,
      children: (
        <Card>
          <Table
            columns={columns}
            dataSource={filteredRules}
            loading={loading}
            rowKey="id"
            pagination={{ pageSize: 20 }}
          />
        </Card>
      ),
    },
    {
      key: '2',
      label: `${t('rules.tabs.node')} (${stats.node})`,
      children: (
        <Card>
          <Table
            columns={columns.filter(col => col.key !== 'type')}
            dataSource={filteredRules.filter(rule => rule.type === 'node')}
            loading={loading}
            rowKey="id"
            pagination={{ pageSize: 20 }}
          />
        </Card>
      ),
    },
    {
      key: '4',
      label: `${t('rules.tabs.kubernetes')} (${stats.opa})`,
      children: (
        <Card>
          <Table
            columns={columns.filter(col => col.key !== 'type')}
            dataSource={filteredRules.filter(rule => rule.type === 'opa')}
            loading={loading}
            rowKey="id"
            pagination={{ pageSize: 20 }}
          />
        </Card>
      ),
    },
    {
      key: '5',
      label: t('rules.tabs.settings'),
      children: (
        <Card>
          <Alert
            message={t('rules.settings.modeTitle')}
            description={
              useGitops
                ? t('rules.settings.gitopsDescription')
                : t('rules.settings.localDescription')
            }
            type={useGitops ? 'info' : 'warning'}
            showIcon
            className="margin-bottom-space-4"
          />

          <Space direction="vertical">
            <div>
              <strong>{t('rules.settings.currentMode')}</strong>{' '}
              {useGitops ? t('rules.settings.gitopsMode') : t('rules.settings.localMode')}
            </div>
            <div>
              <strong>{t('rules.settings.totalRules')}</strong> {stats.total}
            </div>
            <div>
              <strong>{t('rules.settings.byType')}</strong>
              <ul>
                <li>
                  {t('rules.settings.nodes')} {stats.node}
                </li>
                <li>
                  {t('rules.settings.security')} {stats.opa}
                </li>
              </ul>
            </div>
            {useGitops && gitopsConfig && gitopsConfig.repository && (
              <div>
                <strong>{t('rules.settings.gitopsInfo')}</strong>
                <ul>
                  <li>
                    <strong>{t('rules.settings.name')}</strong> {gitopsConfig.repository.name}
                  </li>
                  <li>
                    <strong>{t('rules.settings.url')}</strong> {gitopsConfig.repository.url}
                  </li>
                  <li>
                    <strong>{t('rules.settings.branch')}</strong> {gitopsConfig.repository.branch}
                  </li>
                  <li>
                    <strong>{t('rules.settings.description')}</strong>{' '}
                    {gitopsConfig.repository.description || t('rules.settings.description')}
                  </li>
                  <li>
                    <strong>{t('rules.settings.sslVerification')}</strong>{' '}
                    {gitopsConfig.repository.insecure
                      ? t('rules.settings.disabled')
                      : t('rules.settings.enabled')}
                  </li>
                  {gitopsConfig.from_env && (
                    <li>
                      <strong>{t('rules.settings.configSource')}</strong>{' '}
                      {t('rules.settings.envVars')}
                    </li>
                  )}
                </ul>
              </div>
            )}
          </Space>
        </Card>
      ),
    },
  ];

  return (
    <div>
      <div className="page-title">{t('rules.title')}</div>

      <Card className="margin-bottom-space-4">
        <Space wrap>
          <Select
            placeholder={t('rules.filters.ruleType')}
            className="width-150"
            onChange={value => setFilters(prev => ({ ...prev, type: value }))}
            value={filters.type}
          >
            <Option value="all">{t('rules.filters.allTypes')}</Option>
            <Option value="node">{t('rules.filters.nodes')}</Option>
            <Option value="opa">{t('rules.filters.security')}</Option>
          </Select>

          <Select
            mode="multiple"
            placeholder={t('rules.filters.filterByTags')}
            onChange={value => setFilters(prev => ({ ...prev, tags: value }))}
            value={filters.tags}
            allowClear
            style={{ minWidth: 150 }}
            options={getAllTags().map(({ tag, count }) => ({
              value: tag,
              label: `${tag} (${count})`,
            }))}
          />

          <Input
            placeholder={t('rules.filters.search')}
            className="width-250"
            onChange={e => setFilters(prev => ({ ...prev, search: e.target.value }))}
            value={filters.search}
          />

          <Button icon={<ReloadOutlined />} onClick={loadRules}>
            {t('rules.filters.refreshRules')}
          </Button>

          {useGitops && (
            <Button
              type="primary"
              icon={<SyncOutlined />}
              loading={syncing}
              onClick={syncGitopsRepository}
            >
              {t('rules.filters.syncRepo')}
            </Button>
          )}
        </Space>
      </Card>

      <Tabs defaultActiveKey="1" items={items} />
    </div>
  );
};

export default RuleManagement;
