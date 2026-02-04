import React from 'react';
import { Card } from '../components/common';
import { StockInput } from '../components/analysis';

const HomePage: React.FC = () => {
  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <h1 className="text-3xl font-bold text-center mb-8 text-gray-900">股票智能分析系统</h1>
      <Card title="开始分析">
        <StockInput />
      </Card>
      
      <div className="mt-8 text-center text-gray-500 text-sm">
        <p>基于 AI 大模型，整合多源数据进行深度分析</p>
      </div>
    </div>
  );
};

export default HomePage;
