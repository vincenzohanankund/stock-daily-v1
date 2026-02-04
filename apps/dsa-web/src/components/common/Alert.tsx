import React from 'react';
import { Button } from './Button';

interface AlertProps {
  title: string;
  description?: string;
  variant?: 'error' | 'success' | 'info' | 'warning';
  onRetry?: () => void;
  className?: string;
}

export const Alert: React.FC<AlertProps> = ({
  title,
  description,
  variant = 'info',
  onRetry,
  className = '',
}) => {
  const variants = {
    error: 'border-rose-200/70 text-rose-700 bg-rose-50/80',
    success: 'border-emerald-200/70 text-emerald-700 bg-emerald-50/80',
    info: 'border-sky-200/70 text-sky-700 bg-sky-50/80',
    warning: 'border-amber-200/70 text-amber-700 bg-amber-50/80',
  };

  return (
    <div
      role="alert"
      aria-live="polite"
      className={`rounded-2xl border px-4 py-3 text-sm shadow-sm ${variants[variant]} ${className}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold">{title}</p>
          {description && <p className="mt-1 text-sm opacity-80">{description}</p>}
        </div>
        {onRetry && (
          <Button variant="ghost" className="text-xs" onClick={onRetry}>
            重试
          </Button>
        )}
      </div>
    </div>
  );
};
