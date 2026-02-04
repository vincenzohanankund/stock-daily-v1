import React from 'react';
import type { ReactNode } from 'react';

interface SpectralBackgroundProps {
  children?: ReactNode;
  className?: string;
}

export const SpectralBackground: React.FC<SpectralBackgroundProps> = ({ children, className = '' }) => {
  return (
    <div className={`relative min-h-screen w-full overflow-x-hidden bg-[rgb(var(--bg-ambient))] ${className}`}>
      <div className="pointer-events-none absolute inset-0">
        <div className="spectral-orb spectral-orb--one" aria-hidden="true" />
        <div className="spectral-orb spectral-orb--two" aria-hidden="true" />
        <div className="spectral-orb spectral-orb--three" aria-hidden="true" />
        <div className="spectral-conic" aria-hidden="true" />
        <div className="spectral-fog" aria-hidden="true" />
        <div className="spectral-grain" aria-hidden="true" />
      </div>

      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
};
