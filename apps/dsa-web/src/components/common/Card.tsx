import React from 'react';

interface CardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  title?: React.ReactNode;
  extra?: React.ReactNode;
  bordered?: boolean;
  actions?: React.ReactNode[];
}

export const Card: React.FC<CardProps> = ({
  className = '',
  title,
  extra,
  children,
  bordered = true,
  actions,
  ...props
}) => {
  return (
    <div
      className={`bg-card text-card-foreground rounded-lg shadow-sm ${
        bordered ? 'border border-border' : ''
      } ${className}`}
      {...props}
    >
      {(title || extra) && (
        <div className="flex flex-col space-y-1.5 p-6 pb-2">
          <div className="flex items-center justify-between">
            {title && <div className="font-semibold leading-none tracking-tight">{title}</div>}
            {extra && <div className="text-sm text-muted-foreground">{extra}</div>}
          </div>
        </div>
      )}
      <div className="p-6 pt-2">{children}</div>
      {actions && (
        <div className="flex items-center justify-end gap-2 p-4 border-t border-border bg-muted/20 rounded-b-lg">
          {actions.map((action, index) => (
            <React.Fragment key={index}>{action}</React.Fragment>
          ))}
        </div>
      )}
    </div>
  );
};

export default Card;
