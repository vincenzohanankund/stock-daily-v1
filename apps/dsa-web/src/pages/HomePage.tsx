import type React from 'react';
import { useState, useEffect, useCallback, useRef } from 'react';
import type { HistoryItem, AnalysisReport } from '../types/analysis';
import { historyApi } from '../api/history';
import { analysisApi } from '../api/analysis';
import { validateStockCode } from '../utils/validation';
import { formatDateTime, getRecentStartDate, toDateInputValue } from '../utils/format';
import { getSentimentColor } from '../types/analysis';
import { useAnalysisStore } from '../stores/analysisStore';
import { ReportSummary } from '../components/report';

/**
 * 首页 - 单页设计
 * 顶部输入 + 左侧历史 + 右侧报告
 */
const HomePage: React.FC = () => {
  const { setLoading, setResult, setError: setStoreError } = useAnalysisStore();

  // 输入状态
  const [stockCode, setStockCode] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [inputError, setInputError] = useState<string>();

  // 历史列表状态
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // 报告详情状态
  const [selectedReport, setSelectedReport] = useState<AnalysisReport | null>(null);
  const [isLoadingReport, setIsLoadingReport] = useState(false);

  // 用于跟踪当前分析请求，避免竞态条件
  const analysisRequestIdRef = useRef<number>(0);

  // 加载历史列表
  const fetchHistory = useCallback(async (autoSelectFirst = false) => {
    setIsLoadingHistory(true);
    try {
      const response = await historyApi.getList({
        startDate: getRecentStartDate(30),
        endDate: toDateInputValue(new Date()),
        limit: 50,
      });
      setHistoryItems(response.items);

      // 如果需要自动选择第一条，且有数据，且当前没有选中报告
      if (autoSelectFirst && response.items.length > 0 && !selectedReport) {
        const firstItem = response.items[0];
        setIsLoadingReport(true);
        try {
          const report = await historyApi.getDetail(firstItem.queryId);
          setSelectedReport(report);
        } catch (err) {
          console.error('Failed to fetch first report:', err);
        } finally {
          setIsLoadingReport(false);
        }
      }
    } catch (err) {
      console.error('Failed to fetch history:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  }, [selectedReport]);

  // 初始加载 - 自动选择第一条
  useEffect(() => {
    fetchHistory(true);
  }, []);

  // 点击历史项加载报告
  const handleHistoryClick = async (queryId: string) => {
    // 取消当前分析请求的结果显示（通过递增 requestId）
    analysisRequestIdRef.current += 1;

    setIsLoadingReport(true);
    try {
      const report = await historyApi.getDetail(queryId);
      setSelectedReport(report);
    } catch (err) {
      console.error('Failed to fetch report:', err);
    } finally {
      setIsLoadingReport(false);
    }
  };

  // 分析股票
  const handleAnalyze = async () => {
    const { valid, message, normalized } = validateStockCode(stockCode);
    if (!valid) {
      setInputError(message);
      return;
    }

    setInputError(undefined);
    setIsAnalyzing(true);
    setLoading(true);
    setStoreError(null);

    // 记录当前请求的 ID
    const currentRequestId = ++analysisRequestIdRef.current;

    try {
      const result = await analysisApi.analyze({
        stockCode: normalized,
        reportType: 'detailed',
      });

      // 只有当请求 ID 匹配时才更新报告（用户没有在分析期间切换到其他报告）
      if (currentRequestId === analysisRequestIdRef.current) {
        setResult(result);
        setSelectedReport(result.report);
        setStockCode('');
      }

      // 无论如何都刷新历史列表
      fetchHistory();
    } catch (err) {
      console.error('Analysis failed:', err);
      if (currentRequestId === analysisRequestIdRef.current) {
        setStoreError(err instanceof Error ? err.message : '分析失败');
      }
    } finally {
      setIsAnalyzing(false);
      setLoading(false);
    }
  };

  // 回车提交
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && stockCode && !isAnalyzing) {
      handleAnalyze();
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* 顶部输入栏 */}
      <header className="flex-shrink-0 px-4 py-3 border-b border-white/5">
        <div className="flex items-center gap-2 max-w-2xl">
          <div className="flex-1 relative">
            <input
              type="text"
              value={stockCode}
              onChange={(e) => {
                setStockCode(e.target.value.toUpperCase());
                setInputError(undefined);
              }}
              onKeyDown={handleKeyDown}
              placeholder="输入股票代码，如 600519、00700、AAPL"
              disabled={isAnalyzing}
              className={`input-terminal w-full ${inputError ? 'border-danger/50' : ''}`}
            />
            {inputError && (
              <p className="absolute -bottom-4 left-0 text-xs text-danger">{inputError}</p>
            )}
          </div>
          <button
            type="button"
            onClick={handleAnalyze}
            disabled={!stockCode || isAnalyzing}
            className="btn-primary flex items-center gap-1.5 whitespace-nowrap"
          >
            {isAnalyzing ? (
              <>
                <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                分析中
              </>
            ) : (
              '分析'
            )}
          </button>
        </div>
      </header>

      {/* 主内容区 */}
      <main className="flex-1 flex overflow-hidden p-3 gap-3">
        {/* 左侧历史列表 - 毛玻璃卡片 */}
        <aside className="w-64 flex-shrink-0 glass-card overflow-hidden flex flex-col h-[calc(66vh)]">
          <div className="p-3 flex-1 overflow-y-auto">
            <h2 className="text-xs font-medium text-purple uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              历史记录
            </h2>

            {isLoadingHistory ? (
              <div className="flex justify-center py-6">
                <div className="w-5 h-5 border-2 border-cyan/20 border-t-cyan rounded-full animate-spin" />
              </div>
            ) : historyItems.length === 0 ? (
              <div className="text-center py-6 text-muted text-xs">
                暂无历史记录
              </div>
            ) : (
              <div className="space-y-1.5">
                {historyItems.map((item) => (
                  <button
                    key={item.queryId}
                    type="button"
                    onClick={() => handleHistoryClick(item.queryId)}
                    className={`history-item w-full text-left ${selectedReport?.meta.queryId === item.queryId ? 'active' : ''
                      }`}
                  >
                    <div className="flex items-center gap-2 w-full">
                      {/* 情感分数指示条 */}
                      {item.sentimentScore !== undefined && (
                        <span
                          className="w-0.5 h-8 rounded-full flex-shrink-0"
                          style={{
                            backgroundColor: getSentimentColor(item.sentimentScore),
                            boxShadow: `0 0 6px ${getSentimentColor(item.sentimentScore)}40`
                          }}
                        />
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-1.5">
                          <span className="font-medium text-white truncate text-xs">
                            {item.stockName || item.stockCode}
                          </span>
                          {item.sentimentScore !== undefined && (
                            <span
                              className="text-xs font-mono font-semibold px-1 py-0.5 rounded"
                              style={{
                                color: getSentimentColor(item.sentimentScore),
                                backgroundColor: `${getSentimentColor(item.sentimentScore)}15`
                              }}
                            >
                              {item.sentimentScore}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <span className="text-xs text-muted font-mono">
                            {item.stockCode}
                          </span>
                          <span className="text-xs text-muted/50">·</span>
                          <span className="text-xs text-muted">
                            {formatDateTime(item.createdAt)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </aside>

        {/* 右侧报告详情 */}
        <section className="flex-1 overflow-y-auto pl-1">
          {isLoadingReport ? (
            <div className="flex flex-col items-center justify-center h-full">
              <div className="w-10 h-10 border-3 border-cyan/20 border-t-cyan rounded-full animate-spin" />
              <p className="mt-3 text-secondary text-sm">加载报告中...</p>
            </div>
          ) : selectedReport ? (
            <div className="max-w-4xl">
              {/* 报告内容 */}
              <ReportSummary data={selectedReport} isHistory />
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-12 h-12 mb-3 rounded-xl bg-elevated flex items-center justify-center">
                <svg className="w-6 h-6 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="text-base font-medium text-white mb-1.5">开始分析</h3>
              <p className="text-xs text-muted max-w-xs">
                输入股票代码进行分析，或从左侧选择历史报告查看
              </p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
};

export default HomePage;
