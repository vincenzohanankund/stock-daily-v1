import React, { useState, useEffect, useCallback } from 'react';
import { Card } from '../common/Card';
import Button from '../common/Button';
import { Empty } from '../common/Empty';
import { RefreshCw } from 'lucide-react';
import { historyApi } from '../../api/history';
import type { NewsIntelItem } from '../../types/analysis';

interface ReportNewsProps {
  queryId?: string;
  limit?: number;
}

export const ReportNews: React.FC<ReportNewsProps> = ({ queryId, limit = 20 }) => {
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<NewsIntelItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const fetchNews = useCallback(async () => {
    if (!queryId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await historyApi.getNews(queryId, limit);
      if (Array.isArray(response)) {
          setItems(response);
      } else if (response && response.items) {
          setItems(response.items);
      } else {
          setItems([]);
      }
    } catch (err: any) {
      setError(err.message || '加载资讯失败');
    } finally {
      setLoading(false);
    }
  }, [queryId, limit]);

  useEffect(() => {
    if (queryId) {
      fetchNews();
    } else {
        setItems([]);
    }
  }, [queryId, fetchNews]);

  if (!queryId) return null;

  return (
    <Card
      title="相关资讯"
      extra={
        <Button 
            variant="ghost" 
            size="sm" 
            onClick={fetchNews} 
            loading={loading}
            className="h-8 w-8 p-0"
        >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
        </Button>
      }
      className="mb-4"
    >
      {loading && items.length === 0 ? (
          <div className="flex justify-center py-8">
              <RefreshCw className="animate-spin text-muted-foreground" />
          </div>
      ) : error ? (
          <div className="text-red-500 text-center py-4">{error}</div>
      ) : items.length === 0 ? (
          <Empty description="暂无相关资讯" />
      ) : (
          <div className="divide-y divide-border">
            {items.map((item, index) => (
                <div key={index} className="py-3 first:pt-0 last:pb-0">
                    <div className="flex flex-col gap-1">
                        <a 
                            href={item.url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-sm font-medium hover:underline text-primary truncate block"
                        >
                            {item.title}
                        </a>
                        <p className="text-xs text-muted-foreground line-clamp-2 m-0">
                            {item.snippet}
                        </p>
                    </div>
                </div>
            ))}
          </div>
      )}
    </Card>
  );
};
