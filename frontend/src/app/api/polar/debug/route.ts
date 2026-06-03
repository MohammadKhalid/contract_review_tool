/**
 * Debug endpoint for Polar token and product issues.
 * Visit: http://localhost:3000/api/polar/debug
 *
 * This helps diagnose authentication and product access problems.
 */
import { NextResponse } from "next/server";
import { polar } from "@/polar";

export async function GET() {
  const debugInfo: any = {
    timestamp: new Date().toISOString(),
    environment: {
      POLAR_SERVER: process.env.POLAR_SERVER || "sandbox",
      has_POLAR_ACCESS_TOKEN: !!process.env.POLAR_ACCESS_TOKEN,
      POLAR_ACCESS_TOKEN_prefix: process.env.POLAR_ACCESS_TOKEN
        ? process.env.POLAR_ACCESS_TOKEN.substring(0, 18) + "..."
        : null,
      POLAR_ORGANIZATION_ID: process.env.POLAR_ORGANIZATION_ID,
      POLAR_ANALYSIS_PRODUCT_ID: process.env.POLAR_ANALYSIS_PRODUCT_ID,
    },
    tests: {},
  };

  try {
    // Using centralized client from @/polar (official guide pattern)
    debugInfo.clientInitialized = true;
  } catch (e: any) {
    debugInfo.clientInitialized = false;
    debugInfo.clientError = e.message;
    return NextResponse.json(debugInfo, { status: 500 });
  }

  // Test 1: List organizations the token can access
  try {
    const orgs = await polar.organizations.list({ limit: 10 });
    debugInfo.tests.listOrganizations = {
      success: true,
      count: orgs.items?.length ?? 0,
      organizations: orgs.items?.map((org: any) => ({
        id: org.id,
        name: org.name,
        slug: org.slug,
      })) ?? [],
    };
  } catch (e: any) {
    debugInfo.tests.listOrganizations = {
      success: false,
      error: e.message,
      status: e.status,
    };
  }

  // Test 2: Try to fetch the configured product
  if (process.env.POLAR_ANALYSIS_PRODUCT_ID) {
    try {
      const product = await polar.products.get({
        id: process.env.POLAR_ANALYSIS_PRODUCT_ID,
      });

      debugInfo.tests.getProduct = {
        success: true,
        product: {
          id: product.id,
          name: product.name,
          organizationId: product.organizationId,
          prices: product.prices?.map((p: any) => ({
            id: p.id,
            type: p.type,
            amount: p.priceAmount ?? p.amount,
          })) ?? [],
        },
      };
    } catch (e: any) {
      debugInfo.tests.getProduct = {
        success: false,
        error: e.message,
        status: e.status,
        raw: e.body ?? null,
      };
    }
  } else {
    debugInfo.tests.getProduct = {
      skipped: true,
      reason: "POLAR_ANALYSIS_PRODUCT_ID not set",
    };
  }

  // Test 3: Token introspection (Note: This often fails for Organization Access Tokens - not very useful)
  try {
    const token = process.env.POLAR_ACCESS_TOKEN;
    const polarBase = process.env.POLAR_SERVER === "production" 
      ? "https://api.polar.sh" 
      : "https://sandbox-api.polar.sh";

    const introspectRes = await fetch(`${polarBase}/v1/oauth2/introspect`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({ token: token || "" }),
    });

    const introspectData = await introspectRes.json();

    debugInfo.tests.tokenIntrospection = {
      success: introspectRes.ok,
      active: introspectData.active,
      scope: introspectData.scope,
      client_id: introspectData.client_id,
      username: introspectData.username,
      raw: introspectData,
    };
  } catch (e: any) {
    debugInfo.tests.tokenIntrospection = {
      success: false,
      error: e.message,
    };
  }

  // Test 4+: More aggressive permission probing
  // These help reveal the exact scope boundary of the token
  const additionalTests: string[] = [
    "products.list",
    "checkouts.list",
    "orders.list",
    "customers.list",
    "benefits.list",
  ];

  debugInfo.tests.additionalEndpointTests = {};

  for (const test of additionalTests) {
    try {
      let result;
      switch (test) {
        case "products.list":
          result = await polar.products.list({ limit: 3 });
          break;
        case "checkouts.list":
          result = await polar.checkouts.list({ limit: 3 });
          break;
        case "orders.list":
          result = await polar.orders.list({ limit: 3 });
          break;
        case "customers.list":
          result = await polar.customers.list({ limit: 3 });
          break;
        case "benefits.list":
          result = await polar.benefits.list({ limit: 3 });
          break;
        default:
          result = { skipped: true };
      }

      debugInfo.tests.additionalEndpointTests[test] = {
        success: true,
        count: (result as any)?.items?.length ?? (result as any)?.length ?? "unknown",
      };
    } catch (e: any) {
      debugInfo.tests.additionalEndpointTests[test] = {
        success: false,
        error: e.message,
        status: e.status,
      };
    }
  }

  return NextResponse.json(debugInfo, { status: 200 });
}
