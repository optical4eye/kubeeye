import React from 'react';
import { useTranslation } from 'react-i18next';
import { useClusterForm } from '../hooks/useClusterForm';
import { ClusterFormContainer } from '../components/cluster';
import { Form } from 'antd';
import { ClusterFormValues } from '../types/cluster';

const AddCluster = () => {
  const { t } = useTranslation();
  const [createForm] = Form.useForm();

  const { handleTestNodes, handleTestKubeconfig, handleGetNodesFromKubeconfig } =
    useClusterForm(null);

  const onCreateSubmit = (values: ClusterFormValues) => {
    // This will be handled by the parent component or a hook
    console.log('Creating cluster:', values);
  };

  return (
    <div>
      <div className="page-title">{t('clusters.add')}</div>
      <div className="page-subtitle">{t('clusters.addSubtitle')}</div>
      <ClusterFormContainer
        form={createForm}
        onSubmit={onCreateSubmit}
        onTestNodes={() => handleTestNodes(null, createForm)}
        onTestKubeconfig={() => handleTestKubeconfig(null, createForm)}
        onGetNodesFromKubeconfig={() => handleGetNodesFromKubeconfig(null, createForm)}
        isEditMode={false}
      />
    </div>
  );
};

export default AddCluster;
