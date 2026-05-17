'use client';

import { useTranslations } from 'next-intl';
import { X, RefreshCw, Clock, FileText, CheckCircle2 } from 'lucide-react';
import type { ContractAnalysisResponse } from '@/types/contract';
import ResultsStats from './ResultsStats';
import IssuesList from './IssuesList';
import EntitiesTable from './EntitiesTable';

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
          <h2 className="text-2xl font-bold text-gray-900">{t('title')}</h2>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2">
            <span className="flex items-center gap-1.5 text-sm text-gray-600">
              <FileText className="w-4 h-4 text-gray-400" />
              {t('filename', { filename: data.filename })}
            </span>
            <span className="flex items-center gap-1.5 text-sm text-gray-500">
              <Clock className="w-4 h-4 text-gray-400" />
              {data.processing_time_seconds}s
            </span>
            <span className="flex items-center gap-1.5 text-sm text-gray-500">
              <CheckCircle2 className="w-4 h-4 text-green-500" />
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
          className="group flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 rounded-xl transition-all duration-200"
        >
          <RefreshCw className="w-4 h-4 group-hover:rotate-180 transition-transform duration-500" />
          New Analysis
        </button>
      </div>

      {/* Stats cards */}
      <section>
        <ResultsStats data={data} />
      </section>

      {/* Key Terms */}
      {data.analysis.key_terms.length > 0 && (
        <section className="animate-slide-up">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">{t('keyTerms.title')}</h3>
          <div className="flex flex-wrap gap-2">
            {data.analysis.key_terms.map((term, index) => (
              <span
                key={index}
                className="px-3 py-1.5 bg-gradient-to-r from-blue-50 to-purple-50 text-blue-700 text-sm font-medium rounded-full border border-blue-100"
              >
                {term}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Entities */}
      {data.analysis.entities.length > 0 && (
        <section className="animate-slide-up">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">{t('entities.title')}</h3>
          <EntitiesTable entities={data.analysis.entities} />
        </section>
      )}

      {/* Issues */}
      <section className="animate-slide-up">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">{t('issues.title')}</h3>
        <IssuesList issues={data.analysis.issues} />
      </section>
    </div>
  );
}