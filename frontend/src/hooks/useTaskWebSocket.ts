import React, { useRef, useEffect, useCallback } from 'react';
import { message } from 'antd';
import { useTranslation } from 'react-i18next';
import { cancelInspectionTask } from '../services/api';
import { WebSocketConnectionManager } from '../services/websocket/connectionManager';
import { TaskMessage } from '../services/websocket/messageTypes';

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

export const useTaskWebSocket = (
  activeTasks: Task[],
  setActiveTasks: React.Dispatch<React.SetStateAction<Task[]>>
) => {
  const { t } = useTranslation();
  const wsManagerRef = useRef<WebSocketConnectionManager | null>(null);

  // Initialize WebSocket connection
  useEffect(() => {
    // Get base URL from environment or window.location
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const baseUrl = `${protocol}//${host}`;

    wsManagerRef.current = new WebSocketConnectionManager(baseUrl);

    wsManagerRef.current
      .connect()
      .then(() => {
        // WebSocket connected for task monitoring
      })
      .catch(error => {
        // WebSocket connection failed
      });

    // Subscribe to task messages
    const unsubscribe = wsManagerRef.current.subscribeToTasks((message: TaskMessage) => {
      handleTaskMessage(message);
    });

    return () => {
      unsubscribe();
      wsManagerRef.current?.disconnect();
    };
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      wsManagerRef.current?.disconnect();
    };
  }, []);

  const handleTaskMessage = useCallback((message: TaskMessage) => {
    const { task_id, result, error } = message.payload;

    setActiveTasks(prev =>
      prev.map(t => {
        if (t.task_id === task_id) {
          const updatedTask = { ...t };

          switch (message.type) {
            case 'task_started':
              updatedTask.status = 'running';
              updatedTask.started_at = new Date().toISOString();
              break;
            case 'task_completed':
              updatedTask.status = 'completed';
              updatedTask.completed_at = new Date().toISOString();
              updatedTask.result = result;
              showCompletionMessage(updatedTask);
              break;
            case 'task_failed':
              updatedTask.status = 'failed';
              updatedTask.completed_at = new Date().toISOString();
              updatedTask.error = error;
              showErrorMessage(updatedTask, error);
              break;
          }

          return updatedTask;
        }
        return t;
      })
    );
  }, []);

  const showCompletionMessage = (task: Task) => {
    message.success(t('tasks.taskCompleted', { taskId: task.task_id }));

    // Trigger a custom event to notify other components about the new report
    window.dispatchEvent(
      new CustomEvent('newReportAvailable', {
        detail: {
          taskId: task.task_id,
          result: task.result,
        },
      })
    );
  };

  const showErrorMessage = (task: Task, error?: string) => {
    message.error(t('tasks.taskFailed', { taskId: task.task_id, error: error || task.error }));
  };

  const startTaskMonitoring = (taskId: string) => {
    // WebSocket is handling updates automatically
  };

  const handleCancelTask = async (taskId: string) => {
    try {
      // Determine task type and use appropriate API
      const task = activeTasks.find(t => t.task_id === taskId);

      if (task?.task_type === 'popeye') {
        const { cancelPopeyeTask } = await import('../services/api');
        await cancelPopeyeTask(taskId);
      } else {
        await cancelInspectionTask(taskId);
      }

      setActiveTasks(prev =>
        prev.map(t => (t.task_id === taskId ? { ...t, status: 'cancelled' } : t))
      );
      message.success(t('tasks.taskCancelled'));
    } catch {
      message.error(t('tasks.cancelTaskError'));
    }
  };

  return {
    startTaskMonitoring,
    handleCancelTask,
  };
};
