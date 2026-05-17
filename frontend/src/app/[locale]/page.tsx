'use client';

import { useState, useCallback, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { Scale, Shield, Sparkles, ArrowRight, Loader2 } from 'lucide-react';
import FileUpload from '@/components/FileUpload';
import ResultsDisplay from '@/components/ResultsDisplay';
import { analyzeContract, ApiError } from '@/lib/api';
import type { ContractAnalysisResponse, UploadState } from '@/types/contract';
import {
  getAnalysisState,
  setAnalysisPending,
  setAnalysisSuccess,
  setAnalysisError,
  resetAnalysis,
  setFileName,
} from '@/lib/analysisStore';

const RESULTS_KEY = 'contract_analysis_results';

function loadSavedResults(): ContractAnalysisResponse | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(RESULTS_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function saveResults(results: ContractAnalysisResponse) {
  try {
    localStorage.setItem(RESULTS_KEY, JSON.stringify(results));
  } catch { /* ignore */ }
}

function clearResults() {
  try {
    localStorage.removeItem(RESULTS_KEY);
  } catch { /* ignore */ }
}

export default function HomePage() {
  const t = useTranslations();
  const tFeatures = useTranslations('app.features');

  // Initialize from module-level store first, then fall back to localStorage
  const store = getAnalysisState();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedFileName, setSelectedFileName] = useState<string | null>(store.fileName || null);
  const [results, setResults] = useState<ContractAnalysisResponse | null>(store.results || loadSavedResults);
  const [error, setError] = useState<string | null>(store.error || null);
  const [uploadState, setUploadState] = useState<UploadState>(store.state);

  // On mount: if store says analyzing, wait for the promise to complete
  useEffect(() => {
    const currentState = getAnalysisState();
    if (currentState.state === 'analyzing' && currentState.promise) {
      // Already analyzing — promise will update store when done
      // We need to poll or listen for the store to change
      const interval = setInterval(() => {
        const s = getAnalysisState();
        if (s.state !== 'analyzing') {
          clearInterval(interval);
          setUploadState(s.state);
          if (s.results) {
            setResults(s.results);
            saveResults(s.results);
          }
          if (s.error) {
            setError(s.error);
          }
        }
      }, 200);
      return () => clearInterval(interval);
    }
  }, []);

  const handleFileSelect = useCallback((file: File) => {
    setSelectedFile(file);
    setSelectedFileName(file.name);
    setFileName(file.name);
    setError(null);
    setResults(null);
    clearResults();
    resetAnalysis();
    setUploadState('idle');
  }, []);

  const handleAnalyze = useCallback(async () => {
    if (!selectedFile) return;

    setUploadState('analyzing');
    setError(null);

    const promise = analyzeContract(selectedFile);

    // Store the pending analysis in module-level store
    setAnalysisPending(selectedFile.name, promise);

    try {
      const data = await promise;
      setResults(data);
      saveResults(data);
      setAnalysisSuccess(data);
      setUploadState('success');
    } catch (err) {
      let message: string;
      if (err instanceof ApiError) {
        message = err.message;
      } else {
        message = err instanceof Error ? err.message : t('errors.general');
      }
      setError(message);
      setAnalysisError(message);
      setUploadState('error');
    }
  }, [selectedFile, t]);

  const handleReset = useCallback(() => {
    setSelectedFile(null);
    setSelectedFileName(null);
    setResults(null);
    setError(null);
    clearResults();
    resetAnalysis();
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

  const showAnalyzing = uploadState === 'analyzing';

  return (
    <div className="flex flex-col items-center">
      {/* Hero Section */}
      <section className="w-full max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 pb-12 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-blue-900/30 rounded-full text-sm font-medium text-blue-300 mb-6 animate-fade-in border border-blue-800/40">
          <Sparkles className="w-4 h-4" />
          {t('app.subtitle')}
        </div>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white tracking-tight text-balance">
          {t('app.title')}
        </h1>
        <p className="mt-6 text-lg text-gray-400 max-w-2xl mx-auto text-balance">
          {t('app.description')}
        </p>
      </section>

      {/* Features */}
      <section className="w-full max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
        <div className="grid md:grid-cols-3 gap-6">
          {[
            {
              icon: Scale,
              key: 'legal',
            },
            {
              icon: Shield,
              key: 'risk',
            },
            {
              icon: Sparkles,
              key: 'ai',
            },
          ].map((feature, index) => (
            <div
              key={index}
              className="glass-card rounded-xl p-6 hover:shadow-xl hover:shadow-blue-900/10 transition-all duration-300 animate-slide-up border-gray-800/50"
              style={{ animationDelay: `${index * 150}ms` }}
            >
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-900/40 to-purple-900/40 flex items-center justify-center mb-4">
                <feature.icon className="w-5 h-5 text-blue-400" />
              </div>
              <h3 className="font-semibold text-gray-200 mb-1">{tFeatures(`${feature.key}.title`)}</h3>
              <p className="text-sm text-gray-400 leading-relaxed">{tFeatures(`${feature.key}.desc`)}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Upload Section */}
      <section className="w-full max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
        <div className="glass-card rounded-2xl p-8 md:p-12 border-gray-800/50">
          <h2 className="text-2xl font-bold text-white text-center mb-8">
            {t('upload.title')}
          </h2>
          <FileUpload
            onFileSelect={handleFileSelect}
            disabled={uploadState === 'analyzing'}
            selectedFile={selectedFile}
            selectedFileName={selectedFileName}
          />

          {/* Show "Analyze" button only when a real File object exists and not analyzing */}
          {selectedFile && !showAnalyzing && (
            <div className="flex justify-center mt-8 animate-fade-in">
              <button
                onClick={handleAnalyze}
                className="inline-flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-blue-600 to-blue-700 text-white font-medium rounded-xl shadow-lg shadow-blue-900/30 hover:shadow-xl hover:shadow-blue-900/40 hover:from-blue-500 hover:to-blue-600 transition-all duration-200 text-base"
              >
                <ArrowRight className="w-5 h-5" />
                {t('upload.analyze')}
              </button>
            </div>
          )}

          {/* Show re-select message when filename exists but File is missing (after language change) and not analyzing */}
          {!selectedFile && selectedFileName && !showAnalyzing && (
            <div className="flex justify-center mt-8 animate-fade-in">
              <p className="text-sm text-yellow-400 bg-yellow-900/20 rounded-xl px-4 py-3 border border-yellow-800/30 text-center max-w-md">
                Previously selected: {selectedFileName}. Please re-select the file to analyze.
              </p>
            </div>
          )}

          {/* Show analyzing state */}
          {showAnalyzing && (
            <div className="flex flex-col items-center mt-8 animate-fade-in">
              <div className="w-16 h-16 rounded-2xl bg-blue-900/30 flex items-center justify-center mb-4">
                <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
              </div>
              <p className="text-gray-300 font-medium">{t('upload.analyzing')}</p>
              <p className="text-sm text-gray-500 mt-1">
                {t('upload.analyzingDescription')}
              </p>
              <p className="text-xs text-gray-400 mt-2">{t('upload.analyzingNote')}</p>
            </div>
          )}

          {/* Show error state */}
          {uploadState === 'error' && error && (
            <div className="mt-6 p-4 bg-red-900/30 rounded-xl border border-red-800/40 animate-fade-in">
              <p className="text-sm text-red-300">{error}</p>
            </div>
          )}
        </div>
      </section>

      {/* Legal notice */}
      <section className="w-full max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
        <p className="text-xs text-gray-500 text-center max-w-2xl mx-auto">
          {t('app.legalNotice')}
        </p>
      </section>
    </div>
  );
}