import React from 'react';
import { Badge } from '../common';
import { formatDateTime } from '../../utils/format';

interface HistoryBadgeProps {
  createdAt: string;
  className?: string;
}

/**
 * 历史报告标识组件
 * 显示"历史报告"标识和原始生成时间
 */
export const HistoryBadge: React.FC<HistoryBadgeProps> = ({
  createdAt,
  className = '',
}) => {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <Badge variant="history" glow size="md">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        历史报告
      </Badge>
      <span className="text-sm text-gray-400 flex items-center gap-1">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
        生成于 {formatDateTime(createdAt)}
      </span>
    </div>
  );
};
