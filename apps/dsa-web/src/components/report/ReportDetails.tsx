import React from 'react';
import Card from '../common/Card';
import { Collapse } from '../common/Collapse';
import Button from '../common/Button';
import { Copy } from 'lucide-react';
import type { ReportDetails as ReportDetailsType } from '../../types/analysis';

interface ReportDetailsProps {
  details?: ReportDetailsType;
  queryId?: string;
}

export const ReportDetails: React.FC<ReportDetailsProps> = ({
  details,
  queryId,
}) => {
  if (!details?.rawResult && !details?.contextSnapshot && !queryId) {
    return null;
  }

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      console.log('Copied to clipboard');
    });
  };

  const renderJson = (data: unknown) => {
    const jsonStr = JSON.stringify(data, null, 2);
    return (
      <div className="relative">
        <Button
          variant="ghost"
          size="sm"
          className="absolute top-2 right-2 h-6 w-6 p-0"
          onClick={(e: React.MouseEvent) => {
              e.stopPropagation();
              handleCopy(jsonStr);
          }}
        >
            <Copy size={14} />
        </Button>
        <pre className="m-0 p-3 bg-muted rounded overflow-auto max-h-[400px] text-xs font-mono">
          {jsonStr}
        </pre>
      </div>
    );
  };

  return (
    <Card title="数据追溯" className="mb-4">
      {queryId && (
        <div className="mb-4 text-sm">
          <span className="text-muted-foreground">Query ID: </span>
          <code className="bg-muted px-1 py-0.5 rounded text-xs">{queryId}</code>
        </div>
      )}
      <Collapse accordion>
        <Collapse.Item header="原始分析结果" name="1">
          {details?.rawResult ? renderJson(details.rawResult) : <div>无数据</div>}
        </Collapse.Item>
        <Collapse.Item header="分析上下文快照" name="2">
          {details?.contextSnapshot ? renderJson(details.contextSnapshot) : <div>无数据</div>}
        </Collapse.Item>
        {details?.newsContent && (
             <Collapse.Item header="新闻内容" name="3">
                 <p className="whitespace-pre-wrap text-sm">
                     {details.newsContent}
                 </p>
             </Collapse.Item>
        )}
      </Collapse>
    </Card>
  );
};
