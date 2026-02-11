import React, { lazy } from 'react';
import HelpPage from '../components/ui/HelpPage';

const KubeconfigTab = lazy(() => import('../components/ui/HelpTabs/KubeconfigTab'));

const HelpKubeconfig = () => {
  return (
    <HelpPage
      titleKey="help.tabs.kubeconfig"
      subtitleKey="help.kubeconfigSubtitle"
      TabComponent={KubeconfigTab}
    />
  );
};

export default HelpKubeconfig;
