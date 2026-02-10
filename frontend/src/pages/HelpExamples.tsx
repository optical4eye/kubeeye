import React, { Suspense, lazy } from 'react';
import { Spin } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import ErrorBoundary from '../components/ui/ErrorBoundary';

const ExamplesTab = lazy(() => import('../components/ui/HelpTabs/ExamplesTab'));

const HelpExamples = () => {
  const { t } = useTranslation();

  return (
    <div>
      <div className="page-title">
        <QuestionCircleOutlined className="help-icon-margin" aria-label="Help icon" />
        {t('help.tabs.examples')}
      </div>
      <div className="page-subtitle">{t('help.examplesSubtitle')}</div>
      <ErrorBoundary fallback={<div>{t('error.loadingTab')}</div>}>
        <Suspense fallback={<Spin />}>
          <ExamplesTab />
        </Suspense>
      </ErrorBoundary>
    </div>
  );
};

export default HelpExamples;
