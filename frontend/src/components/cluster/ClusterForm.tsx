import React, { useState } from 'react';
import { Form, Input, Button, Space, Modal, Tooltip, Table } from 'antd';
import { KeyOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { Secret } from '../../types';
import { getSecretTypeTag } from '../ui/statusUtils';

interface ClusterFormProps {
  form: any;
  onSubmit: (values: any) => void;
  onTestNodes: () => void;
  onTestKubeconfig: () => void;
  onGetNodesFromKubeconfig: () => void;
  isEditMode?: boolean;
}

const ClusterForm: React.FC<ClusterFormProps> = ({
  form,
  onSubmit,
  onTestNodes,
  onTestKubeconfig,
  onGetNodesFromKubeconfig,
  isEditMode = false,
}) => {
  const { t } = useTranslation();
  const [secretModalVisible, setSecretModalVisible] = useState<boolean>(false);
  const [secrets, setSecrets] = useState<Secret[]>([]);
  const [targetField, setTargetField] = useState<string | null>(null);

  const loadSecrets = async () => {
    try {
      const response = await axios.get('/api/secrets');
      setSecrets(response.data.secrets || []);
    } catch {
      // Failed to load secrets
    }
  };

  const openSecretModal = (fieldName: string) => {
    setTargetField(fieldName);
    loadSecrets();
    setSecretModalVisible(true);
  };

  const selectSecret = (secretName: string) => {
    const secretVariable = `\u0024\u007Bsecret:${secretName}\u007D`;
    const currentValue = form.getFieldValue(targetField) || '';
    form.setFieldValue(targetField, currentValue + secretVariable);
    setSecretModalVisible(false);
  };

  return (
    <>
      <Form
        form={form}
        layout="vertical"
        onFinish={onSubmit}
        aria-label={
          isEditMode
            ? t('clusters.clusterForm.updateCluster')
            : t('clusters.clusterForm.createCluster')
        }
      >
        <Form.Item
          name="name"
          label={t('clusters.clusterForm.clusterName')}
          rules={[{ required: true, message: t('clusters.clusterForm.clusterNameRequired') }]}
        >
          <Input
            placeholder={t('clusters.clusterForm.clusterNamePlaceholder')}
            aria-label={t('clusters.clusterForm.clusterName')}
          />
        </Form.Item>

        <Form.Item
          name="nodes_text"
          label={
            <Space>
              <span>{t('clusters.clusterForm.nodesList')}</span>
            </Space>
          }
          rules={[{ required: true, message: t('clusters.clusterForm.nodesRequired') }]}
        >
          <Input.TextArea
            rows={6}
            placeholder={t('clusters.clusterForm.nodesPlaceholder')}
            aria-label={t('clusters.clusterForm.nodesList')}
          />
        </Form.Item>

        <Form.Item>
          <Space wrap>
            <Button
              className="action-button"
              icon={<KeyOutlined />}
              onClick={() => openSecretModal('nodes_text')}
              aria-label={t('clusters.clusterForm.insertSecretNodes')}
            >
              {t('clusters.clusterForm.insertSecretNodes')}
            </Button>
            <Button
              className="action-button"
              onClick={onGetNodesFromKubeconfig}
              aria-label={t('clusters.clusterForm.getNodesFromK8s')}
            >
              {t('clusters.clusterForm.getNodesFromK8s')}
            </Button>
            <Button
              className="action-button"
              onClick={onTestNodes}
              aria-label={t('clusters.clusterForm.testNodes')}
            >
              {t('clusters.clusterForm.testNodes')}
            </Button>
          </Space>
        </Form.Item>

        <Form.Item
          name="kubeconfig"
          label={
            <Space>
              <span>{t('clusters.clusterForm.kubeconfig')}</span>
              <Tooltip title={t('clusters.clusterForm.kubeconfigTooltip')}>
                <InfoCircleOutlined style={{ color: 'var(--info-color)' }} />
              </Tooltip>
            </Space>
          }
          rules={
            isEditMode
              ? []
              : [{ required: true, message: t('clusters.clusterForm.kubeconfigRequired') }]
          }
        >
          <Input.TextArea
            rows={8}
            placeholder={t('clusters.clusterForm.kubeconfigPlaceholder')}
            aria-label={t('clusters.clusterForm.kubeconfig')}
          />
        </Form.Item>

        <Form.Item>
          <Space wrap>
            <Button
              className="action-button"
              icon={<KeyOutlined />}
              onClick={() => openSecretModal('kubeconfig')}
              aria-label={t('clusters.clusterForm.insertSecretKubeconfig')}
            >
              {t('clusters.clusterForm.insertSecretKubeconfig')}
            </Button>
            <Button
              className="action-button"
              onClick={onTestKubeconfig}
              aria-label={t('clusters.clusterForm.testKubeconfig')}
            >
              {t('clusters.clusterForm.testKubeconfig')}
            </Button>
          </Space>
        </Form.Item>

        <Form.Item>
          <Button
            className="action-button"
            type="primary"
            htmlType="submit"
            aria-label={
              isEditMode
                ? t('clusters.clusterForm.updateCluster')
                : t('clusters.clusterForm.createCluster')
            }
          >
            {isEditMode
              ? t('clusters.clusterForm.updateCluster')
              : t('clusters.clusterForm.createCluster')}
          </Button>
        </Form.Item>
      </Form>

      <Modal
        title={t('clusters.clusterForm.selectSecret')}
        open={secretModalVisible}
        onCancel={() => setSecretModalVisible(false)}
        footer={null}
        width={800}
      >
        <Table
          dataSource={secrets}
          rowKey="id"
          pagination={{ pageSize: 5 }}
          columns={[
            { title: t('clusters.clusterForm.id'), dataIndex: 'id', key: 'id', width: 80 },
            {
              title: t('clusters.clusterForm.name'),
              dataIndex: 'name',
              key: 'name',
            },
            {
              title: t('clusters.clusterForm.type'),
              dataIndex: 'secret_type',
              key: 'secret_type',
              render: type => getSecretTypeTag(type),
            },
            {
              title: t('clusters.clusterForm.description'),
              dataIndex: 'description',
              key: 'description',
              render: text => text || '-',
            },
            {
              title: t('clusters.clusterForm.select'),
              key: 'actions',
              render: (_, record) => (
                <Button
                  type="primary"
                  size="small"
                  className="action-button"
                  onClick={() => selectSecret(record.name)}
                  aria-label={`${t('clusters.clusterForm.select')} ${record.name}`}
                >
                  {t('clusters.clusterForm.select')}
                </Button>
              ),
            },
          ]}
          locale={{ emptyText: t('clusters.clusterForm.noSecrets') }}
        />
      </Modal>
    </>
  );
};

export default ClusterForm;
