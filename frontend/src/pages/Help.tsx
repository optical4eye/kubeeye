import React, { Suspense, lazy } from 'react';
import { Tabs, Spin } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import ErrorBoundary from '../components/ui/ErrorBoundary';

const IntroductionTab = lazy(() => import('../components/ui/HelpTabs/IntroductionTab'));
const ExamplesTab = lazy(() => import('../components/ui/HelpTabs/ExamplesTab'));
const SecurityTab = lazy(() => import('../components/ui/HelpTabs/SecurityTab'));
const KubeconfigTab = lazy(() => import('../components/ui/HelpTabs/KubeconfigTab'));
const ApiTab = lazy(() => import('../components/ui/HelpTabs/ApiTab'));

const Help = () => {
  const { t } = useTranslation();

  const items = [
    {
      key: '1',
      label: t('help.tabs.tools'),
      'aria-label': t('help.tabs.tools'),
      children: (
        <ErrorBoundary fallback={<div>{t('error.loadingTab')}</div>}>
          <Suspense fallback={<Spin />}>
            <IntroductionTab />
          </Suspense>
        </ErrorBoundary>
      ),
    },
    {
      key: '2',
      label: t('help.tabs.examples'),
      'aria-label': t('help.tabs.examples'),
      children: (
        <ErrorBoundary fallback={<div>{t('error.loadingTab')}</div>}>
          <Suspense fallback={<Spin />}>
            <ExamplesTab />
          </Suspense>
        </ErrorBoundary>
      ),
    },
    {
      key: '3',
      label: t('help.tabs.security'),
      'aria-label': t('help.tabs.security'),
      children: (
        <ErrorBoundary fallback={<div>{t('error.loadingTab')}</div>}>
          <Suspense fallback={<Spin />}>
            <SecurityTab />
          </Suspense>
        </ErrorBoundary>
      ),
    },
    {
      key: '4',
      label: t('help.tabs.kubeconfig'),
      'aria-label': t('help.tabs.kubeconfig'),
      children: (
        <ErrorBoundary fallback={<div>{t('error.loadingTab')}</div>}>
          <Suspense fallback={<Spin />}>
            <KubeconfigTab />
          </Suspense>
        </ErrorBoundary>
      ),
    },
    {
      key: '5',
      label: t('help.tabs.api'),
      'aria-label': t('help.tabs.api'),
      children: (
        <ErrorBoundary fallback={<div>{t('error.loadingTab')}</div>}>
          <Suspense fallback={<Spin />}>
            <ApiTab />
          </Suspense>
        </ErrorBoundary>
      ),
    },
  ];

  return (
    <div>
      <div className="page-title">
        <QuestionCircleOutlined className="help-icon-margin" aria-label="Help icon" />
        {t('help.title')}
      </div>
      <div className="page-subtitle">{t('help.subtitle')}</div>

      <Tabs defaultActiveKey="1" aria-label={t('help.sectionsAria')} items={items} />
    </div>
  );
};

export default Help;
