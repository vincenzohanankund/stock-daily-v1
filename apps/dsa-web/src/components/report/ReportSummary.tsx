import React from 'react';
import type { AnalysisResult } from '../../types/analysis';
import { Card } from '../common';

interface ReportSummaryProps {
  data: AnalysisResult;
}

export const ReportSummary: React.FC<ReportSummaryProps> = ({ data }) => {
  return (
    <div className="space-y-4">
      <Card title="基本信息">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <span className="text-gray-600">股票名称:</span>
            <span className="ml-2 font-medium">{data.stockName}</span>
          </div>
          <div>
            <span className="text-gray-600">代码:</span>
            <span className="ml-2 font-medium">{data.stockCode}</span>
          </div>
          <div>
            <span className="text-gray-600">情绪评分:</span>
            <span className="ml-2 font-medium text-blue-600">{data.summary.sentimentScore}</span>
          </div>
          <div>
            <span className="text-gray-600">时间:</span>
            <span className="ml-2 text-gray-500">{new Date(data.createdAt).toLocaleString()}</span>
          </div>
        </div>
      </Card>

      <Card title="分析摘要">
        <p className="text-gray-800 leading-relaxed whitespace-pre-wrap">
          {data.summary.analysisSummary}
        </p>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card title="操作建议">
          <p className="text-gray-800 font-medium">
            {data.summary.operationAdvice}
          </p>
        </Card>
        <Card title="趋势预测">
          <p className="text-gray-800 font-medium">
            {data.summary.trendPrediction}
          </p>
        </Card>
      </div>
    </div>
  );
};
