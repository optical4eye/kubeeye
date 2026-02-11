import React, { lazy } from 'react';
import HelpPage from '../components/ui/HelpPage';

const IntroductionTab = lazy(() => import('../components/ui/HelpTabs/IntroductionTab'));

const HelpIntroduction = () => {
  return (
    <HelpPage
      titleKey="help.tabs.tools"
      subtitleKey="help.toolsSubtitle"
      TabComponent={IntroductionTab}
    />
  );
};

export default HelpIntroduction;
