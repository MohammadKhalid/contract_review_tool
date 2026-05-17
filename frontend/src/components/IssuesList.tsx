'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { AlertTriangle, ChevronDown, ChevronUp, Scale, FileText, Percent } from 'lucide-react';
import type { ContractIssue } from '@/types/contract';
import clsx from 'clsx';

interface IssuesListProps {
  issues: ContractIssue[];
}

const riskConfig = {
  high: {
    bg: 'bg-red-50 border-red-200',
    badge: 'bg-red-100 text-red-700',
    icon: 'text-red-500',
    hover: 'hover:border-red-300',
  },
  medium: {
    bg: 'bg-amber-50 border-amber-200',
    badge: 'bg-amber-100 text-amber-700',
    icon: 'text-amber-500',
    hover: 'hover:border-amber-300',
  },
  low: {
    bg: 'bg-green-50 border-green-200',
    badge: 'bg-green-100 text-green-700',
    icon: 'text-green-500',
    hover: 'hover:border-green-300',
  },
};

export default function IssuesList({ issues }: IssuesListProps) {
  const t = useTranslations('results');
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  if (issues.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500 animate-fade-in">
        <AlertTriangle className="w-12 h-12 mx-auto mb-3 text-green-400" />
        <p className="font-medium">{t('noIssues')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle className="w-5 h-5 text-amber-500" />
        <p className="text-sm font-medium text-gray-700">
          {t('count', { count: issues.length })}
        </p>
      </div>

      {issues.map((issue, index) => {
        const risk = (issue.risk_level?.toLowerCase() || 'low') as keyof typeof riskConfig;
        const config = riskConfig[risk] || riskConfig.low;
        const isExpanded = expandedIndex === index;

        return (
          <div
            key={index}
            className={clsx(
              'glass-card rounded-xl border p-5 transition-all duration-200 animate-slide-up cursor-pointer',
              config.bg,
              config.hover
            )}
            style={{ animationDelay: `${index * 100}ms` }}
            onClick={() => setExpandedIndex(isExpanded ? null : index)}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <span className={clsx('px-2.5 py-0.5 rounded-full text-xs font-semibold', config.badge)}>
                    {t(`risk.${risk}`)}
                  </span>
                </div>
                <p className="font-medium text-gray-900">{issue.description}</p>
              </div>
              <button className="flex-shrink-0 p-1 text-gray-400 hover:text-gray-600 transition-colors">
                {isExpanded ? (
                  <ChevronUp className="w-5 h-5" />
                ) : (
                  <ChevronDown className="w-5 h-5" />
                )}
              </button>
            </div>

            {/* Expanded details */}
            {isExpanded && (
              <div className="mt-4 pt-4 border-t border-gray-200/60 space-y-3 animate-fade-in">
                {issue.legal_basis && (
                  <div className="flex items-start gap-3">
                    <Scale className="w-4 h-4 text-gray-400 mt-0.5" />
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">
                        {t('legalBasis')}
                      </p>
                      <p className="text-sm text-gray-700">{issue.legal_basis}</p>
                    </div>
                  </div>
                )}

                {issue.clause_snippet && (
                  <div className="flex items-start gap-3">
                    <FileText className="w-4 h-4 text-gray-400 mt-0.5" />
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">
                        {t('clauseSnippet')}
                      </p>
                      <div className="bg-white/60 rounded-lg p-3 border border-gray-200/60">
                        <p className="text-sm text-gray-600 italic">
                          &ldquo;{issue.clause_snippet}&rdquo;
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {issue.similarity !== undefined && (
                  <div className="flex items-start gap-3">
                    <Percent className="w-4 h-4 text-gray-400 mt-0.5" />
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">
                        {t('similarity', { score: Math.round(issue.similarity * 100) })}
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