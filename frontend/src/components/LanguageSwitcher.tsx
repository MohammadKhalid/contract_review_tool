'use client';

import { usePathname, useRouter } from 'next/navigation';
import { useLocale } from 'next-intl';
import { useTransition } from 'react';

export default function LanguageSwitcher() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();

  const switchLocale = (newLocale: string) => {
    startTransition(() => {
      const segments = pathname.split('/');
      segments[1] = newLocale;
      const newPath = segments.join('/');
      router.replace(newPath, { scroll: false });
    });
  };

  return (
    <div className="flex items-center gap-1 bg-gray-800 rounded-lg p-0.5" role="radiogroup" aria-label="Switch language">
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
              ? 'bg-gray-700 text-white shadow-sm border border-gray-600/50'
              : 'text-gray-400 hover:text-gray-200 hover:bg-gray-700/50'
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