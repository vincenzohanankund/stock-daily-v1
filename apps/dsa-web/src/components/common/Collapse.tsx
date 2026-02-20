import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';

interface CollapseProps {
  accordion?: boolean;
  defaultActiveKey?: string | string[];
  children: React.ReactNode;
  className?: string;
}

interface CollapseItemProps {
  header: React.ReactNode;
  name: string;
  children: React.ReactNode;
  isActive?: boolean;
  onClick?: () => void;
  className?: string;
}

const CollapseItem: React.FC<CollapseItemProps> = ({
  header,
  children,
  isActive,
  onClick,
  className = '',
}) => {
  return (
    <div className={`border-b border-border last:border-b-0 ${className}`}>
      <button
        type="button"
        className="flex w-full items-center justify-between py-4 font-medium transition-all hover:underline"
        onClick={onClick}
      >
        {header}
        <ChevronDown
          className={`h-4 w-4 shrink-0 transition-transform duration-200 ${
            isActive ? 'rotate-180' : ''
          }`}
        />
      </button>
      <div
        className={`overflow-hidden transition-all duration-300 ease-in-out ${
          isActive ? 'max-h-96 opacity-100 mb-4' : 'max-h-0 opacity-0'
        }`}
      >
        {children}
      </div>
    </div>
  );
};

export const Collapse = ({
  accordion,
  defaultActiveKey,
  children,
  className = '',
}: CollapseProps) => {
  const [activeKeys, setActiveKeys] = useState<string[]>(
    Array.isArray(defaultActiveKey)
      ? defaultActiveKey
      : defaultActiveKey
      ? [defaultActiveKey]
      : []
  );

  const handleItemClick = (key: string) => {
    if (accordion) {
      setActiveKeys(activeKeys.includes(key) ? [] : [key]);
    } else {
      setActiveKeys(
        activeKeys.includes(key)
          ? activeKeys.filter((k) => k !== key)
          : [...activeKeys, key]
      );
    }
  };

  return (
    <div className={`w-full ${className}`}>
      {React.Children.map(children, (child) => {
        if (!React.isValidElement(child)) return null;
        
        // @ts-ignore
        const key = child.props.name;
        const isActive = activeKeys.includes(key);

        return React.cloneElement(child as React.ReactElement<any>, {
          isActive,
          onClick: () => handleItemClick(key),
        });
      })}
    </div>
  );
};

// @ts-ignore
Collapse.Item = CollapseItem;
