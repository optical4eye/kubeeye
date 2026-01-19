import React, { useState, useEffect, useCallback } from 'react';
import { Tabs, message } from 'antd';
import { getClusters, runInspectionAsync, getRules, getRuleTags } from '../services/api';
import ScheduledInspection from '../components/ScheduledInspection';
import InspectionForm from '../components/InspectionForm';
import ActiveTasksList from '../components/ActiveTasksList';
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

const { TabPane } = Tabs;

const Inspection = React.memo(() => {
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
      message.error('Ошибка загрузки кластеров');
    }
  }, []);

  const loadRules = useCallback(async (tags: string[] | null = null) => {
    try {
      const response = await getRules(tags);
      setRules(response.data.rules || {});
    } catch {
      message.error('Ошибка загрузки правил');
    }
  }, []);

  const loadTags = useCallback(async () => {
    try {
      const response = await getRuleTags();
      setAvailableTags(response.data.tags || []);
    } catch {
      message.error('Ошибка загрузки тегов');
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
      message.error('Выберите кластер');
      return;
    }

    const totalSelectedRules = Object.values(selectedRules).reduce(
      (sum, arr) => sum + arr.length,
      0
    );
    if (totalSelectedRules === 0) {
      message.error('Выберите хотя бы одно правило');
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

      message.success(`Инспекция запущена (ID: ${taskId})`);
    } catch (error: any) {
      // Handle different types of errors
      if (error.code === 'ECONNABORTED') {
        message.error(
          `Таймаут подключения к кластеру ${selectedCluster}. Проверьте доступность узлов кластера.`
        );
      } else if (error.message && error.message.includes('timeout')) {
        message.error(
          `Не удалось выполнить инспекцию кластера ${selectedCluster} из-за таймаута подключения`
        );
      } else if (error.response?.status === 500) {
        message.error('Ошибка сервера при выполнении инспекции');
      } else if (error.response?.data?.detail) {
        message.error(`Ошибка: ${error.response.data.detail}`);
      } else {
        message.error('Ошибка выполнения инспекции');
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
      <div className="page-title">Центр инспекции кластеров</div>
      <div className="page-subtitle">
        Выполнение немедленной или запланированной инспекции, управление правилами инспекции
      </div>

      <Tabs defaultActiveKey="1">
        <TabPane tab="Немедленная инспекция" key="1">
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
        </TabPane>

        <TabPane tab="Запланированная инспекция" key="2">
          <ScheduledInspection />
        </TabPane>
      </Tabs>
    </div>
  );
});

Inspection.displayName = 'Inspection';

export default Inspection;
