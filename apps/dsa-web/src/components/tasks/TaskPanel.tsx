import React from 'react';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { Loader2, CheckCircle2, XCircle, Clock } from 'lucide-react';
import type { TaskInfo } from '../../types/analysis';

interface TaskPanelProps {
  tasks: TaskInfo[];
  visible?: boolean;
  title?: string;
  className?: string;
  variant?: 'card' | 'plain';
}

export const TaskPanel: React.FC<TaskPanelProps> = ({
  tasks,
  visible = true,
  title = '任务列表',
  className = '',
  variant = 'card',
}) => {
  if (!visible || tasks.length === 0) return null;

  const content = (
    <div className="flex flex-col divide-y divide-border">
      {tasks.map((task) => (
        <div key={task.taskId} className="flex items-start py-3 space-x-3 last:pb-0 first:pt-0">
           <div className="flex-shrink-0 mt-0.5">
             {task.status === 'processing' ? <Loader2 className="w-5 h-5 text-blue-500 animate-spin" /> :
              task.status === 'completed' ? <CheckCircle2 className="w-5 h-5 text-green-500" /> :
              task.status === 'failed' ? <XCircle className="w-5 h-5 text-red-500" /> :
              <Clock className="w-5 h-5 text-gray-400" />}
           </div>
           <div className="flex-1 min-w-0">
             <div className="flex justify-between items-center mb-1">
               <span className="font-medium text-sm truncate">{task.stockName || task.stockCode}</span>
               <Badge variant={
                  task.status === 'processing' ? 'info' :
                  task.status === 'completed' ? 'success' :
                  task.status === 'failed' ? 'destructive' : 'secondary'
               }>
                  {task.status === 'processing' ? '分析中' :
                   task.status === 'completed' ? '已完成' :
                   task.status === 'failed' ? '失败' : '等待中'}
               </Badge>
             </div>
             <div className="text-xs text-muted-foreground">{task.stockCode}</div>
             {task.message && <div className="text-xs text-muted-foreground mt-1">{task.message}</div>}
           </div>
        </div>
      ))}
    </div>
  );

  if (variant === 'plain') {
    return <div className={className}>{content}</div>;
  }

  return (
    <Card className={className} title={title}>
      {content}
    </Card>
  );
};
