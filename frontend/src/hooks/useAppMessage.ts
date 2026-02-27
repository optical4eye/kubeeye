import { App } from 'antd';
import type { MessageInstance } from 'antd/es/message/interface';

/**
 * Hook to access Ant Design message API through App context.
 * This replaces the static import of message from 'antd'.
 *
 * Must be used within a component that is rendered inside App component.
 *
 * @example
 * const message = useAppMessage();
 * message.success('Operation completed');
 */
export const useAppMessage = (): MessageInstance => {
  const { message } = App.useApp();
  return message;
};

export default useAppMessage;
