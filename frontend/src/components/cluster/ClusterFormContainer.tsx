import React from 'react';
import { Card } from 'antd';
import ClusterForm from './ClusterForm';
import { ClusterFormValues } from '../types/cluster';

interface ClusterFormContainerProps {
  form: any;
  onSubmit: (values: ClusterFormValues) => void;
  onTestNodes: () => void;
  onTestKubeconfig: () => void;
  onGetNodesFromKubeconfig: () => void;
  isEditMode: boolean;
}

const ClusterFormContainer: React.FC<ClusterFormContainerProps> = React.memo(
  ({ form, onSubmit, onTestNodes, onTestKubeconfig, onGetNodesFromKubeconfig, isEditMode }) => {
    return (
      <Card>
        <ClusterForm
          form={form}
          onSubmit={onSubmit}
          onTestNodes={onTestNodes}
          onTestKubeconfig={onTestKubeconfig}
          onGetNodesFromKubeconfig={onGetNodesFromKubeconfig}
          isEditMode={isEditMode}
        />
      </Card>
    );
  }
);

ClusterFormContainer.displayName = 'ClusterFormContainer';

export default ClusterFormContainer;
