'use client';

import { useState } from 'react';

interface RawFetchResult {
  success?: boolean;
  status?: number;
  statusText?: string;
  url?: string;
  body?: any;
  error?: string;
  details?: string;
}

interface SdkCallResult {
  success?: boolean;
  actualSdkBaseUrl?: string | null;
  organizations?: Array<{ id: string; name: string; slug?: string }>;
  product?: any;
  error?: string;
  details?: string;
  statusCode?: number;
  rawError?: any;
}

interface TestResult {
  serverUsed?: string;
  baseUrlUsed?: string;
  token?: { present: boolean; length: number; prefix: string | null };
  rawFetch?: RawFetchResult | null;
  sdkCall?: SdkCallResult | null;
  conclusion?: string;
  // legacy fields for backward compat
  success?: boolean;
  message?: string;
  error?: string;
  details?: string;
  organizations?: any;
  product?: any;
  statusCode?: number;
}

export default function PolarTokenTestPage({ params }: { params: { locale: string } }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TestResult | null>(null);

  const testToken = async () => {
    setLoading(true);
    setResult(null);

    try {
      const res = await fetch('/api/polar/test-token', {
        method: 'POST',
      });

      const text = await res.text();
      let data;
      try {
        data = JSON.parse(text);
      } catch (parseErr) {
        // This is the case the user is hitting
        setResult({
          success: false,
          error: 'Server returned non-JSON response',
          details: `Status: ${res.status} ${res.statusText}\n\nBody:\n${text.substring(0, 2000)}`,
        });
        return;
      }
      setResult(data);
    } catch (err: any) {
      setResult({
        success: false,
        error: 'Network error',
        details: err.message,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white p-8">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold mb-2">Polar Token Tester</h1>
        <p className="text-gray-400 mb-8">
          Use this page to quickly verify if your <code>POLAR_ACCESS_TOKEN</code> is valid.
        </p>

        <button
          onClick={testToken}
          disabled={loading}
          className="px-6 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 rounded-xl font-medium transition"
        >
          {loading ? 'Testing token...' : 'Test Current Polar Token'}
        </button>

        {result && (
          <div className="mt-8 space-y-6">
            {/* Header + Server Info */}
            <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-5">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-xl font-semibold">Diagnostic Results</h2>
                <div className="text-xs px-3 py-1 rounded-full bg-gray-800 text-gray-400">
                  {result.serverUsed} • {result.baseUrlUsed}
                </div>
              </div>

              {result.token && (
                <div className="text-sm text-gray-400">
                  Token: <span className="font-mono text-gray-300">{result.token.prefix}</span> (length {result.token.length})
                </div>
              )}

              {result.conclusion && (
                <div className="mt-3 p-3 bg-gray-950 rounded-lg border border-gray-700 text-sm">
                  <span className="font-semibold text-amber-400">Conclusion:</span> {result.conclusion}
                </div>
              )}
            </div>

            {/* Side-by-side comparison */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* RAW FETCH */}
              <div className={`rounded-2xl border p-5 ${
                result.rawFetch?.success
                  ? 'bg-green-950/30 border-green-800'
                  : result.rawFetch
                    ? 'bg-red-950/30 border-red-800'
                    : 'bg-gray-900/50 border-gray-700'
              }`}>
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-lg">{result.rawFetch?.success ? '✅' : '❌'}</span>
                  <h3 className="font-semibold text-lg">Raw HTTP Fetch (native fetch)</h3>
                </div>
                <p className="text-xs text-gray-400 mb-3">Direct call to Polar API — this is the ground truth for token validity.</p>

                {result.rawFetch ? (
                  <div className="space-y-3 text-sm">
                    <div>
                      <span className="text-gray-400">Status:</span>{' '}
                      <span className={result.rawFetch.success ? 'text-green-400' : 'text-red-400'}>
                        {result.rawFetch.status} {result.rawFetch.statusText}
                      </span>
                    </div>
                    {result.rawFetch.url && (
                      <div className="text-xs break-all text-gray-500">{result.rawFetch.url}</div>
                    )}
                    {result.rawFetch.error && (
                      <div className="text-red-400">{result.rawFetch.error}: {result.rawFetch.details}</div>
                    )}
                    {result.rawFetch.body && (
                      <div>
                        <div className="text-gray-400 mb-1 text-xs">Response body:</div>
                        <pre className="bg-black/60 p-3 rounded-lg text-xs overflow-auto max-h-80">
                          {typeof result.rawFetch.body === 'string'
                            ? result.rawFetch.body
                            : JSON.stringify(result.rawFetch.body, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-gray-500 text-sm">No raw fetch result</p>
                )}
              </div>

              {/* SDK CALL */}
              <div className={`rounded-2xl border p-5 ${
                result.sdkCall?.success
                  ? 'bg-green-950/30 border-green-800'
                  : result.sdkCall
                    ? 'bg-red-950/30 border-red-800'
                    : 'bg-gray-900/50 border-gray-700'
              }`}>
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-lg">{result.sdkCall?.success ? '✅' : '❌'}</span>
                  <h3 className="font-semibold text-lg">Polar SDK Call (@polar-sh/sdk)</h3>
                </div>
                <p className="text-xs text-gray-400 mb-3">Using the exact same code path as create-checkout, resolve-key, etc.</p>

                {result.sdkCall ? (
                  <div className="space-y-3 text-sm">
                    {/* This is the critical diagnostic line */}
                    {result.sdkCall.actualSdkBaseUrl && (
                      <div className="mb-2 p-2 bg-black/70 rounded border border-yellow-900/50">
                        <div className="text-[10px] uppercase tracking-wide text-yellow-500 mb-0.5">
                          Actual base URL inside the live SDK instance:
                        </div>
                        <div className="font-mono text-xs break-all text-yellow-300">
                          {result.sdkCall.actualSdkBaseUrl}
                        </div>
                      </div>
                    )}

                    {result.sdkCall.success ? (
                      <>
                        {result.sdkCall.organizations && result.sdkCall.organizations.length > 0 && (
                          <div>
                            <div className="text-gray-400 mb-1 text-xs">Organizations returned by SDK:</div>
                            <ul className="space-y-1">
                              {result.sdkCall.organizations.map((org: any) => (
                                <li key={org.id} className="text-sm">
                                  • <strong>{org.name}</strong> <span className="text-gray-500">({org.id})</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {result.sdkCall.product && (
                          <div>
                            <div className="text-gray-400 mb-1 text-xs">Product lookup:</div>
                            <pre className="bg-black/60 p-3 rounded-lg text-xs overflow-auto">
                              {JSON.stringify(result.sdkCall.product, null, 2)}
                            </pre>
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="space-y-2">
                        <p className="text-red-400 font-medium">{result.sdkCall.error}</p>
                        {result.sdkCall.details && (
                          <pre className="bg-black/60 p-3 rounded-lg text-xs overflow-auto whitespace-pre-wrap">
                            {result.sdkCall.details}
                          </pre>
                        )}
                        {result.sdkCall.statusCode && (
                          <p className="text-xs text-gray-400">HTTP status from SDK: {result.sdkCall.statusCode}</p>
                        )}
                        {result.sdkCall.rawError && (
                          <details className="mt-2">
                            <summary className="cursor-pointer text-xs text-gray-500 hover:text-gray-300">Show raw SDK error object</summary>
                            <pre className="mt-2 bg-black/70 p-3 rounded text-[10px] overflow-auto max-h-64">
                              {JSON.stringify(result.sdkCall.rawError, null, 2)}
                            </pre>
                          </details>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-gray-500 text-sm">No SDK call result</p>
                )}
              </div>
            </div>

            <p className="text-xs text-gray-500 text-center">
              This page is for development/debugging only. Raw success + SDK failure = SDK is using the wrong base URL.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
