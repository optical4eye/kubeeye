import React from 'react';

interface VersionDisplayProps {
  version: string;
}

const VersionDisplay: React.FC<VersionDisplayProps> = ({ version }) => {
  return (
    <div className="kube-text-center kube-margin-top-0 kube-font-size-12 kube-text-secondary kube-opacity-70">
      ver. {version}
    </div>
  );
};

export default VersionDisplay;
