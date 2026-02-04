import type React from 'react';
import { useEffect, useState } from 'react';
import type { AnalysisReport } from '../../types/analysis';
import { Drawer } from '../common';
import { ReportSummary } from '../report';
import { historyApi } from '../../api/history';
import { useNavigate } from 'react-router-dom';
import { useAnalysisStore } from '../../stores/analysisStore';
import { analysisApi } from '../../api/analysis';

interface HistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  queryId: string | null;
}

/**
 * 历史报告详情抽屉 - 终端风格
 */
export const HistoryDrawer: React.FC<HistoryDrawerProps> = ({
  isOpen,
  onClose,
  queryId,
}) => {
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isReanalyzing, setIsReanalyzing] = useState(false);

  const navigate = useNavigate();
  const { setLoading, setResult, setError: setStoreError } = useAnalysisStore();

  // 加载报告详情
  useEffect(() => {
    if (!isOpen || !queryId) {
      setReport(null);
      setError(null);
      return;
    }

    const fetchReport = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const data = await historyApi.getDetail(queryId);
        setReport(data);
      } catch (err) {
        console.error('Failed to fetch history detail:', err);
        setError(err instanceof Error ? err.message : '获取报告详情失败');
      } finally {
        setIsLoading(false);
      }
    };

    fetchReport();
  }, [isOpen, queryId]);

  // 重新分析
  const handleReanalyze = async () => {
    if (!report) return;

    setIsReanalyzing(true);
    setLoading(true);
    setStoreError(null);

    try {
      const result = await analysisApi.analyze({
        stockCode: report.meta.stockCode,
        reportType: report.meta.reportType,
      });

      setResult(result);
      onClose();
      navigate('/report');
    } catch (err) {
      console.error('Reanalysis failed:', err);
      setStoreError(err instanceof Error ? err.message : '重新分析失败');
    } finally {
      setIsReanalyzing(false);
      setLoading(false);
    }
  };

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      title="历史报告详情"
      width="max-w-3xl"
    >
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="w-12 h-12 rounded-full border-4 border-cyan/20 border-t-cyan animate-spin" />
          <p className="mt-4 text-secondary">加载报告中...</p>
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-16 h-16 mb-4 rounded-2xl bg-danger/10 flex items-center justify-center">
            <svg className="w-8 h-8 text-danger" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <p className="text-danger mb-4">{error}</p>
          <button type="button" className="btn-secondary" onClick={onClose}>
            关闭
          </button>
        </div>
      ) : report ? (
        <div className="space-y-6">
          {/* 操作栏 */}
          <div className="flex items-center justify-end gap-3 pb-4 border-b border-white/5">
            <button
              type="button"
              className="btn-primary flex items-center gap-2"
              onClick={handleReanalyze}
              disabled={isReanalyzing}
            >
              {isReanalyzing ? (
                <>
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  分析中...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  重新分析
                </>
              )}
            </button>
          </div>

          {/* 报告内容 */}
          <ReportSummary data={report} isHistory />
        </div>
      ) : null}
    </Drawer>
  );
};
