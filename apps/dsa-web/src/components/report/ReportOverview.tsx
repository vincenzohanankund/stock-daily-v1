import React from 'react';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { Divider } from '../common/Divider';
import { Clock, TrendingUp, TrendingDown, Activity, Target, Shield, Zap, Eye } from 'lucide-react';
import type { ReportMeta, ReportSummary as ReportSummaryType, ReportStrategy } from '../../types/analysis';
import { formatDateTime } from '../../utils/format';
import { ScoreGauge } from '../common/ScoreGauge';

interface ReportOverviewProps {
  meta: ReportMeta;
  summary: ReportSummaryType;
  strategy?: ReportStrategy;
  isHistory?: boolean;
}

export const ReportOverview: React.FC<ReportOverviewProps> = ({
  meta,
  summary,
  strategy
}) => {
  const getPriceChangeColor = (changePct: number | undefined): string => {
    if (changePct === undefined || changePct === null) return 'text-muted-foreground';
    if (changePct > 0) return 'text-destructive';
    if (changePct < 0) return 'text-green-500';
    return 'text-muted-foreground';
  };

  const formatChangePct = (changePct: number | undefined): string => {
    if (changePct === undefined || changePct === null) return '--';
    const sign = changePct > 0 ? '+' : '';
    return `${sign}${changePct.toFixed(2)}%`;
  };

  const getTrendStyle = (trend: string) => {
    if (trend.includes('上涨') || trend.includes('看涨') || trend.includes('bullish') || trend.includes('多')) {
        return {
            bg: 'bg-destructive/5',
            border: 'border-destructive/10',
            text: 'text-destructive',
            icon: <TrendingUp className="w-4 h-4" />
        };
    }
    if (trend.includes('下跌') || trend.includes('看跌') || trend.includes('bearish') || trend.includes('空')) {
        return {
            bg: 'bg-green-500/5',
            border: 'border-green-500/10',
            text: 'text-green-600',
            icon: <TrendingDown className="w-4 h-4" />
        };
    }
    return {
        bg: 'bg-muted/30',
        border: 'border-border',
        text: 'text-muted-foreground',
        icon: <Activity className="w-4 h-4" />
    };
  };

  const getAdviceStyle = (advice: string) => {
    if (advice.includes('买')) {
        return {
            bg: 'bg-destructive/5',
            border: 'border-destructive/10',
            text: 'text-destructive',
            icon: <Target className="w-4 h-4" />
        };
    }
    if (advice.includes('卖')) {
        return {
            bg: 'bg-green-500/5',
            border: 'border-green-500/10',
            text: 'text-green-600',
            icon: <Zap className="w-4 h-4" />
        };
    }
    return {
        bg: 'bg-blue-500/5',
        border: 'border-blue-500/10',
        text: 'text-blue-600',
        icon: <Eye className="w-4 h-4" />
    };
  };

  const trendStyle = getTrendStyle(summary.trendPrediction || '');
  const adviceStyle = getAdviceStyle(summary.operationAdvice || '');

  return (
    <div className="mb-6 space-y-4">
      {/* Price Header - Compact & Information Dense */}
      <div className="flex items-center justify-between bg-card p-4 rounded-xl border border-border shadow-sm">
          <div className="flex items-center gap-3">
               <div className="flex flex-col">
                  <div className="flex items-baseline gap-2">
                    <h2 className="text-xl font-bold tracking-tight">{meta.stockName || meta.stockCode}</h2>
                    <span className="text-xs font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded border border-border/50">{meta.stockCode}</span>
                  </div>
                  <div className="flex items-center gap-1 mt-0.5">
                    <Clock size={10} className="text-muted-foreground" /> 
                    <span className="text-xs text-muted-foreground">{formatDateTime(meta.createdAt)}</span>
                  </div>
               </div>
          </div>
          {meta.currentPrice != null && (
              <div className="flex flex-col items-end">
                  <div className="flex items-baseline gap-2">
                      <span className={`text-2xl font-bold tracking-tight ${getPriceChangeColor(meta.changePct)}`}>
                          {meta.currentPrice.toFixed(2)}
                      </span>
                      {meta.changePct !== undefined && (
                          <Badge variant={meta.changePct > 0 ? 'destructive' : 'success'} className="text-xs px-1.5 py-0 h-5">
                              {formatChangePct(meta.changePct)}
                          </Badge>
                      )}
                  </div>
                  <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">最新价</span>
              </div>
          )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          {/* Left Column: Core Analysis & Strategy (3/5 width) */}
          <div className="lg:col-span-3 flex flex-col h-full">
               {/* Core Analysis Card */}
               <Card title="核心观点" className="border-l-4 border-l-primary/60 shadow-sm h-full flex flex-col">
                   <div className="flex-1">
                     <p className="text-sm leading-7 text-foreground/90 whitespace-pre-line text-justify font-normal">
                         {summary.analysisSummary || '暂无分析结论'}
                     </p>
                   </div>
                   
                   {/* Strategy Points Integrated at Bottom */}
                  {strategy && (
                    <div className="mt-6 pt-5 border-t border-border/50">
                       <div className="grid grid-cols-2 gap-3">
                           <div className="bg-muted/30 px-3 py-2.5 rounded-lg flex flex-row items-center justify-between border border-border/50">
                               <span className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground"><Target size={12} className="text-green-600 shrink-0" /> 理想买入</span>
                               <span className="text-sm text-green-600 font-bold font-mono leading-none">{strategy.idealBuy || '--'}</span>
                           </div>
                           <div className="bg-muted/30 px-3 py-2.5 rounded-lg flex flex-row items-center justify-between border border-border/50">
                               <span className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground"><Target size={12} className="text-blue-600 shrink-0" /> 二次买入</span>
                               <span className="text-sm text-blue-600 font-bold font-mono leading-none">{strategy.secondaryBuy || '--'}</span>
                           </div>
                           <div className="bg-muted/30 px-3 py-2.5 rounded-lg flex flex-row items-center justify-between border border-border/50">
                               <span className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground"><Shield size={12} className="text-destructive shrink-0" /> 止损价位</span>
                               <span className="text-sm text-destructive font-bold font-mono leading-none">{strategy.stopLoss || '--'}</span>
                           </div>
                           <div className="bg-muted/30 px-3 py-2.5 rounded-lg flex flex-row items-center justify-between border border-border/50">
                               <span className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground"><Zap size={12} className="text-yellow-600 shrink-0" /> 止盈目标</span>
                               <span className="text-sm text-yellow-600 font-bold font-mono leading-none">{strategy.takeProfit || '--'}</span>
                           </div>
                       </div>
                    </div>
                  )}
               </Card>
          </div>

          {/* Right Column: Market Sentiment & Decision (2/5 width) */}
          <div className="lg:col-span-2 flex flex-col h-full">
               <Card className="flex-1 flex flex-col shadow-sm border-t-4 border-t-secondary/60 relative overflow-hidden p-0">
                   {/* Background Gradient for subtle effect */}
                   <div className="absolute top-0 left-0 w-full h-24 bg-gradient-to-b from-muted/30 to-transparent pointer-events-none" />
                   
                   {/* Sentiment Section - Top Half */}
                   <div className="flex-1 flex flex-col items-center justify-center relative z-10 py-6">
                       <ScoreGauge score={summary.sentimentScore || 50} size="md" showLabel={true} />
                   </div>
                   
                   <div className="px-6">
                      <Divider className="my-0 border-dashed" />
                   </div>
                   
                   {/* Decision Section - Bottom Half */}
                   <div className="flex-1 px-6 py-6 flex flex-col justify-center gap-4">
                       <div className={`flex items-center justify-between p-4 rounded-xl border transition-transform hover:scale-[1.02] duration-200 ${trendStyle.bg} ${trendStyle.border}`}>
                           <span className="text-xs uppercase tracking-wider text-muted-foreground/80 font-medium">趋势预测</span>
                           <div className={`flex items-center gap-2 ${trendStyle.text}`}>
                               {trendStyle.icon}
                               <span className="text-base font-bold whitespace-nowrap">{summary.trendPrediction || '暂无'}</span>
                           </div>
                       </div>
                       
                       <div className={`flex items-center justify-between p-4 rounded-xl border transition-transform hover:scale-[1.02] duration-200 ${adviceStyle.bg} ${adviceStyle.border}`}>
                           <span className="text-xs uppercase tracking-wider text-muted-foreground/80 font-medium">操作建议</span>
                           <div className={`flex items-center gap-2 ${adviceStyle.text}`}>
                               {adviceStyle.icon}
                               <span className="text-base font-bold whitespace-nowrap">{summary.operationAdvice || '暂无'}</span>
                           </div>
                       </div>
                   </div>
               </Card>
          </div>
      </div>
    </div>
  );
};
