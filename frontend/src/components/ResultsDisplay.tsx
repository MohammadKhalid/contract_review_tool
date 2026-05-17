'use client';

import { useTranslations } from 'next-intl';
import { RefreshCw, Clock, FileText, CheckCircle2 } from 'lucide-react';
import type { ContractAnalysisResponse } from '@/types/contract';
import ResultsStats from './ResultsStats';
import IssuesList from './IssuesList';

interface ResultsDisplayProps {
  data: ContractAnalysisResponse;
  onReset: () => void;
}

export default function ResultsDisplay({ data, onReset }: ResultsDisplayProps) {
  const t = useTranslations('results');

  return (
    <div className="w-full max-w-4xl mx-auto space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">{t('title')}</h2>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2">
            <span className="flex items-center gap-1.5 text-sm text-gray-400">
              <FileText className="w-4 h-4 text-gray-500" />
              {t('filename', { filename: data.filename })}
            </span>
            <span className="flex items-center gap-1.5 text-sm text-gray-500">
              <Clock className="w-4 h-4 text-gray-500" />
              {data.processing_time_seconds}s
            </span>
            <span className="flex items-center gap-1.5 text-sm text-gray-500">
              <CheckCircle2 className="w-4 h-4 text-green-400" />
              {t('processingInfo', {
                method: data.processing_method,
                ocr: data.ocr_used,
                time: data.processing_time_seconds,
              })}
            </span>
          </div>
        </div>
        <button
          onClick={onReset}
          className="group flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 rounded-xl transition-all duration-200"
        >
          <RefreshCw className="w-4 h-4 group-hover:rotate-180 transition-transform duration-500" />
          New Analysis
        </button>
      </div>

      {/* Stats cards */}
      <section>
        <ResultsStats data={data} />
      </section>

      {/* Issues */}
      <section className="animate-slide-up">
        <h3 className="text-lg font-semibold text-white mb-4">{t('issues.title')}</h3>
        <IssuesList issues={data.analysis.issues} />
      </section>
    </div>
  );
}
