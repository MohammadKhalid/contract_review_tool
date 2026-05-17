'use client';

import { usePathname, useRouter } from 'next/navigation';
import { useLocale, useTranslations } from 'next-intl';
import { useTransition } from 'react';

export default function LanguageSwitcher() {
  const t = useTranslations('language');
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();

  const switchLocale = (newLocale: string) => {
    startTransition(() => {
      const newPath = pathname.replace(`/${locale}`, `/${newLocale}`);
      router.push(newPath);
    });
  };

  return (
    <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-0.5" role="radiogroup" aria-label={t('switch')}>
      {(['de', 'en'] as const).map((lang) => (
        <button
          key={lang}
          onClick={() => switchLocale(lang)}
          disabled={isPending}
          role="radio"
          aria-checked={locale === lang}
          className={`
            px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200
            ${locale === lang
              ? 'bg-white text-blue-600 shadow-sm border border-gray-200'
              : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
            }
            disabled:opacity-50 disabled:cursor-not-allowed
          `}
        >
          {lang === 'de' ? 'DE' : 'EN'}
        </button>
      ))}
    </div>
  );
}