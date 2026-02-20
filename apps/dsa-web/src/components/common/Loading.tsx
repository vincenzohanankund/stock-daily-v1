import React from 'react';
import { Spinner } from './Spinner';

export const Loading: React.FC = () => {
  return (
    <div className="flex justify-center items-center p-8 text-primary">
      <Spinner size="lg" />
    </div>
  );
};
