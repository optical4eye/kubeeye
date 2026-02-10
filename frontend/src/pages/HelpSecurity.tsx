import React, { Suspense, lazy } from 'react';
import { Spin } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import ErrorBoundary from '../components/ui/ErrorBoundary';

const SecurityTab = lazy(() => import('../components/ui/HelpTabs/SecurityTab'));

const HelpSecurity = () => {
  const { t } = useTranslation();

  return (
    <div>
      <div className="page-title">
        <QuestionCircleOutlined className="help-icon-margin" aria-label="Help icon" />
        {t('help.tabs.security')}
      </div>
      <div className="page-subtitle">{t('help.securitySubtitle')}</div>
      <ErrorBoundary fallback={<div>{t('error.loadingTab')}</div>}>
        <Suspense fallback={<Spin />}>
          <SecurityTab />
        </Suspense>
      </ErrorBoundary>
    </div>
  );
};

export default HelpSecurity;
