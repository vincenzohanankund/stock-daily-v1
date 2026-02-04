import React from 'react';
import type { InputHTMLAttributes } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  className = '',
  id,
  ...props
}) => {
  const errorId = error && id ? `${id}-error` : undefined;

  return (
    <div className="flex flex-col gap-1.5 w-full">
      {label && (
        <label htmlFor={id} className="text-xs font-semibold text-slate-600/90 tracking-wide ml-1">
          {label}
        </label>
      )}
      <input
        id={id}
        className={`
          glass-input px-4 py-2.5 rounded-2xl text-slate-800 placeholder-slate-400
          ${error ? 'border-rose-300 focus:border-rose-400 focus:ring-rose-100' : ''}
          ${className}
        `}
        aria-invalid={Boolean(error)}
        aria-describedby={errorId}
        {...props}
      />
      {error && (
        <span id={errorId} className="text-xs text-rose-500 ml-1">
          {error}
        </span>
      )}
    </div>
  );
};
