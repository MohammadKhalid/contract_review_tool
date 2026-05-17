import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { NextIntlClientProvider } from 'next-intl';
import { getMessages } from 'next-intl/server';
import { notFound } from 'next/navigation';
import '../globals.css';
import LanguageSwitcher from '@/components/LanguageSwitcher';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

const locales = ['en', 'de'];

export const metadata: Metadata = {
  title: 'Rental Contract Review Tool | Mietvertrags-Prüfungstool',
  description:
    'AI-powered analysis of German rental contracts for invalid clauses. KI-gestützte Analyse deutscher Mietverträge auf ungültige Klauseln.',
};

export default async function LocaleLayout({
  children,
  params: { locale },
}: {
  children: React.ReactNode;
  params: { locale: string };
}) {
  if (!locales.includes(locale)) {
    notFound();
  }

  const messages = await getMessages();

  return (
    <html lang={locale} className={`${inter.variable} scroll-smooth dark`}>
      <body className="font-sans" style={{ fontFamily: 'var(--font-inter), system-ui, sans-serif' }}>
        <NextIntlClientProvider messages={messages}>
          <div className="flex flex-col min-h-screen">
            {/* Header */}
            <header className="sticky top-0 z-50 bg-gray-950/80 backdrop-blur-md border-b border-gray-800/60">
              <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                      <svg
                        className="w-4 h-4 text-white"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                        />
                      </svg>
                    </div>
                    <span className="text-lg font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                      ContractReview
                    </span>
                  </div>
                  <LanguageSwitcher />
                </div>
              </div>
            </header>

            {/* Main Content */}
            <main className="flex-1">{children}</main>

            {/* Footer */}
            <footer className="border-t border-gray-800/50 bg-gray-950/50 backdrop-blur-sm">
              <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                <p className="text-xs text-gray-500 text-center">
                  © {new Date().getFullYear()} Rental Contract Review Tool
                </p>
              </div>
            </footer>
          </div>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}