'use client';

import { useTranslations } from 'next-intl';
import { FileText, Hash, MessageSquare, AlertTriangle } from 'lucide-react';
import type { ContractAnalysisResponse } from '@/types/contract';

interface ResultsStatsProps {
  data: ContractAnalysisResponse;
}

export default function ResultsStats({ data }: ResultsStatsProps) {
  const t = useTranslations('results.stats');

  const stats = [
    {
      label: t('wordCount'),
      value: data.analysis.word_count.toLocaleString(),
      icon: Hash,
      bgColor: 'bg-blue-900/30',
      iconColor: 'text-blue-400',
    },
    {
      label: t('sentences'),
      value: data.analysis.sentences.toLocaleString(),
      icon: MessageSquare,
      bgColor: 'bg-purple-900/30',
      iconColor: 'text-purple-400',
    },
    {
      label: t('keyTerms'),
      value: data.analysis.key_terms.length.toString(),
      icon: FileText,
      bgColor: 'bg-emerald-900/30',
      iconColor: 'text-emerald-400',
    },
    {
      label: t('issues'),
      value: data.analysis.issues.length.toString(),
      icon: AlertTriangle,
      bgColor: 'bg-amber-900/30',
      iconColor: 'text-amber-400',
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="glass-card rounded-xl p-5 hover:shadow-lg hover:shadow-black/20 transition-all duration-300 animate-slide-up"
        >
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl ${stat.bgColor} flex items-center justify-center`}>
              <stat.icon className={`w-5 h-5 ${stat.iconColor}`} />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stat.value}</p>
              <p className="text-xs text-gray-500 mt-0.5">{stat.label}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}