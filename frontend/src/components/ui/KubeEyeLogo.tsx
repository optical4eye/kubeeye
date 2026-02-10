import React from 'react';

interface KubeEyeLogoProps {
  size?: number;
  className?: string;
}

// Custom KubeEye SVG Logo
const KubeEyeLogo: React.FC<KubeEyeLogoProps> = ({ size = 80, className }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 100 100"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
  >
    {/* Outer circle */}
    <circle cx="50" cy="50" r="45" stroke="currentColor" strokeWidth="3" fill="none" opacity="0.2"/>
    {/* Inner hexagon */}
    <path d="M50 10 L85 30 L85 70 L50 90 L15 70 L15 30 Z" stroke="currentColor" strokeWidth="2" fill="none"/>
    {/* Eye shape */}
    <ellipse cx="50" cy="50" rx="20" ry="12" stroke="currentColor" strokeWidth="2" fill="none"/>
    {/* Pupil */}
    <circle cx="50" cy="50" r="6" fill="currentColor"/>
    {/* Kubernetes nodes */}
    <circle cx="30" cy="30" r="4" fill="currentColor" opacity="0.6"/>
    <circle cx="70" cy="30" r="4" fill="currentColor" opacity="0.6"/>
    <circle cx="30" cy="70" r="4" fill="currentColor" opacity="0.6"/>
    <circle cx="70" cy="70" r="4" fill="currentColor" opacity="0.6"/>
  </svg>
);

export default KubeEyeLogo;
