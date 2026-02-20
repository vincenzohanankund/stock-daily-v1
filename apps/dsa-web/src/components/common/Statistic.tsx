import React from 'react';

interface StatisticProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title' | 'prefix'> {
  title?: React.ReactNode;
  value?: string | number;
  prefix?: React.ReactNode;
  suffix?: React.ReactNode;
  precision?: number;
  valueStyle?: React.CSSProperties;
  valueClassName?: string;
}

export const Statistic: React.FC<StatisticProps> = ({
  className = '',
  title,
  value,
  prefix,
  suffix,
  precision,
  valueStyle,
  valueClassName = '',
  ...props
}) => {
  let displayValue = value;
  if (typeof value === 'number' && precision !== undefined) {
    displayValue = value.toFixed(precision);
  }

  return (
    <div className={`flex flex-col ${className}`} {...props}>
      {title && <div className="text-sm text-muted-foreground mb-1">{title}</div>}
      <div className="flex items-baseline">
        {prefix && <span className="mr-1 text-lg">{prefix}</span>}
        <span 
          className={`text-2xl font-semibold ${valueClassName}`} 
          style={valueStyle}
        >
          {displayValue}
        </span>
        {suffix && <span className="ml-1 text-lg">{suffix}</span>}
      </div>
    </div>
  );
};
