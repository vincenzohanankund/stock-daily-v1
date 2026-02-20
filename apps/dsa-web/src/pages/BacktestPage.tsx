import React, { useState, useEffect, useCallback } from 'react';
import { ArrowUp, ArrowDown, Minus, PlayCircle, Filter, AlertCircle } from 'lucide-react';
import { backtestApi } from '../api/backtest';
import type {
  BacktestResultItem,
  BacktestRunResponse,
  PerformanceMetrics,
} from '../types/backtest';

import { Card } from '../components/common/Card';
import Input from '../components/common/Input';
import Button from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { Statistic } from '../components/common/Statistic';
import { Divider } from '../components/common/Divider';
import { Checkbox } from '../components/common/Checkbox';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/common/Table';
import { Pagination } from '../components/common/Pagination';
import { Spinner } from '../components/common/Spinner';
import { useToast } from '../components/common/Toast';

const BacktestPage: React.FC = () => {
  const [isRunning, setIsRunning] = useState(false);
  const [results, setResults] = useState<BacktestResultItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [overallPerf, setOverallPerf] = useState<PerformanceMetrics | null>(null);
  const [runResult, setRunResult] = useState<BacktestRunResponse | null>(null);

  // Form State
  const [filterCode, setFilterCode] = useState('');
  const [filterEvalDays, setFilterEvalDays] = useState('');
  const [forceRerun, setForceRerun] = useState(false);

  const toast = useToast();
  const pageSize = 20;

  const fetchResults = useCallback(async (page = 1, code?: string, windowDays?: number) => {
    setLoading(true);
    try {
      const response = await backtestApi.getResults({ 
          code: code || undefined, 
          evalWindowDays: windowDays, 
          page, 
          limit: pageSize 
      });
      setResults(response.items);
      setTotal(response.total);
      setCurrentPage(response.page);
    } catch (err) {
      console.error('Failed to fetch backtest results:', err);
      toast.error('获取回测结果失败');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  const fetchPerformance = useCallback(async (_code?: string, windowDays?: number) => {
    try {
      const overall = await backtestApi.getOverallPerformance(windowDays);
      setOverallPerf(overall);
    } catch (err) {
      console.error('Failed to fetch performance:', err);
    }
  }, []);

  useEffect(() => {
    const init = async () => {
      const overall = await backtestApi.getOverallPerformance();
      setOverallPerf(overall);
      const windowDays = overall?.evalWindowDays;
      if (windowDays) {
          setFilterEvalDays(String(windowDays));
      }
      fetchResults(1, undefined, windowDays);
    };
    init();
  }, [fetchResults]);

  const handleRun = async () => {
    const code = filterCode.trim() || undefined;
    const evalDays = filterEvalDays ? parseInt(filterEvalDays, 10) : undefined;

    setIsRunning(true);
    setRunResult(null);
    try {
      const response = await backtestApi.run({
        code,
        force: forceRerun || undefined,
        minAgeDays: forceRerun ? 0 : undefined,
        evalWindowDays: evalDays,
      });
      setRunResult(response);
      toast.success(`回测完成: ${response.completed} 已完成, ${response.processed} 已处理.`);
      
      fetchResults(1, code, evalDays);
      fetchPerformance(code, evalDays);
    } catch (err: any) {
      toast.error(err.message || '回测失败');
    } finally {
      setIsRunning(false);
    }
  };

  const handleFilter = () => {
    const evalDays = filterEvalDays ? parseInt(filterEvalDays, 10) : undefined;
    fetchResults(1, filterCode, evalDays);
  };

  const renderStatusTag = (val: string) => {
    if (!val) return <span className="text-muted-foreground">--</span>;
    // Chinese market convention: Red (destructive) is Up, Green (success) is Down
    const color = val.includes('up') ? 'destructive' : val.includes('down') ? 'success' : 'secondary';
    return <Badge variant={color}>{val}</Badge>;
  };

  return (
    <div className="h-full flex flex-col lg:flex-row gap-6 p-6 overflow-hidden bg-background">
      {/* 1. Left Sidebar: Overall Performance */}
      <div className="w-full lg:w-80 flex-shrink-0 flex flex-col gap-6 overflow-hidden">
        <Card 
          className="h-full flex flex-col border-border shadow-sm"
          title={<div className="flex items-center gap-2"><span className="font-semibold">性能概览</span></div>}
        >
          <div className="flex-1 overflow-y-auto pr-2 space-y-6">
            {overallPerf ? (
              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                    <Statistic 
                        title="准确率" 
                        value={overallPerf.directionAccuracyPct} 
                        precision={1} 
                        suffix="%" 
                        valueClassName="text-xl font-bold text-foreground"
                    />
                    <Statistic 
                        title="胜率" 
                        value={overallPerf.winRatePct} 
                        precision={1} 
                        suffix="%" 
                        valueClassName="text-xl font-bold text-red-500"
                    />
                </div>

                <div className="p-4 rounded-lg bg-muted/50 space-y-4">
                    <Statistic 
                        title="平均模拟收益" 
                        value={overallPerf.avgSimulatedReturnPct} 
                        precision={2} 
                        suffix="%" 
                        valueClassName={`text-2xl font-bold ${(overallPerf.avgSimulatedReturnPct || 0) > 0 ? 'text-red-500' : 'text-green-500'}`}
                    />
                    <div className="grid grid-cols-2 gap-4">
                        <Statistic 
                            title="平均个股收益" 
                            value={overallPerf.avgStockReturnPct} 
                            precision={2} 
                            suffix="%" 
                            valueClassName="text-lg"
                        />
                        <Statistic 
                            title="平均持有天数" 
                            value={overallPerf.avgDaysToFirstHit} 
                            precision={1} 
                            valueClassName="text-lg"
                        />
                    </div>
                </div>

                <div className="space-y-3">
                    <h4 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">触发条件</h4>
                    <div className="grid grid-cols-2 gap-4">
                        <Statistic 
                            title="止损触发率" 
                            value={overallPerf.stopLossTriggerRate} 
                            precision={1} 
                            suffix="%" 
                            valueClassName="text-lg"
                        />
                        <Statistic 
                            title="止盈触发率" 
                            value={overallPerf.takeProfitTriggerRate} 
                            precision={1} 
                            suffix="%" 
                            valueClassName="text-lg"
                        />
                    </div>
                </div>
                
                <Divider className="border-dashed" />
                
                <div className="space-y-2">
                    <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">评估次数</span>
                        <Badge variant="outline" className="font-mono">{overallPerf.completedCount} / {overallPerf.totalEvaluations}</Badge>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">胜 / 负 / 平</span>
                        <div className="flex gap-1">
                            <span className="text-red-500 font-bold">{overallPerf.winCount}</span>
                            <span className="text-muted-foreground">/</span>
                            <span className="text-green-500 font-bold">{overallPerf.lossCount}</span>
                            <span className="text-muted-foreground">/</span>
                            <span className="text-foreground">{overallPerf.neutralCount}</span>
                        </div>
                    </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-40 text-muted-foreground">
                <AlertCircle size={24} className="mb-2 opacity-50" />
                <span>暂无性能数据</span>
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* 2. Right Content: Filter & Table */}
      <div className="flex-1 flex flex-col overflow-hidden gap-4 min-w-0">
        {/* Filter Bar */}
        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center bg-card p-4 rounded-lg border border-border shadow-sm">
            <div className="flex-1 w-full sm:w-auto flex gap-3">
                <div className="relative flex-1 max-w-xs">
                    <Input 
                        placeholder="按股票代码筛选..." 
                        value={filterCode}
                        onChange={(e) => setFilterCode(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleFilter()}
                        className="w-full"
                    />
                </div>
                <div className="w-24">
                     <Input 
                        placeholder="天数" 
                        value={filterEvalDays}
                        onChange={(e) => setFilterEvalDays(e.target.value)}
                        className="w-full"
                    />
                </div>
            </div>
            
            <div className="flex items-center gap-4 w-full sm:w-auto justify-between sm:justify-end">
                <Checkbox 
                    label="强制重测" 
                    checked={forceRerun} 
                    onChange={(e) => setForceRerun(e.target.checked)} 
                />
                <div className="flex gap-2">
                    <Button variant="secondary" onClick={handleFilter} icon={<Filter size={16} />}>
                        筛选
                    </Button>
                    <Button variant="primary" onClick={handleRun} loading={isRunning} icon={<PlayCircle size={16} />}>
                        开始回测
                    </Button>
                </div>
            </div>
        </div>

        {/* Run Summary (if available) */}
        {runResult && (
            <div className="px-4 py-3 bg-muted/50 rounded-lg border border-border flex flex-wrap gap-x-8 gap-y-2 text-sm shadow-sm animate-in fade-in slide-in-from-top-2">
                <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">已处理:</span>
                    <span className="font-mono font-medium">{runResult.processed}</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">已保存:</span>
                    <span className="font-mono font-medium">{runResult.saved}</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">已完成:</span>
                    <span className="font-mono font-medium text-green-600 dark:text-green-400">{runResult.completed}</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">数据不足:</span>
                    <span className="font-mono font-medium text-yellow-600 dark:text-yellow-400">{runResult.insufficient}</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">错误:</span>
                    <span className="font-mono font-medium text-destructive">{runResult.errors}</span>
                </div>
            </div>
        )}

        {/* Results Table */}
        <div className="flex-1 flex flex-col min-h-0 bg-card rounded-lg border border-border shadow-sm overflow-hidden">
            <div className="flex-1 overflow-auto">
                <Table>
                    <TableHeader>
                        <TableRow className="bg-muted/50 hover:bg-muted/50">
                            <TableHead className="w-[100px]">代码</TableHead>
                            <TableHead className="w-[120px]">日期</TableHead>
                            <TableHead>建议</TableHead>
                            <TableHead>方向</TableHead>
                            <TableHead>结果</TableHead>
                            <TableHead className="text-right">收益</TableHead>
                            <TableHead className="text-right">止损</TableHead>
                            <TableHead className="text-right">Take Profit</TableHead>
                            <TableHead className="text-center">Status</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {loading ? (
                            <TableRow>
                                <TableCell colSpan={9} className="h-32 text-center">
                                    <div className="flex flex-col items-center justify-center gap-2 text-muted-foreground">
                                        <Spinner size="md" />
                                        <span>Loading results...</span>
                                    </div>
                                </TableCell>
                            </TableRow>
                        ) : results.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={9} className="h-32 text-center text-muted-foreground">
                                    No backtest results found
                                </TableCell>
                            </TableRow>
                        ) : (
                            results.map((item) => (
                                <TableRow key={item.analysisHistoryId}>
                                    <TableCell className="font-medium font-mono">{item.code}</TableCell>
                                    <TableCell className="text-muted-foreground text-xs">{item.analysisDate}</TableCell>
                                    <TableCell>
                                        <Badge variant="secondary" className="font-normal">{item.operationAdvice || '--'}</Badge>
                                    </TableCell>
                                    <TableCell>
                                        {renderStatusTag(item.directionExpected || '')}
                                    </TableCell>
                                    <TableCell>
                                        {item.outcome === 'win' ? (
                                            <Badge variant="destructive" className="gap-1 pl-1 pr-2"><ArrowUp size={12} /> WIN</Badge>
                                        ) : item.outcome === 'loss' ? (
                                            <Badge variant="success" className="gap-1 pl-1 pr-2"><ArrowDown size={12} /> LOSS</Badge>
                                        ) : (
                                            <Badge variant="secondary" className="gap-1 pl-1 pr-2"><Minus size={12} /> FLAT</Badge>
                                        )}
                                    </TableCell>
                                    <TableCell className="text-right">
                                        {(item.simulatedReturnPct !== undefined && item.simulatedReturnPct !== null) ? (
                                            <div className={`flex items-center justify-end gap-1 font-mono font-medium ${item.simulatedReturnPct > 0 ? 'text-destructive' : 'text-green-500'}`}>
                                                {item.simulatedReturnPct > 0 ? <ArrowUp size={14} /> : <ArrowDown size={14} />}
                                                {item.simulatedReturnPct.toFixed(2)}%
                                            </div>
                                        ) : <span className="text-muted-foreground">--</span>}
                                    </TableCell>
                                    <TableCell className="text-right font-mono text-sm text-muted-foreground">{item.stopLoss?.toFixed(2) || '--'}</TableCell>
                                    <TableCell className="text-right font-mono text-sm text-muted-foreground">{item.takeProfit?.toFixed(2) || '--'}</TableCell>
                                    <TableCell className="text-center"><Badge variant="outline" className="text-xs">{item.evalStatus}</Badge></TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </div>
            
            <div className="p-4 border-t border-border bg-muted/20">
                <Pagination 
                    currentPage={currentPage} 
                    totalPages={Math.ceil(total / pageSize)} 
                    onPageChange={(page) => {
                        const evalDays = filterEvalDays ? parseInt(filterEvalDays, 10) : undefined;
                        fetchResults(page, filterCode, evalDays);
                    }} 
                />
            </div>
        </div>
      </div>
    </div>
  );
};

export default BacktestPage;
