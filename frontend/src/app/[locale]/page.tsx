'use client';

import { useState, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { Scale, Shield, Sparkles, ArrowRight, Loader2 } from 'lucide-react';
import FileUpload from '@/components/FileUpload';
import ResultsDisplay from '@/components/ResultsDisplay';
import { analyzeContract, ApiError } from '@/lib/api';
import type { ContractAnalysisResponse, UploadState } from '@/types/contract';

export default function HomePage() {
  const t = useTranslations();
  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [results, setResults] = useState<ContractAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = useCallback((file: File) => {
    setSelectedFile(file);
    setError(null);
    setResults(null);
    setUploadState('idle');
  }, []);

  const handleAnalyze = useCallback(async () => {
    if (!selectedFile) return;

    setUploadState('analyzing');
    setError(null);

    try {
      const data = await analyzeContract(selectedFile);
      setResults(data);
      setUploadState('success');
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        const message = err instanceof Error ? err.message : t('errors.general');
        setError(message);
      }
      setUploadState('error');
    }
  }, [selectedFile, t]);

  const handleReset = useCallback(() => {
    setSelectedFile(null);
    setResults(null);
    setError(null);
    setUploadState('idle');
  }, []);

  // If we have results, show them
  if (results) {
    return (
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ResultsDisplay data={results} onReset={handleReset} />
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center">
      {/* Hero Section */}
      <section className="w-full max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 pb-12 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-blue-50 rounded-full text-sm font-medium text-blue-700 mb-6 animate-fade-in">
          <Sparkles className="w-4 h-4" />
          {t('app.subtitle')}
        </div>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-gray-900 tracking-tight text-balance">
          {t('app.title')}
        </h1>
        <p className="mt-6 text-lg text-gray-600 max-w-2xl mx-auto text-balance">
          {t('app.description')}
        </p>
      </section>

      {/* Features */}
      <section className="w-full max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
        <div className="grid md:grid-cols-3 gap-6">
          {[
            {
              icon: Scale,
              title: 'Legal Analysis',
              desc: 'Automatic detection of potentially invalid clauses based on German rental law (BGB)',
            },
            {
              icon: Shield,
              title: 'Risk Assessment',
              desc: 'Each issue is categorized by risk level with legal basis and similarity scoring',
            },
            {
              icon: Sparkles,
              title: 'AI-Powered',
              desc: 'Advanced NLP and vector search for comprehensive contract analysis',
            },
          ].map((feature, index) => (
            <div
              key={index}
              className="glass-card rounded-xl p-6 hover:shadow-xl hover:shadow-blue-900/5 transition-all duration-300 animate-slide-up border border-gray-100"
              style={{ animationDelay: `${index * 150}ms` }}
            >
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center mb-4">
                <feature.icon className="w-5 h-5 text-blue-600" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-1">{feature.title}</h3>
              <p className="text-sm text-gray-500 leading-relaxed">{feature.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Upload Section */}
      <section className="w-full max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
        <div className="glass-card rounded-2xl p-8 md:p-12 border border-gray-100">
          <h2 className="text-2xl font-bold text-gray-900 text-center mb-8">
            {t('upload.title')}
          </h2>
          <FileUpload
            onFileSelect={handleFileSelect}
            disabled={uploadState === 'analyzing'}
            selectedFile={selectedFile}
          />

          {selectedFile && uploadState !== 'analyzing' && (
            <div className="flex justify-center mt-8 animate-fade-in">
              <button
                onClick={handleAnalyze}
                className="inline-flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white font-medium rounded-xl shadow-lg shadow-blue-200 hover:shadow-xl hover:shadow-blue-200 hover:from-blue-600 hover:to-blue-700 transition-all duration-200 text-base"
              >
                <ArrowRight className="w-5 h-5" />
                {t('upload.analyze')}
              </button>
            </div>
          )}

          {uploadState === 'analyzing' && (
            <div className="flex flex-col items-center mt-8 animate-fade-in">
              <div className="w-16 h-16 rounded-2xl bg-blue-50 flex items-center justify-center mb-4">
                <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
              </div>
              <p className="text-gray-700 font-medium">{t('upload.analyzing')}</p>
              <p className="text-sm text-gray-400 mt-1">
                Extracting text, analyzing clauses, and checking legal patterns...
              </p>
            </div>
          )}

          {/* Error display */}
          {error && (
            <div className="mt-6 p-4 bg-red-50 rounded-xl border border-red-200 animate-fade-in">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}
        </div>
      </section>

      {/* Legal notice */}
      <section className="w-full max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
        <p className="text-xs text-gray-400 text-center max-w-2xl mx-auto">
          {t('app.legalNotice')}
        </p>
      </section>
    </div>
  );
}