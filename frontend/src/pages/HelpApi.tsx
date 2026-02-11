import React, { lazy } from 'react';
import HelpPage from '../components/ui/HelpPage';

const ApiTab = lazy(() => import('../components/ui/HelpTabs/ApiTab'));

const HelpApi = () => {
  return <HelpPage titleKey="help.tabs.api" subtitleKey="help.apiSubtitle" TabComponent={ApiTab} />;
};

export default HelpApi;
