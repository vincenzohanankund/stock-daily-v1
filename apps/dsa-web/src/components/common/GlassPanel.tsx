import React from 'react';
import type { ReactNode } from 'react';

interface GlassPanelProps {
  children: ReactNode;
  className?: string;
  interactive?: boolean;
  variant?: 'standard' | 'shine' | 'dark';
}

export const GlassPanel: React.FC<GlassPanelProps> = ({ 
  children, 
  className = '', 
  interactive = false,
  variant = 'standard'
}) => {
  const baseClasses = "glass-panel relative overflow-hidden transition-all duration-500";
  
  const variants = {
    standard: "",
    shine: "glass-panel--shine",
    dark: "glass-panel--dark",
  };

  const interactiveClasses = interactive
    ? "cursor-pointer hover:-translate-y-1 hover:shadow-2xl hover:border-white/80 group"
    : "";

  return (
    <div 
      className={`
        ${baseClasses} 
        ${variants[variant]} 
        ${interactiveClasses} 
        ${className}
      `}
      >
      <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-white/80 to-transparent opacity-60" />

      {children}
    </div>
  );
};
