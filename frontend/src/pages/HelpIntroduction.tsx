import React, { Suspense, lazy } from 'react';
import { Spin } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import ErrorBoundary from '../components/ui/ErrorBoundary';

const IntroductionTab = lazy(() => import('../components/ui/HelpTabs/IntroductionTab'));

const HelpIntroduction = () => {
  const { t } = useTranslation();

  return (
    <div>
      <div className="page-title">
        <QuestionCircleOutlined className="help-icon-margin" aria-label="Help icon" />
        {t('help.tabs.tools')}
      </div>
      <div className="page-subtitle">{t('help.toolsSubtitle')}</div>
      <ErrorBoundary fallback={<div>{t('error.loadingTab')}</div>}>
        <Suspense fallback={<Spin />}>
          <IntroductionTab />
        </Suspense>
      </ErrorBoundary>
    </div>
  );
};

export default HelpIntroduction;
