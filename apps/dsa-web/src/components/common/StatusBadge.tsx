import React from 'react';

interface StatusBadgeProps {
  label: string;
  type?: 'success' | 'warning' | 'error' | 'neutral' | 'info';
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ 
  label, 
  type = 'neutral',
  className = ''
}) => {
  const styles = {
    success: 'bg-emerald-500/15 text-emerald-700 border-emerald-200/60',
    warning: 'bg-amber-500/15 text-amber-700 border-amber-200/60',
    error: 'bg-rose-500/15 text-rose-700 border-rose-200/60',
    info: 'bg-sky-500/15 text-sky-700 border-sky-200/60',
    neutral: 'bg-slate-200/70 text-slate-600 border-slate-200/60',
  };

  return (
    <span 
      className={`
        inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border
        ${styles[type]}
        ${className}
      `}
    >
      {label}
    </span>
  );
};
