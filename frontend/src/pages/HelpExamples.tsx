import React, { lazy } from 'react';
import HelpPage from '../components/ui/HelpPage';

const ExamplesTab = lazy(() => import('../components/ui/HelpTabs/ExamplesTab'));

const HelpExamples = () => {
  return (
    <HelpPage
      titleKey="help.tabs.examples"
      subtitleKey="help.examplesSubtitle"
      TabComponent={ExamplesTab}
    />
  );
};

export default HelpExamples;
