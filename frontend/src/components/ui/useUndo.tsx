import React, { useState, useCallback } from 'react';
import { App } from 'antd';
import { UndoOutlined } from '@ant-design/icons';

interface UndoAction {
  id: string;
  message: string;
  onUndo: () => void | Promise<void>;
}

/**
 * Hook для управления Undo функционалом
 * Позволяет пользователям отменять последние действия (удаление, изменение и т.д.)
 */
export const useUndo = () => {
  const { message } = App.useApp();
  const [undoStack, setUndoStack] = useState<UndoAction[]>([]);

  /**
   * Добавляет действие в стек undo и показывает уведомление с возможностью отмены
   */
  const showUndoMessage = useCallback((action: UndoAction) => {
    setUndoStack(prev => [...prev, action]);

    message.success({
      content: action.message,
      duration: 5,
      icon: <UndoOutlined />,
      onClick: async () => {
        try {
          await action.onUndo();
          setUndoStack(prev => prev.filter(item => item.id !== action.id));
          message.success('Action undone successfully');
        } catch (error) {
          message.error('Failed to undo action');
        }
      },
    });
  }, [message]);

  /**
   * Очищает стек undo
   */
  const clearUndoStack = useCallback(() => {
    setUndoStack([]);
  }, []);

  /**
   * Удаляет конкретное действие из стека
   */
  const removeFromUndoStack = useCallback((id: string) => {
    setUndoStack(prev => prev.filter(item => item.id !== id));
  }, []);

  return {
    undoStack,
    showUndoMessage,
    clearUndoStack,
    removeFromUndoStack,
  };
};

/**
 * Компонент для отображения кнопки Undo в контекстном меню
 */
export const UndoButton: React.FC<{
  onUndo: () => void | Promise<void>;
  disabled?: boolean;
}> = ({ onUndo, disabled = false }) => {
  const { message } = App.useApp();

  const handleUndo = async () => {
    try {
      await onUndo();
      message.success('Action undone successfully');
    } catch (error) {
      message.error('Failed to undo action');
    }
  };

  return (
    <button
      onClick={handleUndo}
      disabled={disabled}
      className="undo-button"
      title="Undo last action"
    >
      <UndoOutlined />
    </button>
  );
};

export default useUndo;
