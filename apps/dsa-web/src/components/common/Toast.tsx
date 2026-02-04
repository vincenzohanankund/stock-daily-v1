import React from 'react';

interface ToastProps {
  message: string;
  variant?: 'error' | 'success' | 'info' | 'warning';
  className?: string;
}

export const Toast: React.FC<ToastProps> = ({
  message,
  variant = 'info',
  className = '',
}) => {
  const variants = {
    error: 'border-rose-200/70 text-rose-700 bg-rose-50/90',
    success: 'border-emerald-200/70 text-emerald-700 bg-emerald-50/90',
    info: 'border-sky-200/70 text-sky-700 bg-sky-50/90',
    warning: 'border-amber-200/70 text-amber-700 bg-amber-50/90',
  };

  return (
    <div
      role="status"
      aria-live="polite"
      className={`rounded-full border px-4 py-2 text-xs shadow-sm backdrop-blur ${variants[variant]} ${className}`}
    >
      {message}
    </div>
  );
};
