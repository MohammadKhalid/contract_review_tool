'use client';

import { useTranslations } from 'next-intl';
import { FileText, Hash, MessageSquare, AlertTriangle } from 'lucide-react';
import type { ContractAnalysisResponse } from '@/types/contract';

interface ResultsStatsProps {
  data: ContractAnalysisResponse;
}

export default function ResultsStats({ data }: ResultsStatsProps) {
  const t = useTranslations('results');

  const stats = [
    {
      label: t('stats.wordCount'),
      value: data.analysis.word_count.toLocaleString(),
      icon: Hash,
      color: 'from-blue-500 to-blue-600',
      bgColor: 'bg-blue-50',
      iconColor: 'text-blue-600',
    },
    {
      label: t('stats.sentences'),
      value: data.analysis.sentences.toLocaleString(),
      icon: MessageSquare,
      color: 'from-purple-500 to-purple-600',
      bgColor: 'bg-purple-50',
      iconColor: 'text-purple-600',
    },
    {
      label: t('keyTerms.title'),
      value: data.analysis.key_terms.length.toString(),
      icon: FileText,
      color: 'from-emerald-500 to-emerald-600',
      bgColor: 'bg-emerald-50',
      iconColor: 'text-emerald-600',
    },
    {
      label: t('issues.title'),
      value: data.analysis.issues.length.toString(),
      icon: AlertTriangle,
      color: 'from-amber-500 to-amber-600',
      bgColor: 'bg-amber-50',
      iconColor: 'text-amber-600',
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="glass-card rounded-xl p-5 hover:shadow-lg hover:shadow-blue-900/5 transition-all duration-300 animate-slide-up"
        >
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl ${stat.bgColor} flex items-center justify-center`}>
              <stat.icon className={`w-5 h-5 ${stat.iconColor}`} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              <p className="text-xs text-gray-500 mt-0.5">{stat.label}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}