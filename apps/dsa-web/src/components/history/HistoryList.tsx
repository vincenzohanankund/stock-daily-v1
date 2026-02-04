import type React from 'react';
import { useState, useEffect, useCallback } from 'react';
import type {
  HistoryItem as HistoryItemType,
  HistoryFilters as HistoryFiltersType,
} from '../../types/analysis';
import { historyApi } from '../../api/history';
import { Pagination } from '../common';
import { HistoryFilters } from './HistoryFilters';
import { HistoryItem } from './HistoryItem';
import { EmptyState } from './EmptyState';
import { HistoryDrawer } from './HistoryDrawer';
import { getRecentStartDate, toDateInputValue } from '../../utils/format';

const DEFAULT_PAGE_SIZE = 20;

/**
 * 历史分析列表组件 - 终端风格
 */
export const HistoryList: React.FC = () => {
  // 状态
  const [items, setItems] = useState<HistoryItemType[]>([]);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 筛选条件
  const [filters, setFilters] = useState<HistoryFiltersType>({
    startDate: getRecentStartDate(30),
    endDate: toDateInputValue(new Date()),
  });

  // 抽屉状态
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedQueryId, setSelectedQueryId] = useState<string | null>(null);

  // 加载数据
  const fetchHistory = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await historyApi.getList({
        ...filters,
        page: currentPage,
        limit: DEFAULT_PAGE_SIZE,
      });

      setItems(response.items);
      setTotal(response.total);
    } catch (err) {
      console.error('Failed to fetch history:', err);
      setError(err instanceof Error ? err.message : '获取历史记录失败');
    } finally {
      setIsLoading(false);
    }
  }, [filters, currentPage]);

  // 初始加载和筛选变化时重新加载
  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  // 搜索
  const handleSearch = () => {
    setCurrentPage(1);
    fetchHistory();
  };

  // 重置筛选
  const handleReset = () => {
    setFilters({
      startDate: getRecentStartDate(30),
      endDate: toDateInputValue(new Date()),
    });
    setCurrentPage(1);
  };

  // 分页
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  // 点击查看详情
  const handleItemClick = (queryId: string) => {
    setSelectedQueryId(queryId);
    setDrawerOpen(true);
  };

  // 关闭抽屉
  const handleDrawerClose = () => {
    setDrawerOpen(false);
    setSelectedQueryId(null);
  };

  const totalPages = Math.ceil(total / DEFAULT_PAGE_SIZE);

  return (
    <div className="space-y-6">
      {/* 筛选区 */}
      <HistoryFilters
        filters={filters}
        onFiltersChange={setFilters}
        onSearch={handleSearch}
        onReset={handleReset}
        isLoading={isLoading}
      />

      {/* 统计信息 */}
      {!isLoading && items.length > 0 && (
        <div className="flex items-center justify-between text-sm text-muted">
          <span>
            共 <span className="text-cyan font-medium">{total}</span> 条记录
          </span>
          <span>
            第 {currentPage} / {totalPages} 页
          </span>
        </div>
      )}

      {/* 内容区 */}
      {isLoading ? (
        <div className="py-16 flex flex-col items-center">
          <div className="w-12 h-12 rounded-full border-4 border-cyan/20 border-t-cyan animate-spin" />
          <p className="mt-4 text-secondary">加载中...</p>
        </div>
      ) : error ? (
        <div className="py-16 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-danger/10 flex items-center justify-center">
            <svg className="w-8 h-8 text-danger" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <p className="text-danger mb-4">{error}</p>
          <button
            type="button"
            onClick={fetchHistory}
            className="text-cyan hover:underline"
          >
            点击重试
          </button>
        </div>
      ) : items.length === 0 ? (
        <EmptyState />
      ) : (
        <>
          {/* 列表 */}
          <div className="terminal-card divide-y divide-white/5">
            {items.map((item) => (
              <HistoryItem
                key={item.queryId}
                item={item}
                onClick={() => handleItemClick(item.queryId)}
              />
            ))}
          </div>

          {/* 分页 */}
          {totalPages > 1 && (
            <Pagination
              currentPage={currentPage}
              totalPages={totalPages}
              onPageChange={handlePageChange}
              className="mt-6"
            />
          )}
        </>
      )}

      {/* 详情抽屉 */}
      <HistoryDrawer
        isOpen={drawerOpen}
        onClose={handleDrawerClose}
        queryId={selectedQueryId}
      />
    </div>
  );
};
