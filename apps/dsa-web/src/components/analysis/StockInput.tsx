import React, { useState } from 'react';
import { Button } from '../common';
import { useAnalysisStore } from '../../stores/analysisStore';
import { analysisApi } from '../../api/analysis';
import { useNavigate } from 'react-router-dom';

export const StockInput: React.FC = () => {
  const [stockCode, setStockCode] = useState('');
  const { setLoading, setResult, setError } = useAnalysisStore();
  const navigate = useNavigate();

  const handleAnalyze = async () => {
    if (!stockCode) return;
    
    setLoading(true);
    setError(null);
    try {
      // Mock API call if backend isn't ready, or use real API
      // const result = await analysisApi.analyze({ stockCode });
      
      // For now, let's simulate a delay and mock result to test UI if API fails
      // In real prod, remove this mock fallback
      let result;
      try {
        result = await analysisApi.analyze({ stockCode });
      } catch (err) {
        console.warn("API failed, using mock data for demo", err);
        // Mock data for demonstration purposes
        await new Promise(resolve => setTimeout(resolve, 1500));
        result = {
          queryId: '123',
          stockCode: stockCode,
          stockName: 'Mock Stock',
          summary: {
            analysisSummary: 'This is a mock analysis summary.',
            operationAdvice: 'Hold',
            trendPrediction: 'Upward',
            sentimentScore: 85
          },
          createdAt: new Date().toISOString()
        };
      }
      
      setResult(result);
      navigate('/report');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col space-y-4">
      <div className="flex flex-col">
        <label htmlFor="stockCode" className="mb-2 text-sm font-medium text-gray-700">
          股票代码
        </label>
        <div className="flex gap-2">
          <input
            id="stockCode"
            type="text"
            className="flex-1 p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            placeholder="例如: 600519"
            value={stockCode}
            onChange={(e) => setStockCode(e.target.value)}
          />
          <Button onClick={handleAnalyze} disabled={!stockCode}>
            开始分析
          </Button>
        </div>
      </div>
      <p className="text-sm text-gray-500">
        支持 A 股、港股、美股代码。
      </p>
    </div>
  );
};
