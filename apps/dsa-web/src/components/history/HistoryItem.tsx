import type React from 'react';
import type { HistoryItem as HistoryItemType } from '../../types/analysis';
import { formatDateTime } from '../../utils/format';
import { getSentimentColor } from '../../types/analysis';

interface HistoryItemProps {
  item: HistoryItemType;
  onClick: () => void;
}

/**
 * 单条历史记录卡片 - 终端风格
 */
export const HistoryItem: React.FC<HistoryItemProps> = ({
  item,
  onClick,
}) => {
  const scoreColor = item.sentimentScore !== undefined 
    ? getSentimentColor(item.sentimentScore)
    : undefined;

  return (
    <button
      type="button"
      onClick={onClick}
      className="list-item w-full text-left group"
    >
      {/* 左侧色条 */}
      {scoreColor && (
        <div
          className="w-1 h-12 rounded-full mr-4 flex-shrink-0"
          style={{ backgroundColor: scoreColor }}
        />
      )}

      {/* 股票信息 */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3 mb-1">
          <span className="text-white font-medium group-hover:text-cyan transition-colors truncate">
            {item.stockName || item.stockCode}
          </span>
          <span className="text-xs font-mono text-muted bg-elevated px-2 py-0.5 rounded">
            {item.stockCode}
          </span>
        </div>
        
        {item.operationAdvice && (
          <p className="text-sm text-secondary line-clamp-1">
            {item.operationAdvice}
          </p>
        )}
      </div>

      {/* 情绪分数 */}
      {item.sentimentScore !== undefined && (
        <div className="flex-shrink-0 mx-4">
          <span
            className="text-2xl font-bold font-mono"
            style={{ color: scoreColor }}
          >
            {item.sentimentScore}
          </span>
        </div>
      )}

      {/* 时间 */}
      <div className="flex-shrink-0 text-right">
        <span className="text-xs text-muted">
          {formatDateTime(item.createdAt)}
        </span>
      </div>

      {/* 箭头 */}
      <svg
        className="w-5 h-5 ml-4 text-muted group-hover:text-cyan group-hover:translate-x-1 transition-all flex-shrink-0"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
      </svg>
    </button>
  );
};
