'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Scale,
  FileText,
  Percent,
  Bot,
  Shield,
  AlertOctagon,
} from 'lucide-react';
import type { ContractIssue } from '@/types/contract';
import clsx from 'clsx';

interface IssuesListProps {
  issues: ContractIssue[];
}

const riskConfig = {
  high: {
    bg: 'bg-red-950/30 border-red-800/30',
    badge: 'bg-red-900/50 text-red-300 border-red-800/30',
    icon: 'text-red-400',
    hover: 'hover:border-red-700/50',
  },
  medium: {
    bg: 'bg-amber-950/30 border-amber-800/30',
    badge: 'bg-amber-900/50 text-amber-300 border-amber-800/30',
    icon: 'text-amber-400',
    hover: 'hover:border-amber-700/50',
  },
  low: {
    bg: 'bg-green-950/30 border-green-800/30',
    badge: 'bg-green-900/50 text-green-300 border-green-800/30',
    icon: 'text-green-400',
    hover: 'hover:border-green-700/50',
  },
};

const methodLabels: Record<string, { label: string; icon: typeof Bot }> = {
  rule_based: { label: 'Rule-based', icon: Shield },
  llm: { label: 'LLM Judge', icon: Bot },
  ocr_error: { label: 'OCR Error', icon: AlertOctagon },
};

export default function IssuesList({ issues }: IssuesListProps) {
  const t = useTranslations('results');
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  if (issues.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400 animate-fade-in">
        <AlertTriangle className="w-12 h-12 mx-auto mb-3 text-green-500" />
        <p className="font-medium">{t('noIssues')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle className="w-5 h-5 text-amber-400" />
        <p className="text-sm font-medium text-gray-300">
          {t('issues.count', { count: issues.length })}
        </p>
      </div>

      {issues.map((issue, index) => {
        const risk = (issue.risk_level?.toLowerCase() || 'low') as keyof typeof riskConfig;
        const config = riskConfig[risk] || riskConfig.low;
        const isExpanded = expandedIndex === index;
        const methodInfo = issue.detection_method
          ? methodLabels[issue.detection_method] || null
          : null;

        return (
          <div
            key={index}
            className={clsx(
              'rounded-xl border p-5 transition-all duration-200 animate-slide-up cursor-pointer bg-gray-900/40 backdrop-blur-sm',
              config.bg,
              config.hover
            )}
            style={{ animationDelay: `${index * 100}ms` }}
            onClick={() => setExpandedIndex(isExpanded ? null : index)}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <span className={clsx('px-2.5 py-0.5 rounded-full text-xs font-semibold border', config.badge)}>
                    {t(`issues.risk.${risk}`)}
                  </span>
                  {methodInfo && (
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium border border-gray-600/30 bg-gray-800/40 text-gray-400 flex items-center gap-1">
                      <methodInfo.icon className="w-3 h-3" />
                      {methodInfo.label}
                    </span>
                  )}
                </div>
                <p className="font-medium text-gray-200">{issue.description}</p>
                {(issue.confidence !== undefined || issue.exact_quote) && (
                  <div className="flex items-center gap-3 mt-1.5">
                    {issue.confidence !== undefined && (
                      <span className="text-xs text-gray-500">
                        Confidence: {(issue.confidence * 100).toFixed(0)}%
                      </span>
                    )}
                    {issue.exact_quote && (
                      <span className="text-xs text-gray-500 truncate max-w-[300px]">
                        &ldquo;{issue.exact_quote.slice(0, 80)}&rdquo;
                      </span>
                    )}
                  </div>
                )}
              </div>
              <button className="flex-shrink-0 p-1 text-gray-500 hover:text-gray-300 transition-colors">
                {isExpanded ? (
                  <ChevronUp className="w-5 h-5" />
                ) : (
                  <ChevronDown className="w-5 h-5" />
                )}
              </button>
            </div>

            {/* Expanded details */}
            {isExpanded && (
              <div className="mt-4 pt-4 border-t border-gray-700/50 space-y-3 animate-fade-in">
                {issue.legal_basis && (
                  <div className="flex items-start gap-3">
                    <Scale className="w-4 h-4 text-gray-500 mt-0.5" />
                    <div>
                      <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">
                        {t('issues.legalBasis')}
                      </p>
                      <p className="text-sm text-gray-300">{issue.legal_basis}</p>
                    </div>
                  </div>
                )}

                {issue.legal_citation && (
                  <div className="flex items-start gap-3">
                    <Scale className="w-4 h-4 text-blue-400 mt-0.5" />
                    <div>
                      <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">
                        Legal Citation
                      </p>
                      <p className="text-sm text-blue-300 font-mono">{issue.legal_citation}</p>
                    </div>
                  </div>
                )}

                {issue.exact_quote && (
                  <div className="flex items-start gap-3">
                    <FileText className="w-4 h-4 text-amber-400 mt-0.5" />
                    <div>
                      <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">
                        Exact Quote
                      </p>
                      <div className="bg-gray-800/60 rounded-lg p-3 border border-amber-800/30">
                        <p className="text-sm text-amber-200 italic">
                          &ldquo;{issue.exact_quote}&rdquo;
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {issue.clause_snippet && !issue.exact_quote && (
                  <div className="flex items-start gap-3">
                    <FileText className="w-4 h-4 text-gray-500 mt-0.5" />
                    <div>
                      <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">
                        {t('issues.clauseSnippet')}
                      </p>
                      <div className="bg-gray-800/60 rounded-lg p-3 border border-gray-700/50">
                        <p className="text-sm text-gray-300 italic">
                          &ldquo;{issue.clause_snippet}&rdquo;
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {(issue.similarity !== undefined || issue.confidence !== undefined) && (
                  <div className="flex items-start gap-3">
                    <Percent className="w-4 h-4 text-gray-500 mt-0.5" />
                    <div>
                      <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">
                        {issue.confidence !== undefined
                          ? `LLM Confidence: ${(issue.confidence * 100).toFixed(1)}%`
                          : t('issues.similarity', { score: Math.round(issue.similarity! * 100) })}
                      </p>
                    </div>
                  </div>
                )}

                {issue.detection_method === 'ocr_error' && (
                  <div className="flex items-start gap-3">
                    <AlertOctagon className="w-4 h-4 text-red-400 mt-0.5" />
                    <div>
                      <p className="text-xs font-medium text-red-400 uppercase tracking-wider mb-1">
                        Action Required
                      </p>
                      <p className="text-sm text-gray-300">
                        This section may have OCR quality issues. Manual review is recommended.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}