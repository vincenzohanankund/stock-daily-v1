import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';
import Button from '../components/common/Button';

const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="h-full flex flex-col items-center justify-center p-8 text-center">
      <div className="mb-8 p-6 bg-muted/20 rounded-full">
        <AlertTriangle size={64} className="text-yellow-500" />
      </div>
      <h1 className="text-4xl font-bold mb-4">404</h1>
      <p className="text-muted-foreground mb-8 text-lg">
        抱歉，您访问的页面不存在或已被移动
      </p>
      <Button variant="primary" onClick={() => navigate('/')}>
        返回首页
      </Button>
    </div>
  );
};

export default NotFoundPage;
