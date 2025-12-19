import React from 'react';
import { Form, Input, Button, Space, Collapse, Checkbox } from 'antd';

const ClusterForm = ({ form, onSubmit, onTestNodes, onTestKubeconfig, isEditMode = false }) => {
  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={onSubmit}
      aria-label={isEditMode ? 'Форма редактирования кластера' : 'Форма создания кластера'}
    >
      <Form.Item
        name="name"
        label="Имя кластера"
        rules={[{ required: true, message: 'Введите имя кластера' }]}
      >
        <Input placeholder="production" aria-label="Имя кластера" />
      </Form.Item>

      <Form.Item
        name="nodes_text"
        label="Список узлов"
        rules={[{ required: true, message: 'Добавьте хотя бы один узел' }]}
      >
        <Input.TextArea
          rows={6}
          placeholder={`Добавьте SSH узлы для проверки в формате: IP:Port User AuthType [Password/KeyPath]\nПримеры:\n192.168.1.100:22 root password mypassword123\n192.168.1.101:22 admin key /home/user/.ssh/id_rsa`}
          aria-label="Список узлов в формате IP:Port User AuthType [Password/KeyPath]"
        />
      </Form.Item>

      <Collapse
        defaultActiveKey={[]}
        className="margin-bottom-space-4"
        items={[
          {
            key: 'prometheus',
            label: 'Настройки Prometheus',
            children: (
              <>
                <Form.Item
                  name="prometheus_enabled"
                  label="Включить Prometheus"
                  valuePropName="checked"
                >
                  <Checkbox aria-label="Включить Prometheus" />
                </Form.Item>

                <Form.Item
                  name="prometheus_url"
                  label="URL Prometheus"
                >
                  <Input placeholder="http://prometheus.example.com:9090" aria-label="URL Prometheus" />
                </Form.Item>

                <Form.Item
                  name="prometheus_username"
                  label="Имя пользователя Prometheus"
                >
                  <Input aria-label="Имя пользователя Prometheus" />
                </Form.Item>

                <Form.Item
                  name="prometheus_password"
                  label="Пароль Prometheus"
                >
                  <Input type="password" aria-label="Пароль Prometheus" />
                </Form.Item>
              </>
            ),
          },
        ]}
      />

      <Form.Item
        name="kubeconfig"
        label="Kubeconfig"
        rules={isEditMode ? [] : [{ required: true, message: 'Введите kubeconfig' }]}
      >
        <Input.TextArea
          rows={8}
          placeholder="Вставьте содержимое kubeconfig файла"
          aria-label="Содержимое kubeconfig файла"
        />
      </Form.Item>

      <Form.Item>
        <Space>
          <Button type="primary" htmlType="submit" aria-label={isEditMode ? 'Обновить кластер' : 'Создать кластер'}>
            {isEditMode ? 'Обновить кластер' : 'Создать кластер'}
          </Button>
          <Button onClick={onTestNodes} aria-label="Проверить узлы">
            Проверить узлы
          </Button>
          <Button onClick={onTestKubeconfig} aria-label="Проверить kubeconfig">
            Проверить kubeconfig
          </Button>
        </Space>
      </Form.Item>
    </Form>
  );
};

export default ClusterForm;