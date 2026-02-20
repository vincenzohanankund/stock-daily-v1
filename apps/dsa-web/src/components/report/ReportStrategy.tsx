import React from 'react';
import { Card } from '../common/Card';
import { Statistic } from '../common/Statistic';
import type { ReportStrategy as ReportStrategyType } from '../../types/analysis';

interface ReportStrategyProps {
  strategy?: ReportStrategyType;
}

export const ReportStrategy: React.FC<ReportStrategyProps> = ({ strategy }) => {
  if (!strategy) {
    return null;
  }

  return (
    <Card title="策略点位" className="mb-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        <div>
            <Statistic
                title="理想买入"
                value={strategy.idealBuy}
                valueClassName="text-green-600 font-bold"
            />
        </div>
        <div>
            <Statistic
                title="二次买入"
                value={strategy.secondaryBuy}
                valueClassName="text-blue-600 font-bold"
            />
        </div>
        <div>
            <Statistic
                title="止损价位"
                value={strategy.stopLoss}
                valueClassName="text-red-600 font-bold"
            />
        </div>
        <div>
            <Statistic
                title="止盈目标"
                value={strategy.takeProfit}
                valueClassName="text-yellow-600 font-bold"
            />
        </div>
      </div>
    </Card>
  );
};
