import React, { useRef, useEffect, useCallback, useState } from 'react';
import { message } from 'antd';
import { useTranslation } from 'react-i18next';
import { cancelInspectionTask } from '../services/api';
import { WebSocketConnectionManager } from '../services/websocket/connectionManager';
import { TaskMessage } from '../services/websocket/messageTypes';
import { useWebSocketStore } from '../stores/websocketStore';

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
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const [isWebSocketAvailable, setIsWebSocketAvailable] = useState(true);
  const { status: wsStatus, connectionError } = useWebSocketStore();

  // Initialize WebSocket connection with fallback
  useEffect(() => {
    // Get base URL from environment or window.location
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const baseUrl = `${protocol}//${host}`;

    wsManagerRef.current = new WebSocketConnectionManager(baseUrl, '/ws/tasks');

    wsManagerRef.current
      .connect(['tasks'])
      .then(() => {
        setIsWebSocketAvailable(true);
        // WebSocket connected for task monitoring
      })
      .catch((error) => {
        console.warn('WebSocket connection failed, falling back to polling:', error);
        setIsWebSocketAvailable(false);
        startPolling();
      });

    // Subscribe to task messages
    const unsubscribe = wsManagerRef.current.subscribeToTasks((message: TaskMessage) => {
      handleTaskMessage(message);
    });

    // Handle WebSocket errors and disconnections
    const unsubscribeError = wsManagerRef.current.onError((error) => {
      console.error('WebSocket error in task monitoring:', error);
      if (isWebSocketAvailable) {
        setIsWebSocketAvailable(false);
        startPolling();
        message.warning(t('websocket.fallbackToPolling', 'WebSocket unavailable, using polling for updates'));
      }
    });

    const unsubscribeClose = wsManagerRef.current.onClose((event) => {
      console.log('WebSocket closed in task monitoring:', event.code);
      if (isWebSocketAvailable && event.code !== 1000) {
        setIsWebSocketAvailable(false);
        startPolling();
        message.warning(t('websocket.fallbackToPolling', 'WebSocket unavailable, using polling for updates'));
      }
    });

    return () => {
      unsubscribe();
      unsubscribeError();
      unsubscribeClose();
      wsManagerRef.current?.disconnect();
      stopPolling();
    };
  }, [isWebSocketAvailable]);

  // Polling fallback when WebSocket is unavailable
  const startPolling = useCallback(() => {
    if (pollingIntervalRef.current) return; // Already polling

    pollingIntervalRef.current = setInterval(async () => {
      try {
        // Poll for task updates - this would need to be implemented in the API
        // For now, we'll just log that polling is active
        console.log('Polling for task updates...');
        // TODO: Implement actual polling logic when API supports it
      } catch (error) {
        console.error('Polling error:', error);
      }
    }, 5000); // Poll every 5 seconds
  }, []);

  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
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

  const startTaskMonitoring = (_taskId: string) => {
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
    isWebSocketAvailable,
    connectionError,
  };
};
