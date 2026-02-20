import React from 'react';
import { PlayCircle, Eye, Trash2, TrendingUp, TrendingDown, Clock, Activity, ArrowUpCircle, ArrowDownCircle, MinusCircle, HelpCircle } from 'lucide-react';
import { Badge } from '../common/Badge';
import type { WatchlistItem } from '../../types/analysis';

interface StockCardProps {
  item: WatchlistItem;
  onAnalyze: (code: string) => void;
  onDetail: (code: string) => void;
  onDelete: (code: string) => void;
}

export const StockCard: React.FC<StockCardProps> = ({
  item,
  onAnalyze,
  onDetail,
  onDelete
}) => {
  const isUp = (item.changePct || 0) > 0;
  const isDown = (item.changePct || 0) < 0;
  const changeColorClass = isUp ? 'text-destructive' : isDown ? 'text-green-500' : 'text-muted-foreground';
  const borderColorClass = isUp ? 'border-t-destructive' : isDown ? 'border-t-green-500' : 'border-t-border';
  const bgGradientClass = isUp 
    ? 'bg-gradient-to-b from-destructive/5 to-transparent' 
    : isDown 
      ? 'bg-gradient-to-b from-green-500/5 to-transparent' 
      : 'bg-gradient-to-b from-muted/20 to-transparent';

  const getTrendIcon = (trend?: string) => {
    if (!trend) return null;
    if (trend.includes('涨') || trend.includes('多')) return <TrendingUp size={14} className="text-destructive shrink-0" />;
    if (trend.includes('跌') || trend.includes('空')) return <TrendingDown size={14} className="text-green-500 shrink-0" />;
    // 震荡或其他状态显示 Activity 图标
    return <Activity size={14} className="text-muted-foreground shrink-0" />;
  };

  const getAdviceIcon = (advice?: string) => {
    if (!advice) return <HelpCircle size={14} className="text-muted-foreground shrink-0" />;
    if (advice.includes('买')) return <ArrowUpCircle size={14} className="text-destructive shrink-0" />;
    if (advice.includes('卖')) return <ArrowDownCircle size={14} className="text-green-500 shrink-0" />;
    return <MinusCircle size={14} className="text-muted-foreground shrink-0" />;
  };

  return (
    <div className={`
      group relative bg-card rounded-xl border border-border shadow-sm hover:shadow-md transition-all duration-300 overflow-hidden flex flex-col
      border-t-4 ${borderColorClass}
    `}>
      {/* Background Gradient for subtle effect */}
      <div className={`absolute top-0 left-0 right-0 h-16 ${bgGradientClass} opacity-50 pointer-events-none`} />

      {/* Header Section */}
      <div className="p-3 pb-1 relative z-10 flex justify-between items-start">
        <div className="flex flex-col overflow-hidden w-full">
          <div className="flex items-center gap-2 w-full">
            <h3 className="font-bold text-lg tracking-tight leading-none truncate">{item.stockName || item.stockCode}</h3>
            {item.stockName && (
              <span className="text-[10px] font-mono text-muted-foreground bg-muted/50 px-1.5 py-0.5 rounded border border-border/50 shrink-0">
                {item.stockCode}
              </span>
            )}
          </div>
          <span className="text-[10px] text-muted-foreground mt-1 flex items-center gap-1">
            <Clock size={10} />
            {item.lastAnalysisTime ? new Date(item.lastAnalysisTime).toLocaleString('zh-CN', {
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            }) : '从未分析'}
          </span>
        </div>
        
        {/* Delete Button (visible on hover) */}
        <button 
          onClick={(e) => {
            e.stopPropagation();
            onDelete(item.stockCode);
          }}
          className="text-muted-foreground hover:text-destructive hover:bg-destructive/10 p-1.5 rounded-md opacity-0 group-hover:opacity-100 transition-opacity absolute right-2 top-2"
          title="删除自选"
        >
          <Trash2 size={14} />
        </button>
      </div>

      {/* Price Section */}
      <div className="px-3 py-1 relative z-10">
        <div className="flex items-baseline gap-2">
          <span className={`text-2xl font-bold tracking-tight ${changeColorClass}`}>
            {item.lastPrice?.toFixed(2) || '--'}
          </span>
          {item.changePct != null && (
            <Badge variant={isUp ? 'destructive' : 'success'} className="px-1.5 py-0 text-[10px] h-5 font-mono">
              {isUp ? '+' : ''}{item.changePct.toFixed(2)}%
            </Badge>
          )}
        </div>
      </div>

      {/* Strategy/Advice Section - Single Line Layout */}
      <div className="px-3 py-3 grid grid-cols-2 gap-2 flex-1">
        <div className="bg-muted/30 rounded-lg px-2.5 py-1.5 border border-border/50 flex items-center justify-between gap-2 overflow-hidden">
            <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider shrink-0 whitespace-nowrap">趋势</span>
            <div className="flex items-center gap-1.5 font-bold text-xs truncate">
                {getTrendIcon(item.trendPrediction)}
                <span className={`truncate whitespace-nowrap ${item.trendPrediction?.includes('涨') ? 'text-destructive' : item.trendPrediction?.includes('跌') ? 'text-green-500' : 'text-muted-foreground'}`}>
                    {item.trendPrediction || '--'}
                </span>
            </div>
        </div>
        <div className="bg-muted/30 rounded-lg px-2.5 py-1.5 border border-border/50 flex items-center justify-between gap-2 overflow-hidden">
            <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider shrink-0 whitespace-nowrap">建议</span>
            <div className="flex items-center gap-1.5 font-bold text-xs truncate">
                {getAdviceIcon(item.operationAdvice)}
                 {item.operationAdvice ? (
                    <span className={`truncate whitespace-nowrap ${
                        item.operationAdvice.includes('买') ? 'text-destructive' : 
                        item.operationAdvice.includes('卖') ? 'text-green-500' : 'text-foreground'
                    }`}>
                        {item.operationAdvice}
                    </span>
                ) : <span className="text-muted-foreground">--</span>}
            </div>
        </div>
      </div>

      {/* Actions Footer */}
      <div className="flex border-t border-border/50 bg-muted/10 divide-x divide-border/50">
        <button 
            onClick={() => onAnalyze(item.stockCode)}
            className="flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium text-muted-foreground hover:text-primary hover:bg-muted/30 transition-colors"
        >
            <PlayCircle size={14} />
            <span>重新分析</span>
        </button>
        <button 
            onClick={() => onDetail(item.stockCode)}
            className="flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium text-muted-foreground hover:text-primary hover:bg-muted/30 transition-colors"
        >
            <Eye size={14} />
            <span>详情</span>
        </button>
      </div>
    </div>
  );
};
