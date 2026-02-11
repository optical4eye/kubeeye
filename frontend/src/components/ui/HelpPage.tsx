import React, { Suspense } from 'react';
import { Spin } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import ErrorBoundary from './ErrorBoundary';

/**
 * Props for HelpPage component
 */
export interface HelpPageProps {
  /** Translation key for the page title */
  titleKey: string;
  /** Translation key for the page subtitle */
  subtitleKey: string;
  /** Lazy-loaded tab component to display */
  TabComponent: React.LazyExoticComponent<React.ComponentType>;
}

/**
 * Generic help page component that displays a title, subtitle, and a lazy-loaded tab component.
 * Used to reduce code duplication across help pages.
 */
const HelpPage = ({ titleKey, subtitleKey, TabComponent }: HelpPageProps) => {
  const { t } = useTranslation();

  return (
    <div>
      <div className="page-title">
        <QuestionCircleOutlined className="help-icon-margin" aria-label="Help icon" />
        {t(titleKey)}
      </div>
      <div className="page-subtitle">{t(subtitleKey)}</div>
      <ErrorBoundary fallback={<div>{t('error.loadingTab')}</div>}>
        <Suspense fallback={<Spin />}>
          <TabComponent />
        </Suspense>
      </ErrorBoundary>
    </div>
  );
};

export default HelpPage;
