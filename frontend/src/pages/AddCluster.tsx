import React from 'react';
import { useTranslation } from 'react-i18next';
import { useClusterForm } from '../hooks/useClusterForm';
import { useClusters } from '../hooks/useClusters';
import { ClusterForm } from '../components/cluster';
import { Form, Card } from 'antd';
import { ClusterFormValues } from '../types/cluster';

const AddCluster = () => {
  const { t } = useTranslation();
  const [createForm] = Form.useForm();

  const { handleCreateCluster } = useClusters();
  const { handleTestNodes, handleTestKubeconfig, handleGetNodesFromKubeconfig } =
    useClusterForm(null);

  const onCreateSubmit = (values: ClusterFormValues) => {
    handleCreateCluster(values);
  };

  return (
    <div>
      <div className="page-title">{t('clusters.add')}</div>
      <div className="page-subtitle">{t('clusters.addSubtitle')}</div>
      <Card>
        <ClusterForm
          form={createForm}
          onSubmit={onCreateSubmit}
          onTestNodes={() => handleTestNodes(null, createForm)}
          onTestKubeconfig={() => handleTestKubeconfig(null, createForm)}
          onGetNodesFromKubeconfig={() => handleGetNodesFromKubeconfig(null, createForm)}
          isEditMode={false}
        />
      </Card>
    </div>
  );
};

export default AddCluster;
