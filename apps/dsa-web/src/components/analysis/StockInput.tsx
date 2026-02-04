import React, { useState, useCallback } from 'react';
import { useAnalysisStore } from '../../stores/analysisStore';
import { analysisApi } from '../../api/analysis';
import { validateStockCode } from '../../utils/validation';
import { useNavigate } from 'react-router-dom';

/**
 * 股票分析输入组件 - 简洁终端风格
 * 移除报告类型选择，默认完整报告
 */
export const StockInput: React.FC = () => {
  const [stockCode, setStockCode] = useState('');
  const [validationError, setValidationError] = useState<string | undefined>();
  const [isTouched, setIsTouched] = useState(false);

  const { isLoading, setLoading, setResult, setError } = useAnalysisStore();
  const navigate = useNavigate();

  // 实时校验
  const handleInputChange = useCallback((value: string) => {
    setStockCode(value);
    if (isTouched && value) {
      const { valid, message } = validateStockCode(value);
      setValidationError(valid ? undefined : message);
    } else if (!value) {
      setValidationError(undefined);
    }
  }, [isTouched]);

  const handleBlur = useCallback(() => {
    setIsTouched(true);
    if (stockCode) {
      const { valid, message } = validateStockCode(stockCode);
      setValidationError(valid ? undefined : message);
    }
  }, [stockCode]);

  // 提交分析
  const handleAnalyze = async () => {
    const { valid, message, normalized } = validateStockCode(stockCode);

    if (!valid) {
      setValidationError(message);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await analysisApi.analyze({
        stockCode: normalized,
        reportType: 'detailed', // 固定使用完整报告
      });

      setResult(result);
      navigate('/report');
    } catch (err) {
      console.error('Analysis failed:', err);
      setError(err instanceof Error ? err.message : '分析请求失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  // 键盘回车提交
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && stockCode && !validationError && !isLoading) {
      handleAnalyze();
    }
  };

  const isValid = stockCode && !validationError;

  return (
    <div className="space-y-5">
      {/* 输入区域 */}
      <div className="space-y-3">
        <div className="relative">
          <input
            id="stockCode"
            type="text"
            value={stockCode}
            onChange={(e) => handleInputChange(e.target.value.toUpperCase())}
            onBlur={handleBlur}
            onKeyDown={handleKeyDown}
            placeholder="输入股票代码，例如 600519"
            disabled={isLoading}
            autoComplete="off"
            className={`
              input-terminal pr-12
              ${validationError
                ? 'border-danger/50 focus:border-danger/60'
                : isValid
                  ? 'border-success/30 focus:border-success/50'
                  : ''
              }
            `}
          />

          {/* 状态图标 */}
          {stockCode && (
            <div className="absolute inset-y-0 right-0 flex items-center pr-4">
              {validationError ? (
                <svg className="w-5 h-5 text-danger" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : isValid ? (
                <svg className="w-5 h-5 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              ) : null}
            </div>
          )}
        </div>

        {/* 错误提示 */}
        {validationError && (
          <p className="text-sm text-danger flex items-center gap-2 animate-fade-in">
            <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            {validationError}
          </p>
        )}

        {/* 支持格式提示 */}
        <p className="text-xs text-muted">
          支持 A股 · 港股 · 美股
        </p>
      </div>

      {/* 分析按钮 */}
      <button
        onClick={handleAnalyze}
        disabled={!isValid || isLoading}
        className="btn-primary w-full flex items-center justify-center gap-2"
      >
        {isLoading ? (
          <>
            <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            分析中...
          </>
        ) : (
          <>
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            开始分析
          </>
        )}
      </button>

      {/* 加载提示 */}
      {isLoading && (
        <div className="text-center text-sm text-secondary animate-pulse">
          AI 正在深度分析中，预计需要 10-30 秒...
        </div>
      )}
    </div>
  );
};
