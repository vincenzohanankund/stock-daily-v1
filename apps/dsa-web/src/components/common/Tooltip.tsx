import React from 'react';

interface TooltipProps {
  content: string | React.ReactNode;
  children: React.ReactNode;
  position?: 'top' | 'bottom' | 'left' | 'right';
  className?: string;
}

export const Tooltip: React.FC<TooltipProps> = ({
  content,
  children,
  position = 'top',
  className = '',
}) => {
  return (
    <div className="relative group inline-block">
      {children}
      <div
        className={`
          absolute z-50 px-3 py-1.5 text-xs font-medium text-primary-foreground bg-primary rounded-md shadow-md opacity-0 
          group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap
          ${position === 'top' ? 'bottom-full left-1/2 -translate-x-1/2 mb-2' : ''}
          ${position === 'bottom' ? 'top-full left-1/2 -translate-x-1/2 mt-2' : ''}
          ${position === 'left' ? 'right-full top-1/2 -translate-y-1/2 mr-2' : ''}
          ${position === 'right' ? 'left-full top-1/2 -translate-y-1/2 ml-2' : ''}
          ${className}
        `}
      >
        {content}
      </div>
    </div>
  );
};

export default Tooltip;
