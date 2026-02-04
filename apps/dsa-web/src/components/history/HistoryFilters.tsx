import type React from 'react';
import type { HistoryFilters as HistoryFiltersType } from '../../types/analysis';
import { getRecentStartDate, toDateInputValue } from '../../utils/format';

interface HistoryFiltersProps {
  filters: HistoryFiltersType;
  onFiltersChange: (filters: HistoryFiltersType) => void;
  onSearch: () => void;
  onReset: () => void;
  isLoading?: boolean;
}

/**
 * 历史记录筛选组件 - 终端风格
 */
export const HistoryFilters: React.FC<HistoryFiltersProps> = ({
  filters,
  onFiltersChange,
  onSearch,
  onReset,
  isLoading = false,
}) => {
  const handleStockCodeChange = (value: string) => {
    onFiltersChange({ ...filters, stockCode: value.toUpperCase() || undefined });
  };

  const handleStartDateChange = (value: string) => {
    onFiltersChange({ ...filters, startDate: value || undefined });
  };

  const handleEndDateChange = (value: string) => {
    onFiltersChange({ ...filters, endDate: value || undefined });
  };

  const handleQuickFilter = (days: number) => {
    const startDate = getRecentStartDate(days);
    const endDate = toDateInputValue(new Date());
    onFiltersChange({ ...filters, startDate, endDate });
  };

  return (
    <div className="terminal-card p-6 space-y-4">
      {/* 筛选输入区 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* 股票代码 */}
        <div>
          <label className="block text-xs font-medium text-muted mb-2 uppercase tracking-wider">
            股票代码
          </label>
          <input
            type="text"
            value={filters.stockCode || ''}
            onChange={(e) => handleStockCodeChange(e.target.value)}
            placeholder="例如: 600519"
            className="input-terminal"
            disabled={isLoading}
          />
        </div>

        {/* 开始日期 */}
        <div>
          <label className="block text-xs font-medium text-muted mb-2 uppercase tracking-wider">
            开始日期
          </label>
          <input
            type="date"
            value={filters.startDate || ''}
            onChange={(e) => handleStartDateChange(e.target.value)}
            className="input-terminal"
            disabled={isLoading}
          />
        </div>

        {/* 结束日期 */}
        <div>
          <label className="block text-xs font-medium text-muted mb-2 uppercase tracking-wider">
            结束日期
          </label>
          <input
            type="date"
            value={filters.endDate || ''}
            onChange={(e) => handleEndDateChange(e.target.value)}
            className="input-terminal"
            disabled={isLoading}
          />
        </div>

        {/* 操作按钮 */}
        <div className="flex items-end gap-2">
          <button
            type="button"
            className="btn-primary flex-1"
            onClick={onSearch}
            disabled={isLoading}
          >
            搜索
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={onReset}
            disabled={isLoading}
          >
            重置
          </button>
        </div>
      </div>

      {/* 快捷筛选 */}
      <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-white/5">
        <span className="text-xs text-muted">快捷筛选:</span>
        {[
          { label: '7 天', days: 7 },
          { label: '30 天', days: 30 },
          { label: '90 天', days: 90 },
        ].map(({ label, days }) => (
          <button
            key={days}
            type="button"
            onClick={() => handleQuickFilter(days)}
            disabled={isLoading}
            className="px-3 py-1 text-xs rounded-lg
              bg-elevated text-secondary border border-white/5
              hover:bg-hover hover:text-cyan hover:border-cyan/30
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-colors"
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
};
