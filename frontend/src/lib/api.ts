import type { ContractAnalysisResponse, ErrorResponse } from '@/types/contract';

/**
 * Resolve the backend base URL for API calls.
 *
 * In production the frontend and /contracts/* are served on the same host via
 * nginx. Using a relative base (empty string) keeps requests same-origin and
 * avoids a CORS preflight OPTIONS before the actual POST.
 *
 * In local dev the Next.js app (port 3000) and backend (port 5001) are different
 * origins, so we call the backend URL directly (CORS is enabled there).
 */
function resolveApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL;

  if (typeof window === 'undefined') {
    return configured || 'http://localhost:5001';
  }

  const isLocalDev =
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1';

  if (isLocalDev) {
    return configured || 'http://localhost:5001';
  }

  return '';
}

export class ApiError extends Error {
  statusCode?: number;

  constructor(message: string, statusCode?: number) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
  }
}

/**
 * Call the contract analysis endpoint.
 * Pass a valid access token (Polar license key after payment, or admin key).
 */
export async function analyzeContract(
  file: File,
  lang: string = 'de',
  apiKey?: string
): Promise<ContractAnalysisResponse> {
  console.log('[analyzeContract] Sending request with lang =', lang, 'hasKey=', !!apiKey);

  const formData = new FormData();
  formData.append('file', file);

  const headers: Record<string, string> = {};
  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }

  const response = await fetch(`${resolveApiBaseUrl()}/contracts/analyze?lang=${lang}`, {
    method: 'POST',
    body: formData,
    headers,
  });

  if (!response.ok) {
    let errorMessage = 'An error occurred during analysis.';

    try {
      const errorData: ErrorResponse = await response.json();
      errorMessage = errorData.detail || errorMessage;
    } catch {
      errorMessage = response.statusText || errorMessage;
    }

    const err = new ApiError(errorMessage, response.status);
    // Special case for paywall
    if (response.status === 401 || response.status === 402) {
      err.message = errorMessage || (response.status === 402 ? 'Payment required' : 'Unauthorized');
    }
    throw err;
  }

  const data: ContractAnalysisResponse = await response.json();
  return data;
}

export function getApiBaseUrl(): string {
  return resolveApiBaseUrl();
}

/** Helper to detect paywall errors from the backend */
export function isPaymentError(err: unknown): err is ApiError {
  return err instanceof ApiError && (err.statusCode === 401 || err.statusCode === 402);
}