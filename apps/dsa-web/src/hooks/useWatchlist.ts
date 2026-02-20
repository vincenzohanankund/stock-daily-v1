import { useState, useEffect, useCallback } from 'react';
import { useToast } from '../components/common/Toast';
import { stocksApi } from '../api/stocks';
import type { WatchlistItem } from '../types/analysis';

export function useWatchlist() {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSyncingPrices, setIsSyncingPrices] = useState(false);
  const toast = useToast();

  const refreshWatchlist = useCallback(async (silent = false) => {
    setIsLoading(true);
    try {
      // 1. First fetch with async mode to get cache + trigger task
      const response = await stocksApi.getWatchlist(true, true);
      setWatchlist(response.items || []);
      
      // 2. If there is a refresh task running/started
      if (response.refreshTask && !response.refreshTask.completed) {
        if (!silent) toast.info('正在同步实时价格...');
        setIsSyncingPrices(true);
        
        const taskId = response.refreshTask.taskId;
        
        // 3. Poll for status
        const pollInterval = setInterval(async () => {
          try {
            const status = await stocksApi.getRefreshStatus(taskId);
            
            if (status.completed) {
              clearInterval(pollInterval);
              setIsSyncingPrices(false);
              if (!silent) toast.success('实时价格同步完成');
              
              // 4. Fetch final data
              const finalResponse = await stocksApi.getWatchlist(true, false);
              setWatchlist(finalResponse.items || []);
            } else if (status.status === 'failed' || status.status === 'not_found') {
              clearInterval(pollInterval);
              setIsSyncingPrices(false);
              console.error('Price sync failed:', status.error);
            }
          } catch (e) {
            console.error('Polling error', e);
            clearInterval(pollInterval);
            setIsSyncingPrices(false);
          }
        }, 3000);

        // Safety timeout (e.g. 60s)
        setTimeout(() => {
            clearInterval(pollInterval);
            if (isSyncingPrices) setIsSyncingPrices(false);
        }, 60000);
      }
    } catch (e) {
      console.error('Failed to load watchlist', e);
      if (!silent) {
        toast.error('加载自选股失败');
      }
    } finally {
      setIsLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    // Initial load
    void refreshWatchlist(true);
  }, []); // Remove refreshWatchlist from deps to avoid loop if it changes

  const addStock = useCallback(async (code: string): Promise<boolean> => {
    try {
      const response = await stocksApi.addWatchlistStock(code);
      if (response.added === false) {
        toast.warning('该股票已在自选列表中');
        return false;
      }
      toast.success('添加成功');
      await refreshWatchlist(true);
      return true;
    } catch (e) {
      console.error('Failed to add watchlist stock', e);
      toast.error('添加失败，请稍后重试');
      return false;
    }
  }, [refreshWatchlist, toast]);

  const removeStock = useCallback(async (code: string): Promise<boolean> => {
    try {
      await stocksApi.removeWatchlistStock(code);
      setWatchlist((prev) => prev.filter((item) => item.stockCode !== code));
      toast.success('删除成功');
      return true;
    } catch (e) {
      console.error('Failed to remove watchlist stock', e);
      toast.error('删除失败，请稍后重试');
      return false;
    }
  }, [toast]);

  const updateStock = useCallback((code: string, data: Partial<WatchlistItem>) => {
    setWatchlist((prev) =>
      prev.map((item) => (item.stockCode === code ? { ...item, ...data } : item))
    );
  }, []);

  return {
    watchlist,
    isLoading,
    isSyncingPrices,
    refreshWatchlist,
    addStock,
    removeStock,
    updateStock,
  };
}
