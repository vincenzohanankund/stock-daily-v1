import React, { useState, useCallback } from 'react';
import { 
  RefreshCcw, 
  Plus, 
  Trash2, 
  Eye, 
  PlayCircle, 
  TrendingUp, 
  TrendingDown, 
  Info,
  LayoutGrid,
  List,
  Activity,
  ClipboardList
} from 'lucide-react';
import { useAnalysisStore } from '../stores/analysisStore';
import { historyApi } from '../api/history';
import { analysisApi, DuplicateTaskError } from '../api/analysis';
import { validateStockCode } from '../utils/validation';
import { HistoryList } from '../components/history';
import { TaskPanel } from '../components/tasks';
import { ReportSummary } from '../components/report';
import { useTaskStream } from '../hooks';
import { useWatchlist } from '../hooks/useWatchlist';
import type { HistoryItem, AnalysisReport, TaskInfo } from '../types/analysis';

import Input from '../components/common/Input';
import Button from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import Modal from '../components/common/Modal';
import { Empty } from '../components/common/Empty';
import ConfirmationModal from '../components/common/ConfirmationModal';
import { useToast } from '../components/common/Toast';
import { StockCard } from '../components/stock/StockCard';
import ErrorBoundary from '../components/common/ErrorBoundary';
import Drawer from '../components/common/Drawer';

