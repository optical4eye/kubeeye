import React, { useRef, useEffect, useState, useCallback } from 'react';
import { message } from 'antd';
import { getInspectionTaskStatus, cancelInspectionTask } from '../services/api';
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
  const pollingIntervals = useRef<Record<string, ReturnType<typeof setInterval>>>({});
  const wsManagerRef = useRef<WebSocketConnectionManager | null>(null);
  const [useWebSocket, setUseWebSocket] = useState(true);
  const [wsConnected, setWsConnected] = useState(false);

  // Initialize WebSocket connection
  useEffect(() => {
    if (useWebSocket) {
      try {
        // Get base URL from environment or window.location
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const baseUrl = `${protocol}//${host}`;

        wsManagerRef.current = new WebSocketConnectionManager(baseUrl);

        wsManagerRef.current
          .connect()
          .then(() => {
            setWsConnected(true);
            console.log('WebSocket connected for task monitoring');
          })
          .catch(error => {
            console.warn('WebSocket connection failed, falling back to polling:', error);
            setUseWebSocket(false);
          });

        // Subscribe to task messages
        const unsubscribe = wsManagerRef.current.subscribeToTasks((message: TaskMessage) => {
          handleTaskMessage(message);
        });

        return () => {
          unsubscribe();
          wsManagerRef.current?.disconnect();
        };
      } catch (error) {
        console.warn('WebSocket initialization failed, falling back to polling:', error);
        setUseWebSocket(false);
      }
    }
  }, [useWebSocket]);

  // Cleanup polling intervals on unmount
  useEffect(() => {
    return () => {
      Object.values(pollingIntervals.current).forEach(interval => {
        clearInterval(interval);
      });
      pollingIntervals.current = {};
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
    message.success(`Задача ${task.task_id} завершена успешно. Отчет доступен в разделе "Отчеты"`);

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
    message.error(`Задача ${task.task_id} завершилась с ошибкой: ${error || task.error}`);
  };

  const startTaskMonitoring = (taskId: string) => {
    if (useWebSocket && wsConnected) {
      // WebSocket is handling updates automatically
      console.log(`Monitoring task ${taskId} via WebSocket`);
    } else {
      // Fallback to polling
      startPolling(taskId);
    }
  };

  const startPolling = (taskId: string) => {
    if (pollingIntervals.current[taskId]) {
      clearInterval(pollingIntervals.current[taskId]);
    }

    const interval = setInterval(async () => {
      try {
        // Determine task type and use appropriate API
        const task = activeTasks.find(t => t.task_id === taskId);
        let response;

        if (task?.task_type === 'popeye') {
          const { getPopeyeTaskStatus } = await import('../services/api');
          response = await getPopeyeTaskStatus(taskId);
        } else {
          response = await getInspectionTaskStatus(taskId);
        }

        const updatedTask = response.data;

        setActiveTasks(prev => prev.map(t => (t.task_id === taskId ? updatedTask : t)));

        // Stop polling when task is completed or failed
        if (updatedTask.status === 'completed' || updatedTask.status === 'failed') {
          clearInterval(pollingIntervals.current[taskId]);
          delete pollingIntervals.current[taskId];

          if (updatedTask.status === 'completed') {
            showCompletionMessage(updatedTask);
          } else {
            showErrorMessage(updatedTask, updatedTask.error);
          }
        }
      } catch (error: any) {
        // Check if it's a 404 error (task not found)
        if (error.response?.status === 404) {
          message.error(
            `Задача ${taskId} не найдена. Возможно, она была удалена или истек срок действия.`
          );
        } else {
          message.error(`Ошибка при проверке статуса задачи ${taskId}: ${error.message}`);
        }

        clearInterval(pollingIntervals.current[taskId]);
        delete pollingIntervals.current[taskId];

        // Update task status to show error in UI
        setActiveTasks(prev =>
          prev.map(t =>
            t.task_id === taskId ? { ...t, status: 'failed', error: error.message } : t
          )
        );
      }
    }, 5000); // Poll every 5 seconds

    pollingIntervals.current[taskId] = interval;
  };

  const stopTaskMonitoring = (taskId: string) => {
    if (pollingIntervals.current[taskId]) {
      clearInterval(pollingIntervals.current[taskId]);
      delete pollingIntervals.current[taskId];
    }
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

      stopTaskMonitoring(taskId);
      setActiveTasks(prev =>
        prev.map(t => (t.task_id === taskId ? { ...t, status: 'cancelled' } : t))
      );
      message.success('Задача отменена');
    } catch {
      message.error('Ошибка отмены задачи');
    }
  };

  return {
    startTaskMonitoring,
    stopTaskMonitoring,
    handleCancelTask,
    isWebSocketEnabled: useWebSocket && wsConnected,
  };
};
