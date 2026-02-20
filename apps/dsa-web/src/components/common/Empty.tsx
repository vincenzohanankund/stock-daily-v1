import React from 'react';
import { Inbox } from 'lucide-react';

interface EmptyProps extends React.HTMLAttributes<HTMLDivElement> {
  description?: React.ReactNode;
}

export const Empty: React.FC<EmptyProps> = ({
  className = '',
  description = 'No Data',
  children,
  ...props
}) => {
  return (
    <div className={`flex flex-col items-center justify-center p-8 text-center ${className}`} {...props}>
      <div className="mb-4 text-muted-foreground">
         <Inbox size={48} strokeWidth={1} />
      </div>
      <div className="text-sm text-muted-foreground font-medium">{description}</div>
      {children && <div className="mt-4">{children}</div>}
    </div>
  );
};
