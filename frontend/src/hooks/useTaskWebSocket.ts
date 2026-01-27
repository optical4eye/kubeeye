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
  const { status: wsStatus, connectionError } = useWebSocketStore();
  const [isWebSocketAvailable, setIsWebSocketAvailable] = useState(true);
  const [isTabVisible, setIsTabVisible] = useState(!document.hidden);

  // Initialize WebSocket connection with fallback
  useEffect(() => {
    // Get base URL from environment or window.location
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const baseUrl = `${protocol}//${host}`;

    wsManagerRef.current = new WebSocketConnectionManager(baseUrl, '/ws');

    if (isTabVisible) {
      wsManagerRef.current
        .connect(['tasks'])
        .then(() => {
          // WebSocket connected for task monitoring
        })
        .catch((error) => {
          console.error('WebSocket connection failed:', error);
          // Don't show error message here - reconnection logic will handle it
        });
    }

    // Subscribe to task messages
    const unsubscribe = wsManagerRef.current.subscribeToTasks((message: TaskMessage) => {
      handleTaskMessage(message);
    });

    // Handle WebSocket errors and disconnections
    const unsubscribeError = wsManagerRef.current.onError((error) => {
      console.error('WebSocket error in task monitoring:', error);
      if (!document.hidden) {
        message.error(t('websocket.error', 'WebSocket error occurred. Task monitoring may be unavailable.'));
      }
    });

    const unsubscribeClose = wsManagerRef.current.onClose((event) => {
      if (event.code !== 1000 && !document.hidden) {
        message.warning(t('websocket.reconnecting', 'WebSocket unavailable, attempting to reconnect'));
      }
    });

    const unsubscribeReconnectFailed = wsManagerRef.current.onReconnectFailed(() => {
      setIsWebSocketAvailable(false);
      if (!document.hidden) {
        message.warning(t('websocket.unavailable', 'WebSocket unavailable, task monitoring may be limited'));
      }
    });

    // Handle visibility change - disconnect when tab is hidden
    const handleVisibilityChange = () => {
      const visible = !document.hidden;
      setIsTabVisible(visible);
      if (!visible) {
        wsManagerRef.current?.disconnect();
      } else {
        // Reconnect when tab becomes visible
        wsManagerRef.current?.connect(['tasks']).catch((error) => {
          console.error('WebSocket reconnection failed:', error);
        });
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      unsubscribe();
      unsubscribeError();
      unsubscribeClose();
      unsubscribeReconnectFailed();
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
