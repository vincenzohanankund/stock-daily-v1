import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAnalysisStore } from '../stores/analysisStore';
import { ReportSummary } from '../components/report';
import { Button, Loading } from '../components/common';

const ReportPage: React.FC = () => {
  const { result, isLoading, error } = useAnalysisStore();
  const navigate = useNavigate();

  useEffect(() => {
    if (!result && !isLoading && !error) {
      navigate('/');
    }
  }, [result, isLoading, error, navigate]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh]">
        <Loading />
        <p className="mt-4 text-gray-600">正在生成分析报告...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">出错啦！</strong>
          <span className="block sm:inline"> {error}</span>
        </div>
        <div className="mt-4 text-center">
          <Button onClick={() => navigate('/')}>返回首页</Button>
        </div>
      </div>
    );
  }

  if (!result) {
    return null;
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">分析报告</h1>
        <Button variant="outline" onClick={() => navigate('/')}>
          返回首页
        </Button>
      </div>
      
      <ReportSummary data={result} />
    </div>
  );
};

export default ReportPage;
