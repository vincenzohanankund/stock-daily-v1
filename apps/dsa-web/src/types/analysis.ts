export interface AnalysisRequest {
  stockCode: string;
  reportType?: 'simple' | 'detailed';
}

export interface AnalysisResult {
  queryId: string;
  stockCode: string;
  stockName: string;
  summary: {
    analysisSummary: string;
    operationAdvice: string;
    trendPrediction: string;
    sentimentScore: number;
  };
  createdAt: string;
}
