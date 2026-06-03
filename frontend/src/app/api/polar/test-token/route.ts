/**
 * Diagnostic endpoint: compares raw HTTP fetch vs @polar-sh/sdk call
 * using the exact same token and server configuration.
 *
 * This helps prove whether the token itself is valid (raw succeeds)
 * while the SDK is misconfigured (e.g. hitting wrong base URL).
 */
import { NextResponse } from "next/server";
import { getPolarClient, resetPolarClient } from "@/polar";

export async function POST() {
  const server = process.env.POLAR_SERVER || "sandbox";
  const isSandbox = server !== "production";
  const baseUrl = isSandbox
    ? "https://sandbox-api.polar.sh"
    : "https://api.polar.sh";

  const token = process.env.POLAR_ACCESS_TOKEN || "";
  const tokenInfo = {
    present: !!token,
    length: token.length,
    prefix: token ? token.substring(0, 18) + "..." : null,
  };

  const result: any = {
    serverUsed: server,
    baseUrlUsed: baseUrl,
    token: tokenInfo,
    rawFetch: null,
    sdkCall: null,
    conclusion: null,
    debug: {
      routeVersion: "2025-06-01-diag-v3-post-upgrade",
    },
  };

  // Safety wrapper so this diagnostic route never returns 500 HTML
  try {

  // === 1. Raw native fetch (this is known to work when token + URL are correct) ===
  try {
    const orgsUrl = `${baseUrl}/v1/organizations?limit=5`;
    const rawRes = await fetch(orgsUrl, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/json",
      },
    });

    const rawText = await rawRes.text();
    let rawBody: any;
    try {
      rawBody = JSON.parse(rawText);
    } catch {
      rawBody = rawText;
    }

    result.rawFetch = {
      success: rawRes.ok,
      status: rawRes.status,
      statusText: rawRes.statusText,
      url: orgsUrl,
      body: rawBody,
    };
  } catch (err: any) {
    result.rawFetch = {
      success: false,
      error: "Network / fetch error",
      details: err.message || String(err),
    };
  }

  // === 2. Polar SDK call (the one currently failing with 401) ===
  // Declare here so it's in scope for both success and catch paths
  let actualSdkBaseUrl: string | null = null;

  try {
    // For this diagnostic page only: force a fresh client so we test the *current* code
    // (the singleton may still hold an old instance created before the source edit).
    resetPolarClient();
    const polarClient = getPolarClient();

    // Expose what the live SDK instance actually thinks its base URL is
    try {
      const b = (polarClient as any).baseURL;
      actualSdkBaseUrl = b?.toString?.() || b?.href || null;
    } catch {
      // ignore introspection errors
    }

    // Organizations list
    const orgs = await polarClient.organizations.list({ limit: 5 });

    // Optional product lookup
    let productInfo = null;
    if (process.env.POLAR_ANALYSIS_PRODUCT_ID) {
      try {
        const product = await polarClient.products.get({
          id: process.env.POLAR_ANALYSIS_PRODUCT_ID,
        });
        productInfo = {
          id: product.id,
          name: product.name,
          priceCount: product.prices?.length || 0,
        };
      } catch (prodErr: any) {
        productInfo = {
          error: prodErr?.message || "Product fetch failed",
          status: prodErr?.status,
        };
      }
    }

    result.sdkCall = {
      success: true,
      actualSdkBaseUrl,
      organizations: orgs.items?.map((o: any) => ({
        id: o.id,
        name: o.name,
        slug: o.slug,
      })) || [],
      product: productInfo,
    };
  } catch (err: any) {
    const errorMessage =
      err?.body?.detail ||
      err?.message ||
      "Unknown error from Polar SDK";

    result.sdkCall = {
      success: false,
      actualSdkBaseUrl,
      error: "SDK call failed",
      details: errorMessage,
      statusCode: err?.status || 401,
      // Include the full error object for deeper debugging
      rawError: {
        name: err?.name,
        message: err?.message,
        status: err?.status,
        body: err?.body,
      },
    };
  }

  // === Conclusion helper ===
  const rawOk = result.rawFetch?.success === true;
  const sdkOk = result.sdkCall?.success === true;

  if (rawOk && sdkOk) {
    result.conclusion = "Both raw fetch and SDK succeed. Token + configuration are good.";
  } else if (rawOk && !sdkOk) {
    result.conclusion =
      "Raw HTTP works but SDK fails. This strongly indicates the SDK is using the wrong base URL (e.g. production instead of sandbox) or ignoring POLAR_SERVER.";
  } else if (!rawOk && sdkOk) {
    result.conclusion = "SDK works but raw fetch fails (unusual).";
  } else {
    result.conclusion = "Both fail. The token may be invalid, expired, or lack required scopes for this org.";
  }

    return NextResponse.json(result, { status: 200 });
  } catch (fatalErr: any) {
    // Never let this diagnostic route blow up with 500 HTML
    result.fatalError = {
      message: fatalErr?.message || String(fatalErr),
      stack: fatalErr?.stack?.split("\n").slice(0, 8),
    };
    return NextResponse.json(result, { status: 200 });
  }
}
