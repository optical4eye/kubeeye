import React, { Suspense, lazy } from 'react';
import { Spin } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import ErrorBoundary from '../components/ui/ErrorBoundary';

const KubeconfigTab = lazy(() => import('../components/ui/HelpTabs/KubeconfigTab'));

const HelpKubeconfig = () => {
  const { t } = useTranslation();

  return (
    <div>
      <div className="page-title">
        <QuestionCircleOutlined className="help-icon-margin" aria-label="Help icon" />
        {t('help.tabs.kubeconfig')}
      </div>
      <div className="page-subtitle">{t('help.kubeconfigSubtitle')}</div>
      <ErrorBoundary fallback={<div>{t('error.loadingTab')}</div>}>
        <Suspense fallback={<Spin />}>
          <KubeconfigTab />
        </Suspense>
      </ErrorBoundary>
    </div>
  );
};

export default HelpKubeconfig;
