import type React from 'react';
import { useState } from 'react';
import { Card } from '../common';

interface ReportNewsProps {
  newsContent?: string;
}

/**
 * 资讯区组件 - 终端风格
 */
export const ReportNews: React.FC<ReportNewsProps> = ({ newsContent }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!newsContent) {
    return null;
  }

  return (
    <Card variant="bordered" padding="md">
      <div className="flex items-center justify-between mb-3">
        <div>
          <span className="label-uppercase">NEWS FEED</span>
          <h3 className="text-base font-semibold text-white mt-0.5">相关资讯</h3>
        </div>
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-xs text-cyan hover:text-white transition-colors flex items-center gap-1"
        >
          {isExpanded ? '收起' : '展开'}
          <svg
            className={`w-3.5 h-3.5 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      <div
        className={`overflow-hidden transition-all duration-300 ${
          isExpanded ? 'max-h-[2000px]' : 'max-h-24'
        }`}
      >
        <div className="text-secondary text-sm leading-relaxed whitespace-pre-wrap text-left">
          {newsContent}
        </div>
      </div>

      {!isExpanded && newsContent.length > 200 && (
        <div className="mt-2 pt-2 border-t border-white/5">
          <button
            type="button"
            onClick={() => setIsExpanded(true)}
            className="text-xs text-cyan hover:text-white transition-colors"
          >
            查看更多...
          </button>
        </div>
      )}
    </Card>
  );
};
