import React, { Suspense, lazy } from 'react';
import { Tabs, Spin } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const IntroductionTab = lazy(() => import('../components/ui/HelpTabs/IntroductionTab'));
const ExamplesTab = lazy(() => import('../components/ui/HelpTabs/ExamplesTab'));
const SecurityTab = lazy(() => import('../components/ui/HelpTabs/SecurityTab'));
const KubeconfigTab = lazy(() => import('../components/ui/HelpTabs/KubeconfigTab'));
const ApiTab = lazy(() => import('../components/ui/HelpTabs/ApiTab'));

const Help = () => {
  const { t } = useTranslation();
  return (
    <div>
      <div className="page-title">
        <QuestionCircleOutlined className="help-icon-margin" aria-label="Help icon" />
        {t('help.title')}
      </div>
      <div className="page-subtitle">{t('help.subtitle')}</div>

      <Tabs defaultActiveKey="1" aria-label={t('help.sectionsAria')}>
        <Tabs.TabPane tab={t('help.tabs.tools')} key="1" aria-label={t('help.tabs.tools')}>
          <Suspense fallback={<Spin />}>
            <IntroductionTab />
          </Suspense>
        </Tabs.TabPane>

        <Tabs.TabPane tab={t('help.tabs.examples')} key="2" aria-label={t('help.tabs.examples')}>
          <Suspense fallback={<Spin />}>
            <ExamplesTab />
          </Suspense>
        </Tabs.TabPane>

        <Tabs.TabPane tab={t('help.tabs.security')} key="3" aria-label={t('help.tabs.security')}>
          <Suspense fallback={<Spin />}>
            <SecurityTab />
          </Suspense>
        </Tabs.TabPane>

        <Tabs.TabPane
          tab={t('help.tabs.kubeconfig')}
          key="4"
          aria-label={t('help.tabs.kubeconfig')}
        >
          <Suspense fallback={<Spin />}>
            <KubeconfigTab />
          </Suspense>
        </Tabs.TabPane>

        <Tabs.TabPane tab={t('help.tabs.api')} key="5" aria-label={t('help.tabs.api')}>
          <Suspense fallback={<Spin />}>
            <ApiTab />
          </Suspense>
        </Tabs.TabPane>
      </Tabs>
    </div>
  );
};

export default Help;
