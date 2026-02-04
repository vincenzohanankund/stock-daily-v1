import React from 'react';
import { Card } from '../components/common';
import { HistoryList } from '../components/history';

const HistoryPage: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <h1 className="text-2xl font-bold mb-6 text-gray-900">历史记录</h1>
      <Card>
        <HistoryList />
      </Card>
    </div>
  );
};

export default HistoryPage;
