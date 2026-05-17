'use client';

import { useTranslations } from 'next-intl';
import { User, Building2, DollarSign, Calendar, MapPin, Scale, Percent, AlertCircle } from 'lucide-react';
import type { NamedEntity } from '@/types/contract';

interface EntitiesTableProps {
  entities: NamedEntity[];
}

const labelConfig: Record<string, { icon: React.ReactNode; color: string; bgColor: string }> = {
  PERSON: {
    icon: <User className="w-3.5 h-3.5" />,
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
  },
  ORG: {
    icon: <Building2 className="w-3.5 h-3.5" />,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
  },
  MONEY: {
    icon: <DollarSign className="w-3.5 h-3.5" />,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
  },
  DATE: {
    icon: <Calendar className="w-3.5 h-3.5" />,
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
  },
  LOC: {
    icon: <MapPin className="w-3.5 h-3.5" />,
    color: 'text-rose-600',
    bgColor: 'bg-rose-50',
  },
  LAW: {
    icon: <Scale className="w-3.5 h-3.5" />,
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-50',
  },
  PERCENT: {
    icon: <Percent className="w-3.5 h-3.5" />,
    color: 'text-cyan-600',
    bgColor: 'bg-cyan-50',
  },
  GPE: {
    icon: <MapPin className="w-3.5 h-3.5" />,
    color: 'text-teal-600',
    bgColor: 'bg-teal-50',
  },
};

export default function EntitiesTable({ entities }: EntitiesTableProps) {
  const t = useTranslations('results.entities.table');

  const getLabelTranslation = (label: string): string => {
    const key = label.toLowerCase() as keyof typeof t;
    try {
      return t(key);
    } catch {
      return label;
    }
  };

  const getConfig = (label: string) => {
    const upperLabel = label.toUpperCase();
    return labelConfig[upperLabel] || {
      icon: <AlertCircle className="w-3.5 h-3.5" />,
      color: 'text-gray-600',
      bgColor: 'bg-gray-50',
    };
  };

  return (
    <div className="glass-card rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wider">
                {t('text')}
              </th>
              <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wider">
                {t('label')}
              </th>
            </tr>
          </thead>
          <tbody>
            {entities.map((entity, index) => {
              const config = getConfig(entity.label);
              return (
                <tr
                  key={index}
                  className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors last:border-0 animate-fade-in"
                  style={{ animationDelay: `${index * 50}ms` }}
                >
                  <td className="py-3 px-4">
                    <span className="font-medium text-gray-900">{entity.text}</span>
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.bgColor} ${config.color}`}
                    >
                      {config.icon}
                      {getLabelTranslation(entity.label)}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}