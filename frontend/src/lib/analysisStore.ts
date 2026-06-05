import type { ContractAnalysisResponse, UploadState } from '@/types/contract';

/**
 * Module-level state store that survives React component remounts.
 * This is critical for preserving in-flight analysis state when the user
 * changes the language (which causes the page component to unmount/remount).
 */
let analysisState: UploadState = 'idle';
let analysisPromise: Promise<ContractAnalysisResponse> | null = null;
let analysisResults: ContractAnalysisResponse | null = null;
let analysisError: string | null = null;
let fileName: string | null = null;

// --- License / Paywall key (persisted to localStorage) ---
const LICENSE_STORAGE_KEY = 'contract_analysis_license_key';

let licenseKey: string | null = null;

function loadLicenseFromStorage(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return localStorage.getItem(LICENSE_STORAGE_KEY);
  } catch {
    return null;
  }
}

function persistLicense(key: string | null) {
  if (typeof window === 'undefined') return;
  try {
    if (key) {
      localStorage.setItem(LICENSE_STORAGE_KEY, key);
    } else {
      localStorage.removeItem(LICENSE_STORAGE_KEY);
    }
  } catch { /* ignore */ }
}

// Hydrate on module load (client only)
if (typeof window !== 'undefined') {
  licenseKey = loadLicenseFromStorage();
}

export function setAnalysisPending(filename: string, promise: Promise<ContractAnalysisResponse>) {
  analysisState = 'analyzing';
  analysisPromise = promise;
  fileName = filename;
  analysisResults = null;
  analysisError = null;

  // When the promise resolves or rejects, update the store
  promise
    .then((data) => {
      analysisState = 'success';
      analysisResults = data;
      analysisPromise = null;
    })
    .catch((err) => {
      analysisState = 'error';
      analysisError = err instanceof Error ? err.message : 'An unexpected error occurred';
      analysisPromise = null;
    });
}

export function setAnalysisSuccess(results: ContractAnalysisResponse) {
  analysisState = 'success';
  analysisResults = results;
  analysisPromise = null;
  analysisError = null;
}

export function setAnalysisError(error: string) {
  analysisState = 'error';
  analysisError = error;
  analysisPromise = null;
  analysisResults = null;
}

export function resetAnalysis() {
  analysisState = 'idle';
  analysisPromise = null;
  analysisResults = null;
  analysisError = null;
  fileName = null;
  postPurchaseLoading = false;
}

/**
 * Clear only analysis results (and error state), but preserve the filename.
 * Useful when switching languages — we want to force re-analysis but keep
 * the "previously selected file" memory so we can guide the user.
 */
export function clearAnalysisResultsOnly() {
  analysisState = 'idle';
  analysisPromise = null;
  analysisResults = null;
  analysisError = null;
  // deliberately do NOT clear fileName
}

export function setFileName(name: string) {
  fileName = name;
}

export function getAnalysisState() {
  return {
    state: analysisState,
    promise: analysisPromise,
    results: analysisResults,
    error: analysisError,
    fileName: fileName,
  };
}

// ============================================================
// License key (access token) management for paywall
// ============================================================

export function getLicenseKey(): string | null {
  if (!licenseKey && typeof window !== 'undefined') {
    licenseKey = loadLicenseFromStorage();
  }
  return licenseKey;
}

export function setLicenseKey(key: string) {
  licenseKey = key.trim();
  persistLicense(licenseKey);
}

export function clearLicenseKey() {
  licenseKey = null;
  persistLicense(null);
}

export function hasLicenseKey(): boolean {
  return !!getLicenseKey();
}

// ============================================================
// Post-purchase loading lock (to disable language switch etc. during analysis after checkout)
// ============================================================

let postPurchaseLoading = false;

const listeners = new Set<() => void>();

export function setPostPurchaseLoading(loading: boolean) {
  postPurchaseLoading = loading;
  listeners.forEach((l) => l());
}

export function isPostPurchaseLoading(): boolean {
  return postPurchaseLoading;
}

export function subscribePostPurchaseLoading(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}