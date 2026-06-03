'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { Scale, Shield, Sparkles, ArrowRight, Loader2, CreditCard } from 'lucide-react';
import FileUpload from '@/components/FileUpload';
import ResultsDisplay from '@/components/ResultsDisplay';

import { analyzeContract, ApiError, isPaymentError } from '@/lib/api';
import type { ContractAnalysisResponse, UploadState } from '@/types/contract';
import {
  getAnalysisState,
  setAnalysisPending,
  setAnalysisSuccess,
  setAnalysisError,
  resetAnalysis,
  setFileName,
  clearAnalysisResultsOnly,
  getLicenseKey,
  clearLicenseKey,
  hasLicenseKey,
  setPostPurchaseLoading,
  isPostPurchaseLoading,
} from '@/lib/analysisStore';
import {
  storePendingFile,
  loadAndReconstructFile,
  deletePendingFile,
  pruneOldPendingFiles,
  clearAllPendingFiles,
  ensureCleaned,
} from '@/lib/tempPurchaseFile';

// Polar embed (client-side only)
let PolarEmbedCheckout: any = null;
if (typeof window !== 'undefined') {
  // Dynamic import to avoid SSR issues
  import('@polar-sh/checkout/embed').then((mod) => {
    PolarEmbedCheckout = mod.PolarEmbedCheckout;
  }).catch(() => {});
}

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
  const currentLocale = useLocale();
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  // Always use the latest locale value at call time (avoids stale closures in event handlers and setTimeout)
  const localeRef = useRef(currentLocale);
  useEffect(() => {
    localeRef.current = currentLocale;
  }, [currentLocale]);

  // Initialize from module-level store first, then fall back to localStorage
  const store = getAnalysisState();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedFileName, setSelectedFileName] = useState<string | null>(store.fileName || null);
  const [results, setResults] = useState<ContractAnalysisResponse | null>(store.results || loadSavedResults);
  const [error, setError] = useState<string | null>(store.error || null);
  const [uploadState, setUploadState] = useState<UploadState>(store.state);

  // Ref for the selected File object. This survives the long async gap between
  // clicking "Analyze for €2" and the Polar 'success' event (plus key polling).
  // We must declare + sync this *after* the useState for selectedFile to avoid
  // "Cannot access 'selectedFile' before initialization".
  const selectedFileRef = useRef<File | null>(null);
  useEffect(() => {
    selectedFileRef.current = selectedFile;
  }, [selectedFile]);

  // Paywall / license state
  const [licenseKey, setLicenseKeyState] = useState<string | null>(getLicenseKey());
  const [showPaywall, setShowPaywall] = useState(false);
  const [isBuying, setIsBuying] = useState(false);

  // When we return from Polar after a successful payment (via successUrl), we may have resolved
  // a key before the user has re-selected their file (because navigation clears the File object).
  // This holds that key so we can auto-analyze as soon as they pick the file again.
  const [pendingKeyFromRecentPurchase, setPendingKeyFromRecentPurchase] = useState<string | null>(null);

  // Flag to indicate we are in a post-purchase analysis flow (after checkout redirect or success).
  // Used to render the analyzing/loading state in the clean "results page" layout instead of inside the upload card.
  const [postPurchaseAnalyzing, setPostPurchaseAnalyzing] = useState(false);

  // Track which checkout_ids we have already started processing.
  // This prevents the useEffect below from kicking off duplicate resolve + polling
  // sequences for the same purchase (caused by unstable searchParams object, StrictMode, etc.).
  const processedCheckoutIdsRef = useRef<Set<string>>(new Set());

  // On mount: if store says analyzing, wait for the promise to complete.
  // Also prune any stale temp file snapshots from previous (crashed/abandoned) purchases.
  useEffect(() => {
    ensureCleaned();

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



  // When language changes, clear old results (they have descriptions in the wrong language)
  // but keep the filename so we can show a helpful "re-select this file" message.
  const prevLocaleRef = useRef(currentLocale);
  useEffect(() => {
    if (prevLocaleRef.current !== currentLocale) {
      setResults(null);
      clearResults();                 // clear localStorage
      clearAnalysisResultsOnly();     // clear module store results but preserve fileName
      setError(null);
      setUploadState('idle');
      setPostPurchaseAnalyzing(false);
      setPostPurchaseLoading(false);

      prevLocaleRef.current = currentLocale;
    }
  }, [currentLocale]);

  // Handle return from Polar after successful embedded checkout (via successUrl with checkout_id).
  // This makes the flow survive the redirect that Polar performs after payment for license key purchases.
  // We resolve the key and either auto-start analysis (if file still in memory) or prepare for seamless continuation.
  useEffect(() => {
    const checkoutId = searchParams.get('checkout_id');
    if (!checkoutId) return;

    // Guard: only process each checkout_id once, even if the effect re-runs
    // (unstable searchParams object, React StrictMode double-invoke, re-renders, etc.)
    if (processedCheckoutIdsRef.current.has(checkoutId)) {
      return;
    }
    processedCheckoutIdsRef.current.add(checkoutId);

    // Clean the URL so it doesn't stay in history
    const url = new URL(window.location.href);
    url.searchParams.delete('checkout_id');
    window.history.replaceState({}, '', url.toString());

    console.log('[Polar] Returned from Polar with checkout_id, resuming analysis flow:', checkoutId);

    // Immediately mark as post-purchase analyzing so the first render after redirect
    // shows the clean loading layout (instead of the first/upload page).
    setPostPurchaseAnalyzing(true);
    setPostPurchaseLoading(true);

    (async () => {
      setError(null);

      // Poll for the key (same logic as the embedded success handler)
      let keyData = null;
      for (let i = 0; i < 8; i++) {  // slightly more attempts for redirect case
        await new Promise((res) => setTimeout(res, 1200));
        try {
          const keyRes = await fetch(`/api/polar/resolve-key?checkout_id=${encodeURIComponent(checkoutId)}`);
          if (keyRes.ok) {
            const data = await keyRes.json();
            if (data?.licenseKey) {
              keyData = data;
              break;
            }
          }
        } catch {}
      }

      if (keyData?.licenseKey) {
        // IMPORTANT: Do NOT call setLicenseKey() (the persisting version) for one-time Polar keys.
        // Persisting them to localStorage causes reuse of already-consumed keys on re-select after redirect.
        setLicenseKeyState(keyData.licenseKey);

        // Try to restore the exact file the user selected before the purchase (from our
        // temp IndexedDB snapshot). If we succeed, the user does **not** have to re-pick
        // the file from disk.
        let fileToUse = selectedFileRef.current || selectedFile;

        if (!fileToUse && checkoutId) {
          try {
            const restored = await loadAndReconstructFile(`pending-file-${checkoutId}`);
            if (restored) {
              console.log('[Polar] Restored file snapshot from IndexedDB for checkout', checkoutId);
              fileToUse = restored;
              // Make the UI reflect the restored file immediately (same as a normal selection)
              setSelectedFile(restored);
              setSelectedFileName(restored.name);
              setFileName(restored.name);
              // Also delete the snapshot now that we've consumed it
              deletePendingFile(`pending-file-${checkoutId}`).catch(() => {});
            }
          } catch {
            // fall through to the pending-key banner
          }
        }

        if (fileToUse) {
          // Either the in-memory ref survived or we restored from snapshot → start analysis
          console.log('[Polar] Resuming with file (in-memory or restored):', fileToUse.name);
          await startAnalysisWithKey(fileToUse, keyData.licenseKey);
        } else {
          // Most common case after redirect: file object lost, but we have the key now.
          // The existing "re-select this file" UI will show. We set pendingKeyFromRecentPurchase
          // so that as soon as the user picks the file again, we auto-start analysis (no second purchase).
          console.log('[Polar] Key resolved after redirect, waiting for file re-selection');
          setError(null);
          setPendingKeyFromRecentPurchase(keyData.licenseKey);
          // Keep the post-purchase flag so that when the user re-selects, the analyzing state
          // will use the clean results-style loading layout.
          setPostPurchaseAnalyzing(true);
          setPostPurchaseLoading(true);
        }
      } else {
        setError('Payment completed, but we could not retrieve your access key automatically. Please try the purchase again or check your email.');
        setPostPurchaseLoading(false);
      }
    })();
  }, [searchParams]); // run when params (including after redirect) change

  // Defined early so it can be used by handleFileSelect (for auto-resume after Polar redirect)
  // and by the return-from-Polar effect.
  const startAnalysisWithKey = useCallback(async (file: File, key: string) => {
    setUploadState('analyzing');
    setError(null);

    const promise = analyzeContract(file, localeRef.current, key);
    setAnalysisPending(file.name, promise);

    try {
      const data = await promise;
      setResults(data);
      saveResults(data);
      setAnalysisSuccess(data);
      setUploadState('success');

      // One-time use: clear the license key after a successful analysis
      clearLicenseKey();
      setLicenseKeyState(null);
      setPostPurchaseLoading(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Analysis failed after purchase.';
      setError(message);
      setAnalysisError(message);
      setUploadState('error');
      setPostPurchaseLoading(false);
    }
  }, []);



  const handleAnalyze = useCallback(async () => {
    if (!selectedFile) return;

    const currentKey = licenseKey || getLicenseKey();

    if (!currentKey) {
      // Gate behind paywall
      setShowPaywall(true);
      setError(null);
      return;
    }

    setUploadState('analyzing');
    setError(null);

    const promise = analyzeContract(selectedFile, localeRef.current, currentKey);

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

      // If backend rejected the key (expired / invalid / quota), force paywall on next attempt
      if (isPaymentError(err)) {
        setLicenseKeyState(null);
        setShowPaywall(true);
      }
    }
  }, [selectedFile, licenseKey, t]);

  const handleFileSelect = useCallback((file: File) => {
    setSelectedFile(file);
    setSelectedFileName(file.name);
    setFileName(file.name);
    setError(null);
    setResults(null);
    clearResults();
    resetAnalysis();
    setUploadState('idle');
    setShowPaywall(false);

    // If we just returned from a successful Polar payment and resolved a key
    // before the user re-selected the file (common after the redirect), auto-start
    // the analysis now that we have the bytes again.
    if (pendingKeyFromRecentPurchase) {
      const keyToUse = pendingKeyFromRecentPurchase;
      setPendingKeyFromRecentPurchase(null);
      setPostPurchaseAnalyzing(true);
      setPostPurchaseLoading(true);
      setTimeout(() => {
        startAnalysisWithKey(file, keyToUse);
      }, 50);
    }
  }, [pendingKeyFromRecentPurchase, startAnalysisWithKey]);

  const handleReset = useCallback(() => {
    setSelectedFile(null);
    setSelectedFileName(null);
    setResults(null);
    setError(null);
    clearResults();
    resetAnalysis();
    setUploadState('idle');
    setShowPaywall(false);
    setPendingKeyFromRecentPurchase(null);
    setPostPurchaseAnalyzing(false);
    setPostPurchaseLoading(false);
    processedCheckoutIdsRef.current.clear(); // allow processing new checkouts after "New Analysis"
    // Clear any temp file snapshots for this purchase flow
    clearAllPendingFiles().catch(() => {});
    // Clear license key completely so the full purchase flow starts again
    clearLicenseKey();
    setLicenseKeyState(null);

    // Force clean URL on New Analysis using router.replace (proper Next router update).
    // This guarantees we don't hit the "finalizing purchase" / hasCheckoutParam loader
    // and go straight to the first (upload) page, even if manual history or stale searchParams.
    router.replace(pathname, { scroll: false });
  }, [router, pathname]);

  /**
   * Trigger embedded Polar checkout (smoother UX, no full redirect).
   * On success event we resolve the license key via our BFF and enable analysis.
   */
  const handleBuyAccess = useCallback(async () => {
    setIsBuying(true);
    setError(null);
    setPendingKeyFromRecentPurchase(null); // starting a new purchase, discard any previous pending key
    setPostPurchaseAnalyzing(false);
    setPostPurchaseLoading(false);
    // Note: we do NOT clear processedCheckoutIdsRef here on purpose —
    // each checkout_id should only be processed once even across multiple buy attempts in the same session.
    // handleReset is the place that fully resets the "I can process checkouts again" state.

    // Capture the file at the exact moment the user clicks "Analyze for €2".
    // This + the selectedFileRef below guarantees we still have it when the
    // Polar 'success' event fires many seconds later.
    const fileForPurchase = selectedFileRef.current || selectedFile;
    console.log('[Polar] Buy button clicked, captured fileForPurchase:', fileForPurchase?.name);

    // Snapshot the file bytes to IndexedDB *before* we start the checkout.
    // This lets us reconstruct the File after a Polar-forced redirect (which
    // does a full page load and destroys in-memory state).
    // We use a temp key first; after we receive the real checkoutId we will
    // re-key it.
    let pendingFileTempKey: string | null = null;
    if (fileForPurchase) {
      pendingFileTempKey = `temp-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      // Fire-and-forget the snapshot (non-fatal if it fails)
      storePendingFile(pendingFileTempKey, fileForPurchase).catch(() => {});
    }

    // Build a successUrl that brings the user back to *this exact page* with the checkout_id.
    // This prevents Polar from redirecting to their own portal/access page after payment.
    // We use the {CHECKOUT_ID} placeholder that Polar supports.
    const successUrl = `${window.location.origin}/${currentLocale}?checkout_id={CHECKOUT_ID}`;

    try {
      const res = await fetch('/api/polar/create-checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ successUrl }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || 'Could not start checkout');
      }

      const { checkoutUrl, checkoutId: returnedCheckoutId } = await res.json();

      if (!checkoutUrl) throw new Error('No checkout URL returned');

      // If we snapshotted the file under a temp key, now associate it with the
      // real checkoutId that will be in the successUrl / redirect. This lets the
      // resume logic on the other side of the navigation find and restore the File.
      if (pendingFileTempKey && returnedCheckoutId) {
        // Best-effort move: load the bytes under temp, store under real id, delete temp.
        // We do this synchronously in the flow before opening the embed.
        try {
          const restored = await loadAndReconstructFile(pendingFileTempKey);
          if (restored) {
            await storePendingFile(`pending-file-${returnedCheckoutId}`, restored);
            await deletePendingFile(pendingFileTempKey);
          }
        } catch {
          // Non-fatal; the in-memory ref may still work, or user will re-select.
        }
      }

      // Fallback if embed library failed to load
      if (!PolarEmbedCheckout) {
        window.open(checkoutUrl, '_blank');
        setIsBuying(false);
        return;
      }

      const checkoutInstance = await PolarEmbedCheckout.create(checkoutUrl, {
        theme: 'dark',
        onLoaded: () => console.log('[Polar] Embedded checkout loaded'),
      });

      // Handle successful purchase
      checkoutInstance.addEventListener('success', async (event: any) => {
        console.log('[Polar] Purchase successful via embedded checkout', event.detail);

        const checkoutId = event.detail?.checkoutId;

        setShowPaywall(false);
        setIsBuying(false);
        // For the direct (no-redirect) success path, also mark post-purchase so the loading
        // uses the clean results-style container (consistent with the redirect case).
        setPostPurchaseAnalyzing(true);
        setPostPurchaseLoading(true);

        if (!checkoutId) {
          setError('Purchase successful! Analysis will start automatically. If it does not, please refresh the page.');
          return;
        }

        // Poll the resolve endpoint a few times.
        // This gives the webhook (benefit_grant.created) time to deliver the license key.
        let keyData = null;

        for (let i = 0; i < 6; i++) {
          await new Promise((res) => setTimeout(res, 1500));

          try {
            const keyRes = await fetch(`/api/polar/resolve-key?checkout_id=${encodeURIComponent(checkoutId)}`);
            if (keyRes.ok) {
              const data = await keyRes.json();
              if (data?.licenseKey) {
                keyData = data;
                break;
              }
            }
          } catch (e) {
            // ignore and keep retrying
          }
        }

        console.log('[Polar] Key resolution result after polling:', !!keyData?.licenseKey);

        if (keyData?.licenseKey) {
          // IMPORTANT: Never persist one-time Polar analysis keys to localStorage via setLicenseKey().
          // They are strictly single-use and must be used immediately via startAnalysisWithKey.
          setLicenseKeyState(keyData.licenseKey);

          // Use the file captured at click time + the live ref as fallback.
          const fileToAnalyze = fileForPurchase || selectedFileRef.current;

          if (fileToAnalyze) {
            console.log('[Polar] Starting analysis with file:', fileToAnalyze.name);
            // Use the shared helper — this is what makes the "immediately show analyzing loader + run analysis" path reliable
            await startAnalysisWithKey(fileToAnalyze, keyData.licenseKey);

            // Cleanup any temp snapshot we may have created for this checkout (non-redirect path).
            if (checkoutId) {
              deletePendingFile(`pending-file-${checkoutId}`).catch(() => {});
            }
          } else {
            console.warn('[Polar] SUCCESS but no file available (closure/ref lost)');
            setError('Purchase successful, but the selected file was lost. Please re-upload the contract and click "Analyze for €2" again.');
            setUploadState('idle');
          }
        } else {
          setError('Purchase successful! We could not retrieve your license key yet. Please check your email or refresh to retry analysis.');
        }
      });

      checkoutInstance.addEventListener('close', () => {
        setIsBuying(false);
      });
    } catch (e: any) {
      console.error('[Polar] Buy flow error', e);
      setError(e.message || 'Could not open checkout. Please try again or contact support.');
      setIsBuying(false);
    }
  }, [selectedFile]);

  // If we have results, show them
  if (results) {
    return (
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ResultsDisplay data={results} onReset={handleReset} />
      </div>
    );
  }

  const showAnalyzing = uploadState === 'analyzing';
  const hasCheckoutParam = !!searchParams.get('checkout_id');

  // Post-purchase loading state (after checkout, during key resolution or actual analysis).
  // Blurred mock results page in the background.
  // Foreground: bigger loading circle (no card) centered on the page, with text BENEATH the loader (no text inside circle).
  const isPostPurchaseLoading = hasCheckoutParam || (showAnalyzing && (postPurchaseAnalyzing || hasCheckoutParam));
  if (isPostPurchaseLoading) {
    const isFinalizing = hasCheckoutParam && !showAnalyzing;
    const loaderTitle = isFinalizing ? 'Finalizing your purchase...' : t('upload.analyzing');
    const loaderDesc = isFinalizing
      ? 'Retrieving your access and preparing the analysis.'
      : t('upload.analyzingDescription');
    const loaderNote = isFinalizing ? 'Retrieving access...' : t('upload.analyzingNote');

    const fileLabel = selectedFileName || 'Contract document';

    return (
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 relative min-h-[480px]">
        {/* Blurred results-page background (mock header + content using known filename) */}
        <div className="blur-[5px] opacity-30 pointer-events-none select-none">
          <div className="w-full max-w-4xl mx-auto space-y-6">
            {/* Results-like header */}
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-white">Contract Analysis</h2>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-sm text-gray-400">
                  <span className="flex items-center gap-1.5">
                    {fileLabel}
                  </span>
                  <span>Processing...</span>
                </div>
              </div>
            </div>

            {/* Blurred placeholder stats card */}
            <div className="glass-card rounded-2xl p-6">
              <div className="h-5 w-28 bg-white/10 rounded mb-4" />
              <div className="grid grid-cols-3 gap-3">
                <div className="h-12 bg-white/5 rounded" />
                <div className="h-12 bg-white/5 rounded" />
                <div className="h-12 bg-white/5 rounded" />
              </div>
            </div>

            {/* Blurred placeholder issues */}
            <div>
              <h3 className="text-lg font-semibold text-white mb-3">Issues Found</h3>
              <div className="glass-card rounded-2xl p-5">
                <div className="h-4 bg-white/10 rounded w-3/4 mb-2" />
                <div className="h-4 bg-white/10 rounded w-2/3" />
              </div>
            </div>
          </div>
        </div>

        {/* Foreground centered loading animation - no card, pure bigger circle + text BENEATH it */}
        <div className="absolute inset-0 flex items-center justify-center z-10">
          <div className="flex flex-col items-center">
            {/* Pure spinning circle (bigger, no text inside) */}
            <div className="relative w-32 h-32 flex items-center justify-center mb-4">
              {/* Static ring */}
              <div className="absolute inset-0 rounded-full border-[12px] border-blue-900/20"></div>
              {/* Spinning arc */}
              <div className="absolute inset-0 rounded-full border-[12px] border-blue-400 border-t-transparent animate-spin"></div>
            </div>

            {/* Text beneath the loader, no card */}
            <div className="text-center max-w-xs">
              <p className="text-white font-semibold text-lg">{loaderTitle}</p>
              <p className="text-sm text-gray-400 mt-1 leading-relaxed">{loaderDesc}</p>
              {loaderNote && (
                <p className="text-xs text-gray-500 mt-2">{loaderNote}</p>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

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

          {/* Show button after file upload.
              - Normal case: "Analyze for €2" (starts embedded checkout)
              - After returning from successful Polar payment (key already resolved): show "Start Analysis" instead,
                using the key we already have. This gives the seamless "loading results" experience. */}
          {selectedFile && !showAnalyzing && (
            <div className="flex flex-col items-center gap-4 mt-8 animate-fade-in">
              {pendingKeyFromRecentPurchase ? (
                <button
                  onClick={() => {
                    const key = pendingKeyFromRecentPurchase;
                    setPendingKeyFromRecentPurchase(null);
                    startAnalysisWithKey(selectedFile, key);
                  }}
                  className="inline-flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-blue-600 to-blue-700 text-white font-medium rounded-xl shadow-lg shadow-blue-900/30 hover:shadow-xl hover:shadow-blue-900/40 hover:from-blue-500 hover:to-blue-600 transition-all duration-200 text-base"
                >
                  <ArrowRight className="w-5 h-5" />
                  Start Analysis
                </button>
              ) : (
                <button
                  onClick={handleBuyAccess}
                  disabled={isBuying}
                  className="inline-flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-emerald-600 to-emerald-700 text-white font-medium rounded-xl shadow-lg shadow-emerald-900/30 hover:shadow-xl hover:shadow-emerald-900/40 hover:from-emerald-500 hover:to-emerald-600 transition-all duration-200 text-base disabled:opacity-70"
                >
                  {isBuying ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <CreditCard className="w-5 h-5" />
                  )}
                  {t('paywall.buyCta') || 'Analyze for €2'}
                </button>
              )}
            </div>
          )}

          {/* Show re-select message when filename exists but File is missing.
              Enhanced for the post-Polar-payment case: if we have a pending key, guide the user to continue the analysis. */}
          {!selectedFile && selectedFileName && !showAnalyzing && (
            <div className="flex justify-center mt-8 animate-fade-in">
              <p className="text-sm text-yellow-400 bg-yellow-900/20 rounded-xl px-4 py-3 border border-yellow-800/30 text-center max-w-md">
                {pendingKeyFromRecentPurchase ? (
                  <>Payment successful. Please re-select <strong>{selectedFileName}</strong> to start the analysis with your purchased access.</>
                ) : (
                  <>Language changed. Please re-select <strong>{selectedFileName}</strong> to get the analysis with {currentLocale === 'de' ? 'German' : 'English'} descriptions.</>
                )}
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

          {/* Paywall / License UI (shown when user needs access or explicitly requests) */}
          {showPaywall && !results && (
            <div className="mt-8 animate-fade-in">
              <div className="glass-card rounded-2xl p-6 border-emerald-900/40 bg-emerald-950/10">
                <div className="flex items-start gap-3 mb-4">
                  <div className="w-10 h-10 rounded-xl bg-emerald-900/30 flex items-center justify-center flex-shrink-0">
                    <CreditCard className="w-5 h-5 text-emerald-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white text-lg">{t('paywall.title') || 'Unlock Contract Analysis'}</h3>
                    <p className="text-sm text-gray-400 mt-1">
                      {t('paywall.description') || 'Purchase a one-time access pass to analyze German rental contracts. Your license key works immediately after payment.'}
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap gap-3">
                  <button
                    onClick={handleBuyAccess}
                    disabled={isBuying}
                    className="inline-flex items-center gap-2 px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-700 text-white font-medium rounded-xl text-sm transition"
                  >
                    {isBuying ? <Loader2 className="w-4 h-4 animate-spin" /> : <CreditCard className="w-4 h-4" />}
                    {t('paywall.buyCta') || 'Analyze for €2'}
                  </button>
                  <button
                    onClick={() => setShowPaywall(false)}
                    className="px-6 py-2.5 text-sm text-gray-300 hover:text-white border border-gray-700 rounded-xl"
                  >
                    Cancel
                  </button>
                </div>

                <p className="mt-4 text-xs text-gray-500">
                  Your license key will be delivered automatically after payment.
                </p>
              </div>
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