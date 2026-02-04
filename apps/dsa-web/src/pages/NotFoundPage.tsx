import React from 'react';
import { Link } from 'react-router-dom';

const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-[50vh] flex flex-col items-center justify-center text-center px-4">
      <h1 className="text-6xl font-bold text-gray-300 mb-4">404</h1>
      <p className="text-xl text-gray-600 mb-8">页面未找到</p>
      <Link to="/" className="text-blue-600 hover:underline">
        返回首页
      </Link>
    </div>
  );
};

export default NotFoundPage;
