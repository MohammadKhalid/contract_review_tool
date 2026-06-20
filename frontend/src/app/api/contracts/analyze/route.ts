/**
 * BFF route: proxy contract analysis to the FastAPI backend.
 *
 * Browser calls same-origin /api/contracts/analyze (excluded from next-intl
 * locale prefixing). The Next.js server forwards the upload to the backend
 * over the internal Docker network.
 */
import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL =
  process.env.BACKEND_INTERNAL_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  'http://localhost:5001';

export async function POST(req: NextRequest) {
  const lang = req.nextUrl.searchParams.get('lang') || 'de';
  const apiKey = req.headers.get('x-api-key');

  let formData: FormData;
  try {
    formData = await req.formData();
  } catch {
    return NextResponse.json({ detail: 'Invalid form data' }, { status: 400 });
  }

  const headers: Record<string, string> = {};
  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }

  let backendRes: Response;
  try {
    backendRes = await fetch(
      `${BACKEND_URL}/contracts/analyze?lang=${encodeURIComponent(lang)}`,
      {
        method: 'POST',
        body: formData,
        headers,
      }
    );
  } catch (err) {
    console.error('[contracts/analyze] backend unreachable:', err);
    return NextResponse.json(
      { detail: 'Analysis service is temporarily unavailable' },
      { status: 502 }
    );
  }

  const contentType = backendRes.headers.get('content-type') || 'application/json';
  const body = await backendRes.text();

  return new NextResponse(body, {
    status: backendRes.status,
    headers: { 'Content-Type': contentType },
  });
}