import React, { useState, useEffect } from 'react';
import { Card, Tabs, Table, Button, Select, Input, Space, Tag, Alert, Modal, Form, message, Collapse } from 'antd';
import { ReloadOutlined, SettingOutlined, DownloadOutlined, SyncOutlined } from '@ant-design/icons';
import * as api from '../services/api';

const { TabPane } = Tabs;
const { Option } = Select;

const RuleManagement = () => {
  const [rules, setRules] = useState({});
  const [useGitops, setUseGitops] = useState(false);
  const [gitopsConfig, setGitopsConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [filteredRules, setFilteredRules] = useState([]);
  const [filters, setFilters] = useState({
    type: 'all',
    search: ''
  });

  const loadRules = async () => {
    try {
      setLoading(true);
      const response = await api.getRules();
      console.log('Rules API response:', response.data);
      setRules(response.data.rules || {});
      setUseGitops(response.data.use_gitops || false);

      // Load GitOps config if GitOps is enabled
      if (response.data.use_gitops) {
        try {
          const gitopsResponse = await api.getGitopsConfig(); // eslint-disable-line no-undef
          setGitopsConfig(gitopsResponse.data);
          console.log('GitOps config loaded:', gitopsResponse.data);
        } catch (gitopsError) {
          console.error('Failed to load GitOps config:', gitopsError);
          setGitopsConfig(null);
        }
      } else {
        setGitopsConfig(null);
      }

      // Debug logging
      const totalRules = Object.values(response.data.rules || {}).reduce((sum, rules) => sum + (Array.isArray(rules) ? rules.length : 0), 0);
      console.log(`Loaded ${totalRules} rules, GitOps: ${response.data.use_gitops}`);
    } catch (error) {
      message.error('Ошибка загрузки правил');
      console.error('Rules loading error:', error);
      // Set fallback data
      setRules({});
      setUseGitops(false);
      setGitopsConfig(null);
    } finally {
      setLoading(false);
    }
  };

  const syncGitopsRepository = async () => {
    try {
      setSyncing(true);
      const response = await api.syncGitopsRepository();
      message.success(response.data.message);
      // Reload rules after sync
      await loadRules();
    } catch (error) {
      message.error('Ошибка синхронизации GitOps репозитория');
      console.error('GitOps sync error:', error);
    } finally {
      setSyncing(false);
    }
  };

  useEffect(() => {
    loadRules();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [rules, filters]);

  const applyFilters = () => {
    let allRules = [];

    // Собираем все правила
    Object.entries(rules).forEach(([type, typeRules]) => {
      if (Array.isArray(typeRules)) {
        typeRules.forEach(rule => {
          allRules.push({
            ...rule,
            type: type
          });
        });
      }
    });

    // Применяем фильтры
    let filtered = allRules;

    if (filters.type !== 'all') {
      filtered = filtered.filter(rule => rule.type === filters.type);
    }

    if (filters.search) {
      filtered = filtered.filter(rule =>
        rule.name.toLowerCase().includes(filters.search.toLowerCase()) ||
        rule.description.toLowerCase().includes(filters.search.toLowerCase())
      );
    }

    if (!filters.showDisabled) {
      filtered = filtered.filter(rule => rule.enabled !== false);
    }

    setFilteredRules(filtered);
  };

  const getTypeLabel = (type) => {
    const labels = {
      node: 'Узлы',
      prometheus: 'Мониторинг',
      opa: 'Kubernetes'
    };
    return labels[type] || type;
  };

  const getSeverityTag = (severity) => {
    switch (severity) {
      case 'critical':
        return <Tag className="status-critical">Критическая</Tag>;
      case 'high':
        return <Tag className="status-high">Высокая</Tag>;
      case 'medium':
        return <Tag className="status-medium">Средняя</Tag>;
      case 'low':
        return <Tag className="status-low">Низкая</Tag>;
      case 'warning':
        return <Tag className="status-warning">Предупреждение</Tag>;
      case 'info':
        return <Tag className="status-info">Информация</Tag>;
      default:
        return <Tag className="status-unknown">Неизвестная</Tag>;
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 200,
    },
    {
      title: 'Название',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Тип',
      dataIndex: 'type',
      key: 'type',
      render: (type) => getTypeLabel(type),
    },
    {
      title: 'Серьезность',
      dataIndex: 'severity',
      key: 'severity',
      render: getSeverityTag,
    },
    {
      title: 'Описание',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
  ];

  const ruleStats = () => {
    const stats = { node: 0, prometheus: 0, opa: 0, total: 0 };
    Object.entries(rules).forEach(([type, typeRules]) => {
      if (Array.isArray(typeRules)) {
        stats[type] = typeRules.length;
        stats.total += typeRules.length;
      }
    });
    return stats;
  };

  const stats = ruleStats();

  return (
    <div>
      <div className="page-title">Управление правилами инспекции</div>

      <Card className="margin-bottom-space-4">
        <Space wrap>
          <Select
            placeholder="Тип правил"
            className="width-150"
            onChange={(value) => setFilters(prev => ({ ...prev, type: value }))}
            value={filters.type}
          >
            <Option value="all">Все типы</Option>
            <Option value="node">Узлы</Option>
            <Option value="prometheus">Мониторинг</Option>
            <Option value="opa">Безопасность</Option>
          </Select>

          <Input
            placeholder="Поиск по названию или описанию"
            className="width-250"
            onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
            value={filters.search}
          />


          <Button icon={<ReloadOutlined />} onClick={loadRules}>
            Обновить список rules
          </Button>

          {useGitops && (
            <Button
              type="primary"
              icon={<SyncOutlined />}
              loading={syncing}
              onClick={syncGitopsRepository}
            >
              Синхронизировать репозиторий
            </Button>
          )}
        </Space>
      </Card>

      <Tabs defaultActiveKey="1">
        <TabPane tab={`Все правила (${stats.total})`} key="1">
          <Card>
            <Table
              columns={columns}
              dataSource={filteredRules}
              loading={loading}
              rowKey="id"
              pagination={{ pageSize: 20 }}
            />
          </Card>
        </TabPane>

        <TabPane tab={`Узлы (${stats.node})`} key="2">
          <Card>
            <Table
              columns={columns.filter(col => col.key !== 'type')}
              dataSource={filteredRules.filter(rule => rule.type === 'node')}
              loading={loading}
              rowKey="id"
              pagination={{ pageSize: 20 }}
            />
          </Card>
        </TabPane>

        <TabPane tab={`Мониторинг (${stats.prometheus})`} key="3">
          <Card>
            <Table
              columns={columns.filter(col => col.key !== 'type')}
              dataSource={filteredRules.filter(rule => rule.type === 'prometheus')}
              loading={loading}
              rowKey="id"
              pagination={{ pageSize: 20 }}
            />
          </Card>
        </TabPane>

        <TabPane tab={`Kubernetes (${stats.opa})`} key="4">
          <Card>
            <Table
              columns={columns.filter(col => col.key !== 'type')}
              dataSource={filteredRules.filter(rule => rule.type === 'opa')}
              loading={loading}
              rowKey="id"
              pagination={{ pageSize: 20 }}
            />
          </Card>
        </TabPane>

        <TabPane tab="Настройки" key="5">
            <Card>
              <Alert
                message="Режим управления правилами"
                description={
                  useGitops
                    ? "Используется GitOps режим. Правила загружаются из Git репозитория. Изменения правил производятся через коммиты в репозиторий."
                    : "Используется локальный режим. Правила встроены в приложение и обновляются вместе с ним."
                }
                type={useGitops ? "info" : "warning"}
                showIcon
                className="margin-bottom-space-4"
              />


              <Space direction="vertical">
                <div>
                  <strong>Текущий режим:</strong> {useGitops ? 'GitOps' : 'Локальный'}
                </div>
                <div>
                  <strong>Всего правил:</strong> {stats.total}
                </div>
                <div>
                  <strong>По типам:</strong>
                  <ul>
                    <li>Узлы: {stats.node}</li>
                    <li>Мониторинг: {stats.prometheus}</li>
                    <li>Безопасность: {stats.opa}</li>
                  </ul>
                </div>
                {useGitops && gitopsConfig && gitopsConfig.repository && (
                  <div>
                    <strong>Информация о GitOps репозитории:</strong>
                    <ul>
                      <li><strong>Название:</strong> {gitopsConfig.repository.name}</li>
                      <li><strong>URL:</strong> {gitopsConfig.repository.url}</li>
                      <li><strong>Ветка:</strong> {gitopsConfig.repository.branch}</li>
                      <li><strong>Описание:</strong> {gitopsConfig.repository.description || 'Не указано'}</li>
                      <li><strong>SSL верификация:</strong> {gitopsConfig.repository.insecure ? 'Отключена' : 'Включена'}</li>
                      {gitopsConfig.from_env && (
                        <li><strong>Источник конфигурации:</strong> Переменные окружения</li>
                      )}
                    </ul>
                  </div>
                )}
              </Space>
            </Card>
          </TabPane>
      </Tabs>
    </div>
  );
};

export default RuleManagement;