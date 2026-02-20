import React from 'react';
import type { AnalysisResult, AnalysisReport } from '../../types/analysis';
import { ReportOverview } from './ReportOverview';
import { ReportNews } from './ReportNews';
import { ReportDetails } from './ReportDetails';

interface ReportSummaryProps {
  data: AnalysisResult | AnalysisReport;
  isHistory?: boolean;
}

export const ReportSummary: React.FC<ReportSummaryProps> = ({
  data,
  isHistory = false,
}) => {
  const report: AnalysisReport = 'report' in data ? data.report : data;
  const queryId = 'queryId' in data ? data.queryId : report.meta.queryId;

  const { meta, summary, strategy, details } = report;

  return (
    <div className="animate-in fade-in duration-300">
      <ReportOverview
        meta={meta}
        summary={summary}
        strategy={strategy}
        isHistory={isHistory}
      />

      {/* ReportStrategy component content has been moved to ReportOverview for better density */}
      {/* <ReportStrategy strategy={strategy} /> */}

      <ReportNews queryId={queryId} />

      <ReportDetails details={details} queryId={queryId} />
    </div>
  );
};
