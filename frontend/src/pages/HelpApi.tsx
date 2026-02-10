import React, { Suspense, lazy } from 'react';
import { Spin } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import ErrorBoundary from '../components/ui/ErrorBoundary';

const ApiTab = lazy(() => import('../components/ui/HelpTabs/ApiTab'));

const HelpApi = () => {
  const { t } = useTranslation();

  return (
    <div>
      <div className="page-title">
        <QuestionCircleOutlined className="help-icon-margin" aria-label="Help icon" />
        {t('help.tabs.api')}
      </div>
      <div className="page-subtitle">{t('help.apiSubtitle')}</div>
      <ErrorBoundary fallback={<div>{t('error.loadingTab')}</div>}>
        <Suspense fallback={<Spin />}>
          <ApiTab />
        </Suspense>
      </ErrorBoundary>
    </div>
  );
};

export default HelpApi;
