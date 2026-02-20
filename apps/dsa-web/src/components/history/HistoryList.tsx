import React from 'react';
import { Spinner } from '../common/Spinner';
import { Empty } from '../common/Empty';
import { Badge } from '../common/Badge';
import type { HistoryItem } from '../../types/analysis';
import { formatDateTime } from '../../utils/format';
import { getSentimentClass } from '../../types/analysis';

interface HistoryListProps {
  items: HistoryItem[];
  isLoading: boolean;
  isLoadingMore: boolean;
  hasMore: boolean;
  selectedQueryId?: string;
  onItemClick: (queryId: string) => void;
  onLoadMore: () => void;
  className?: string;
}

export const HistoryList: React.FC<HistoryListProps> = ({
  items,
  isLoading,
  isLoadingMore,
  hasMore,
  selectedQueryId,
  onItemClick,
  onLoadMore,
  className = '',
}) => {
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, clientHeight, scrollHeight } = e.currentTarget;
    if (scrollHeight - scrollTop <= clientHeight + 50) {
      if (hasMore && !isLoadingMore) {
        onLoadMore();
      }
    }
  };

  return (
    <div className={`h-full overflow-hidden flex flex-col ${className}`}>
        {isLoading && items.length === 0 ? (
            <div className="flex justify-center items-center h-full">
                <Spinner />
            </div>
        ) : items.length === 0 ? (
            <div className="flex justify-center items-center h-full">
                <Empty description="暂无历史记录" />
            </div>
        ) : (
            <div 
                className="overflow-auto flex-1 divide-y divide-border"
                onScroll={handleScroll}
            >
                {items.map((item) => {
                    const sentimentClass = item.sentimentScore !== undefined ? getSentimentClass(item.sentimentScore) : 'bg-muted-foreground';
                    const isSelected = selectedQueryId === item.queryId;

                    return (
                        <div
                            key={item.queryId}
                            className={`
                                cursor-pointer p-4 transition-colors hover:bg-accent hover:text-accent-foreground
                                ${isSelected ? 'bg-accent text-accent-foreground' : 'bg-transparent'}
                            `}
                            onClick={() => onItemClick(item.queryId)}
                        >
                            <div className="flex justify-between items-center mb-1">
                                <span className="font-semibold text-base">
                                    {item.stockName || item.stockCode}
                                </span>
                                {item.sentimentScore !== undefined && (
                                    <div 
                                        className={`w-2 h-2 rounded-full shadow-[0_0_4px] ${sentimentClass}`}
                                        title={`情绪值: ${item.sentimentScore}`} 
                                    />
                                )}
                            </div>
                            <div className="flex justify-between items-center text-xs text-muted-foreground">
                                <div className="flex items-center gap-2">
                                    <span>{item.stockCode}</span>
                                    {item.reportType === 'detailed' && (
                                        <Badge variant="secondary" className="text-[10px] px-1 py-0 h-4">详细报告</Badge>
                                    )}
                                </div>
                                <span>{formatDateTime(item.createdAt)}</span>
                            </div>
                        </div>
                    );
                })}
                {isLoadingMore && (
                    <div className="text-center p-2">
                        <Spinner size="sm" />
                    </div>
                )}
            </div>
        )}
    </div>
  );
};
