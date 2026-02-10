import React, { useState, useEffect, useCallback } from 'react';
import { App } from 'antd';
import { useTranslation } from 'react-i18next';
import { getClusters, runInspectionAsync, getRules, getRuleTags } from '../services/api';
import { ActiveTasksList } from '../components/tasks';
import { InspectionForm } from '../components/inspection';
import { useTaskWebSocket } from '../hooks/useTaskWebSocket';

interface Task {
  task_id: string;
  task_type: string;
  status: string;
  created_at: string;
  payload?: any;
  started_at?: string;
  completed_at?: string;
  error?: string;
  result?: any;
}

const Inspection = React.memo(() => {
  const { t } = useTranslation();
  const { message: messageApi } = App.useApp();
  const [clusters, setClusters] = useState([]);
  const [selectedCluster, setSelectedCluster] = useState<string | null>(null);
  const [rules, setRules] = useState({});
  const [selectedRules, setSelectedRules] = useState<Record<string, number[]>>({
    node: [],
    opa: [],
  });
  const [availableTags, setAvailableTags] = useState([]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTasks, setActiveTasks] = useState<Task[]>([]);

  const { startTaskMonitoring, handleCancelTask } = useTaskWebSocket(activeTasks, setActiveTasks);

  const loadClusters = useCallback(async () => {
    try {
      const response = await getClusters();
      setClusters(response.data.clusters || []);
    } catch {
      messageApi.error(t('inspection.errorLoadingClusters'));
    }
  }, []);

  const loadRules = useCallback(async (tags: string[] | null = null) => {
    try {
      const response = await getRules(tags);
      setRules(response.data.rules || {});
    } catch {
      messageApi.error(t('inspection.errorLoadingRules'));
    }
  }, []);

  const loadTags = useCallback(async () => {
    try {
      const response = await getRuleTags();
      setAvailableTags(response.data.tags || []);
    } catch {
      messageApi.error(t('inspection.errorLoadingTags'));
    }
  }, []);

  useEffect(() => {
    loadClusters();
    loadTags();
    loadRules();
  }, [loadClusters, loadTags, loadRules]);

  useEffect(() => {
    const newSelectedRules: Record<string, number[]> = {};
    Object.keys(rules).forEach(ruleType => {
      newSelectedRules[ruleType] = (rules as any)[ruleType]?.map((rule: any) => rule.id) || [];
    });
    setSelectedRules(newSelectedRules);
  }, [rules]);

  useEffect(() => {
    loadRules(selectedTags.length > 0 ? selectedTags : null);
  }, [selectedTags, loadRules]);

  const handleRunInspection = useCallback(async () => {
    if (!selectedCluster) {
      messageApi.error(t('inspection.selectCluster'));
      return;
    }

    const totalSelectedRules = Object.values(selectedRules).reduce(
      (sum, arr) => sum + arr.length,
      0
    );
    if (totalSelectedRules === 0) {
      messageApi.error(t('inspection.selectRule'));
      return;
    }

    const inspectionData = {
      cluster_name: selectedCluster,
      selected_rules: selectedRules,
      inspection_type: 'immediate',
    };

    try {
      setLoading(true);

      // Async mode only
      const response = await runInspectionAsync(inspectionData);
      const taskId = response.data.task_id;

      const newTask = {
        task_id: taskId,
        task_type: 'inspection',
        status: 'pending',
        created_at: new Date().toISOString(),
        payload: inspectionData,
      };

      setActiveTasks(prev => [newTask, ...prev]);
      startTaskMonitoring(taskId);

      messageApi.success(t('inspection.inspectionStarted', { taskId }));
    } catch (error: any) {
      // Handle different types of errors
      if (error.code === 'ECONNABORTED') {
        messageApi.error(t('inspection.timeout', { cluster: selectedCluster }));
      } else if (error.message && error.message.includes('timeout')) {
        messageApi.error(t('inspection.timeoutFailed', { cluster: selectedCluster }));
      } else if (error.response?.status === 500) {
        messageApi.error(t('inspection.serverError'));
      } else if (error.response?.data?.detail) {
        messageApi.error(t('inspection.error', { detail: error.response.data.detail }));
      } else {
        messageApi.error(t('inspection.executionError'));
      }
    } finally {
      setLoading(false);
    }
  }, [selectedCluster, selectedRules, startTaskMonitoring]);

  const handleRuleSelection = useCallback((ruleType: string, ruleIds: number[]) => {
    setSelectedRules(prev => ({
      ...prev,
      [ruleType]: ruleIds,
    }));
  }, []);

  const formatTaskTime = useCallback((isoString: string) => {
    if (!isoString) return '';
    return new Date(isoString).toLocaleString();
  }, []);

  return (
    <div>
      <div className="page-title">{t('inspection.title')}</div>
      <div className="page-subtitle">{t('inspection.subtitle')}</div>

      <InspectionForm
        clusters={clusters}
        rules={rules}
        selectedCluster={selectedCluster}
        setSelectedCluster={setSelectedCluster}
        selectedRules={selectedRules}
        setSelectedRules={setSelectedRules}
        availableTags={availableTags}
        selectedTags={selectedTags}
        setSelectedTags={setSelectedTags}
        loading={loading}
        onRunInspection={handleRunInspection}
        handleRuleSelection={handleRuleSelection}
      />
      <ActiveTasksList
        activeTasks={activeTasks}
        handleCancelTask={handleCancelTask}
        formatTaskTime={formatTaskTime}
      />
    </div>
  );
});

Inspection.displayName = 'Inspection';

export default Inspection;