const HomePage: React.FC = () => {
  const { setLoading, setError: setStoreError } = useAnalysisStore();
  const { watchlist, addStock, removeStock, updateStock, isLoading: isLoadingWatchlist } = useWatchlist();
  const toast = useToast();

  // State
  const [activeTasks, setActiveTasks] = useState<TaskInfo[]>([]);
  
  // Detail Modal & Report State
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedStock, setSelectedStock] = useState<string | null>(null);
  const [selectedReport, setSelectedReport] = useState<AnalysisReport | null>(null);
  const [isLoadingReport, setIsLoadingReport] = useState(false);
  const [stockHistoryItems, setStockHistoryItems] = useState<HistoryItem[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // Add Stock Modal State
  const [addModalVisible, setAddModalVisible] = useState(false);
  const [analyzeAllModalVisible, setAnalyzeAllModalVisible] = useState(false);
  const [newStockCode, setNewStockCode] = useState('');

  // Delete Confirmation State
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'card' | 'list'>('card');
  const [taskDrawerVisible, setTaskDrawerVisible] = useState(false);

  // --- Task Management ---
  const updateTask = useCallback((updatedTask: TaskInfo) => {
    setActiveTasks((prev) => {
      const index = prev.findIndex((t) => t.taskId === updatedTask.taskId);
      if (index >= 0) {
        const newTasks = [...prev];
        newTasks[index] = updatedTask;
        return newTasks;
      }
      return prev;
    });
  }, []);

  const removeTask = useCallback((taskId: string) => {
    setActiveTasks((prev) => prev.filter((t) => t.taskId !== taskId));
  }, []);

  // --- API Calls ---
  const fetchStockHistory = useCallback(async (code: string) => {
    setIsLoadingHistory(true);
    try {
      const response = await historyApi.getList({
        stockCode: code,
        page: 1,
        limit: 20,
      });
      setStockHistoryItems(response.items);
      
      // Auto-select latest report if none selected or if it's a new stock
      if (response.items.length > 0) {
        // We need to define handleViewReport before calling it, but it's defined below.
        // However, since this is inside a component, we can call it if it's stable.
        // But handleViewReport depends on state setters.
        // To avoid circular dependency in useCallback, we can just set the report ID to be fetched
        // or call the API directly here for the first item.
        const firstItem = response.items[0];
        try {
            const report = await historyApi.getDetail(firstItem.queryId);
            setSelectedReport(report);
             if (report && report.summary) {
                updateStock(report.meta.stockCode, {
                   lastAnalysisTime: report.meta.createdAt,
                   lastPrice: report.meta.currentPrice,
                   changePct: report.meta.changePct,
                   trendPrediction: report.summary.trendPrediction,
                   operationAdvice: report.summary.operationAdvice
                });
              }
        } catch (e) {
            console.error(e);
        }
      } else {
        setSelectedReport(null);
      }
    } catch (err) {
      console.error('Failed to fetch stock history:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  }, [updateStock]);

  const handleViewReport = async (queryId: string) => {
    setIsLoadingReport(true);
    try {
      const report = await historyApi.getDetail(queryId);
      setSelectedReport(report);
      
      // Update watchlist item with latest info if available
      if (report && report.summary) {
        updateStock(report.meta.stockCode, {
           lastAnalysisTime: report.meta.createdAt,
           lastPrice: report.meta.currentPrice,
           changePct: report.meta.changePct,
           trendPrediction: report.summary.trendPrediction,
           operationAdvice: report.summary.operationAdvice
        });
      }
    } catch (err) {
      console.error('Failed to fetch report:', err);
      toast.error('获取报告失败');
    } finally {
      setIsLoadingReport(false);
    }
  };

  const handleAnalyze = async (code: string, silent = false) => {
    const { valid, message, normalized } = validateStockCode(code);
    if (!valid) {
      if (!silent) toast.error(message || '无效的股票代码');
      return;
    }

    setLoading(true);
    setStoreError(null);

    try {
      const res = await analysisApi.analyzeAsync({
        stockCode: normalized,
        reportType: 'detailed',
      });
      
      // Optimistically add task to list so it appears in drawer immediately
      setActiveTasks(prev => {
        if (prev.some(t => t.taskId === res.taskId)) return prev;
        return [...prev, {
          taskId: res.taskId,
          stockCode: normalized,
          status: 'pending',
          progress: 0,
          reportType: 'detailed',
          createdAt: new Date().toISOString(),
        }];
      });
      
      if (!silent) toast.success(`已提交 ${normalized} 分析任务`);
    } catch (err: any) {
        if (err instanceof DuplicateTaskError) {
             if (!silent) toast.warning(err.message);
        } else {
             const msg = err.response?.data?.error || err.message || '分析请求失败';
             setStoreError(msg);
             if (!silent) toast.error(msg);
        }
    } finally {
        setLoading(false);
    }
  };

  const handleAnalyzeAll = async () => {
    setAnalyzeAllModalVisible(false);
    if (watchlist.length === 0) {
        toast.warning('自选列表为空');
        return;
    }

    setTaskDrawerVisible(true);
    toast.info(`正在提交 ${watchlist.length} 个分析任务...`);

    let submittedCount = 0;
    
    // Execute in parallel but maybe limit concurrency if needed? 
    // For now, let's just fire them all. Browsers handle concurrent requests well enough for small numbers.
    // If watchlist is huge, we might need to batch. Assuming < 50 stocks.
    
    for (const item of watchlist) {
        // Use a small delay between requests to avoid overwhelming the server or browser
        await new Promise(resolve => setTimeout(resolve, 100));
        void handleAnalyze(item.stockCode, true);
        submittedCount++;
    }
    
    toast.success(`已开始分析全部 ${submittedCount} 只股票`);
  };

  // --- Event Handlers ---
  const handleAddStock = async () => {
      const { valid, message, normalized } = validateStockCode(newStockCode);
      if (!valid) {
          toast.error(message || '无效的股票代码');
          return;
      }

      const added = await addStock(normalized);
      if (!added) {
        return;
      }

      setNewStockCode('');
      setAddModalVisible(false);
      setTaskDrawerVisible(true);
      
      // Optionally trigger analysis immediately
      void handleAnalyze(normalized);
  };

  const openDetailModal = (code: string) => {
      setSelectedStock(code);
      setDetailModalVisible(true);
      fetchStockHistory(code);
  };

  useTaskStream({
    onTaskCreated: (task) => {
      setActiveTasks((prev) => {
        if (prev.some((t) => t.taskId === task.taskId)) return prev;
        return [...prev, task];
      });
      // 只有在没有任务的时候才自动打开 Drawer 提示用户
      // 如果已经有任务在运行，用户可能已经知道了，就不打扰了
      // 或者这里可以做一个 toast 提示
    },
    onTaskStarted: updateTask,
    onTaskCompleted: async (task) => {
      // Refresh history if the completed task matches the currently viewed stock
      if (selectedStock && task.stockCode === selectedStock) {
          fetchStockHistory(selectedStock);
      }
      
      // Auto-update watchlist item
      try {
          const response = await historyApi.getList({
              stockCode: task.stockCode,
              page: 1,
              limit: 1
          });
          if (response.items.length > 0) {
              const latest = response.items[0];
              const report = await historyApi.getDetail(latest.queryId);
              if (report && report.summary) {
                  updateStock(task.stockCode, {
                      lastAnalysisTime: report.meta.createdAt,
                      lastPrice: report.meta.currentPrice,
                      changePct: report.meta.changePct,
                      trendPrediction: report.summary.trendPrediction,
                      operationAdvice: report.summary.operationAdvice
                  });
              }
          }
      } catch (e) {
          console.error('Failed to auto-update watchlist item', e);
      }

      setTimeout(() => removeTask(task.taskId), 2000);
    },
    onTaskFailed: (task) => {
      updateTask(task);
      setStoreError(task.error || '分析失败');
      toast.error(`任务失败: ${task.error || '未知错误'}`);
      setTimeout(() => removeTask(task.taskId), 5000);
    },
    onError: () => {
      console.warn('SSE 连接断开，正在重连...');
    },
    enabled: true,
  });

  // --- Render ---

  return (
    <div className="h-full flex flex-col gap-6 p-6 overflow-hidden bg-muted/5">
        {/* Header & Tasks */}
        <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold tracking-tight">个股分析</h1>
            <div className="flex items-center gap-3">
                <Button 
                    variant="outline" 
                    className="relative px-3"
                    onClick={() => setTaskDrawerVisible(true)}
                    title="查看任务"
                >
                    <ClipboardList size={16} />
                    {activeTasks.length > 0 && (
                        <span className="absolute -top-2 -right-2 bg-destructive text-destructive-foreground text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center border border-background shadow-sm">
                            {activeTasks.length}
                        </span>
                    )}
                </Button>
                
                <div className="flex items-center bg-muted rounded-lg p-1 border border-border">
                    <button
                        onClick={() => setViewMode('card')}
                        className={`p-1.5 rounded-md transition-all ${viewMode === 'card' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                        title="卡片视图"
                    >
                        <LayoutGrid size={16} />
                    </button>
                    <button
                        onClick={() => setViewMode('list')}
                        className={`p-1.5 rounded-md transition-all ${viewMode === 'list' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                        title="列表视图"
                    >
                        <List size={16} />
                    </button>
                </div>
                <Button 
                    variant="outline" 
                    icon={<PlayCircle size={16} />} 
                    onClick={() => setAnalyzeAllModalVisible(true)}
                    disabled={watchlist.length === 0}
                >
                    全部分析
                </Button>
                <Button variant="primary" icon={<Plus size={16} />} onClick={() => setAddModalVisible(true)}>
                    添加自选
                </Button>
            </div>
        </div>

        {/* Watchlist Grid */}
        <div className="flex-1 overflow-auto">
            {isLoadingWatchlist ? (
                <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                    正在加载自选股...
                </div>
            ) : watchlist.length === 0 ? (
                <Empty description="暂无自选股，请点击右上角添加" />
            ) : viewMode === 'list' ? (
                <div className="bg-card rounded-lg border border-border overflow-hidden">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="bg-muted/50 border-b border-border text-left">
                                <th className="py-3 px-4 font-medium text-muted-foreground w-[180px]">股票</th>
                                <th className="py-3 px-4 font-medium text-muted-foreground">最新价</th>
                                <th className="py-3 px-4 font-medium text-muted-foreground">趋势预测</th>
                                <th className="py-3 px-4 font-medium text-muted-foreground">操作建议</th>
                                <th className="py-3 px-4 font-medium text-muted-foreground">最后分析</th>
                                <th className="py-3 px-4 font-medium text-muted-foreground text-right">操作</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {watchlist.map((item) => (
                                <tr key={item.stockCode} className="hover:bg-muted/30 transition-colors group">
                                    <td className="py-3 px-4">
                                        <div className="flex items-center gap-2">
                                            <span className="font-bold">{item.stockName || item.stockCode}</span>
                                            {item.stockName && <span className="text-xs font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded">{item.stockCode}</span>}
                                        </div>
                                    </td>
                                    <td className="py-3 px-4">
                                        <div className="flex items-baseline gap-2">
                                            <span className={`font-bold ${(item.changePct || 0) > 0 ? 'text-destructive' : (item.changePct || 0) < 0 ? 'text-green-500' : 'text-foreground'}`}>
                                                {item.lastPrice?.toFixed(2) || '--'}
                                            </span>
                                            {item.changePct != null && (
                                                <Badge variant={(item.changePct > 0 ? 'destructive' : 'success')} className="px-1.5 py-0 text-[10px]">
                                                    {item.changePct > 0 ? '+' : ''}{item.changePct.toFixed(2)}%
                                                </Badge>
                                            )}
                                        </div>
                                    </td>
                                    <td className="py-3 px-4">
                                        {(() => {
                                            if (!item.trendPrediction) return <span className="text-muted-foreground">--</span>;
                                            let icon = <Activity size={14} />;
                                            let colorClass = 'text-muted-foreground';
                                            if (item.trendPrediction.includes('涨') || item.trendPrediction.includes('多')) {
                                                icon = <TrendingUp size={14} />;
                                                colorClass = 'text-destructive';
                                            } else if (item.trendPrediction.includes('跌') || item.trendPrediction.includes('空')) {
                                                icon = <TrendingDown size={14} />;
                                                colorClass = 'text-green-500';
                                            }
                                            return (
                                                <div className={`${colorClass} flex items-center gap-1.5 font-medium`}>
                                                    {icon}
                                                    <span>{item.trendPrediction}</span>
                                                </div>
                                            );
                                        })()}
                                    </td>
                                    <td className="py-3 px-4">
                                        {item.operationAdvice ? (
                                            <span className={`font-medium ${
                                                item.operationAdvice.includes('买') ? 'text-destructive' : 
                                                item.operationAdvice.includes('卖') ? 'text-green-500' : 'text-foreground'
                                            }`}>
                                                {item.operationAdvice}
                                            </span>
                                        ) : <span className="text-muted-foreground">--</span>}
                                    </td>
                                    <td className="py-3 px-4 text-muted-foreground font-mono text-xs">
                                        {item.lastAnalysisTime ? new Date(item.lastAnalysisTime).toLocaleString('zh-CN', {
                                            month: '2-digit',
                                            day: '2-digit',
                                            hour: '2-digit',
                                            minute: '2-digit'
                                        }) : '从未'}
                                    </td>
                                    <td className="py-3 px-4 text-right">
                                        <div className="flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <Button variant="ghost" size="sm" icon={<PlayCircle size={14} />} onClick={() => handleAnalyze(item.stockCode)}>
                                                分析
                                            </Button>
                                            <Button variant="ghost" size="sm" icon={<Eye size={14} />} onClick={() => openDetailModal(item.stockCode)}>
                                                详情
                                            </Button>
                                            <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-destructive" onClick={() => setDeleteTarget(item.stockCode)}>
                                                <Trash2 size={14} />
                                            </Button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ) : (
                <div className="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-4 pb-6">
                    {watchlist.map((item) => (
                        <ErrorBoundary key={item.stockCode}>
                            <StockCard
                                item={item}
                                onAnalyze={handleAnalyze}
                                onDetail={openDetailModal}
                                onDelete={setDeleteTarget}
                            />
                        </ErrorBoundary>
                    ))}
                </div>
            )}
        </div>

        {/* Task Drawer */}
        <Drawer
            isOpen={taskDrawerVisible}
            onClose={() => setTaskDrawerVisible(false)}
            title={
                <div className="flex items-center gap-2">
                    <ClipboardList size={18} />
                    <span>分析任务列表</span>
                    {activeTasks.length > 0 && (
                        <span className="text-xs font-normal text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
                            {activeTasks.length} 进行中
                        </span>
                    )}
                </div>
            }
            width={400}
        >
            <div className="space-y-4">
                {activeTasks.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12 text-muted-foreground gap-3">
                        <div className="p-4 bg-muted/50 rounded-full">
                            <ClipboardList size={32} className="opacity-50" />
                        </div>
                        <p className="text-sm">暂无进行中的分析任务</p>
                        <Button 
                            variant="outline" 
                            size="sm" 
                            onClick={() => {
                                setTaskDrawerVisible(false);
                                setAddModalVisible(true);
                            }}
                        >
                            <Plus size={14} className="mr-1" /> 新建任务
                        </Button>
                    </div>
                ) : (
                    <TaskPanel 
                        tasks={activeTasks} 
                        visible={true} 
                        variant="plain"
                    />
                )}
            </div>
        </Drawer>

        {/* Add Stock Modal */}
        <Modal
            title="添加自选股"
            isOpen={addModalVisible}
            onClose={() => setAddModalVisible(false)}
            size="sm"
            footer={
                <div className="flex justify-end gap-3 w-full">
                    <Button variant="outline" onClick={() => setAddModalVisible(false)}>取消</Button>
                    <Button onClick={() => void handleAddStock()} icon={<Plus size={16} />}>添加</Button>
                </div>
            }
        >
            <div className="py-4 space-y-4">
                <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">
                        请输入股票代码以添加到您的自选列表。支持 A 股（600000）、港股（00700/HK00700）、美股（AAPL）。
                    </p>
                    <div className="relative">
                        <Input 
                            placeholder="输入股票代码..." 
                            value={newStockCode} 
                            onChange={(e) => setNewStockCode(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') void handleAddStock();
                            }}
                            autoFocus
                            className="font-mono text-lg tracking-wider"
                        />
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground bg-muted/50 p-2 rounded-md border border-border/50">
                        <Info size={12} className="text-primary" />
                        <span>支持 A股/港股/美股 代码，添加后将自动开始分析。</span>
                    </div>
                </div>
            </div>
        </Modal>
        
        {/* Delete Confirmation Modal */}
        <ConfirmationModal
            isOpen={!!deleteTarget}
            onClose={() => setDeleteTarget(null)}
            onConfirm={() => {
                if (deleteTarget) {
                    void removeStock(deleteTarget);
                    setDeleteTarget(null);
                }
            }}
            title="确认删除"
            content={`确认删除自选股 ${deleteTarget} 吗？`}
            type="warning"
            confirmText="删除"
        />

        {/* Analyze All Confirmation Modal */}
        <ConfirmationModal
            isOpen={analyzeAllModalVisible}
            onClose={() => setAnalyzeAllModalVisible(false)}
            onConfirm={handleAnalyzeAll}
            title="全部重新分析"
            content={`确定要对列表中的 ${watchlist.length} 只股票进行重新分析吗？这可能需要一些时间。`}
            type="info"
            confirmText="开始分析"
        />

        {/* Detail Modal */}
        <Modal
            size="2xl"
            isOpen={detailModalVisible}
            onClose={() => setDetailModalVisible(false)}
            scrollableContent={false}
            title={
              <div className="flex items-center gap-2">
                <span className="text-xl font-bold tracking-tight">
                  {watchlist.find(w => w.stockCode === selectedStock)?.stockName || selectedStock}
                </span>
                <Badge variant="outline" className="text-sm font-mono text-muted-foreground bg-muted/50 px-2 py-0.5 rounded-md border-border">
                  {selectedStock}
                </Badge>
              </div>
            }
        >
            <div className="flex h-[70vh] gap-6 overflow-hidden">
                {/* Left: History List for this stock */}
                <div className="w-[280px] flex flex-col border-r border-border pr-4 shrink-0 h-full">
                    <div className="mb-4 flex justify-between items-center shrink-0 pl-1">
                        <h3 className="text-base font-semibold tracking-tight text-foreground/90">历史记录</h3>
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          className="h-8 w-8 p-0 hover:bg-muted/80 text-muted-foreground hover:text-foreground transition-colors rounded-full" 
                          onClick={() => selectedStock && fetchStockHistory(selectedStock)}
                          title="刷新历史记录"
                        >
                            <RefreshCcw size={14} />
                        </Button>
                    </div>
                    <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                        <HistoryList
                            items={stockHistoryItems}
                            isLoading={isLoadingHistory}
                            hasMore={false} 
                            selectedQueryId={selectedReport?.meta?.queryId}
                            onItemClick={handleViewReport}
                            className="history-list-mini space-y-2"
                            isLoadingMore={false}
                            onLoadMore={() => {}}
                        />
                    </div>
                </div>

                {/* Right: Report Content */}
                <div className="flex-1 overflow-y-auto pr-2 pl-2 custom-scrollbar h-full">
                    {isLoadingReport ? (
                        <div className="h-full flex justify-center items-center">
                            <div className="flex flex-col items-center gap-3 p-6 bg-muted/10 rounded-xl">
                                <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent"></div>
                                <span className="text-muted-foreground text-sm font-medium">加载报告中...</span>
                            </div>
                        </div>
                    ) : selectedReport ? (
                        <div className="pb-6">
                            <ReportSummary data={selectedReport} />
                        </div>
                    ) : (
                        <div className="h-full flex flex-col justify-center items-center text-muted-foreground/60 gap-3">
                            <List size={48} strokeWidth={1} />
                            <span className="text-sm">请选择左侧历史记录查看详情</span>
                        </div>
                    )}
                </div>
            </div>
        </Modal>
    </div>
  );
};

export default HomePage;
