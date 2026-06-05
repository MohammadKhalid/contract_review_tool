/**
 * BFF route: Given a checkout_id (returned after embedded success),
 * return the Polar license key that was granted to the customer.
 * This is the bridge that delivers the "access token" to the frontend
 * without exposing the Polar secret.
 */
import { NextRequest, NextResponse } from "next/server";
import { resolveLicenseKeyFromCheckout, getLicenseKeyForId } from "@/lib/polar";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const checkoutId = searchParams.get("checkout_id");

  if (!checkoutId) {
    return NextResponse.json({ error: "Missing checkout_id" }, { status: 400 });
  }

  try {
    // Fast path from webhook store (by checkoutId)
    let keyFromWebhook = getLicenseKeyForId(checkoutId);

    // Also try to resolve the orderId from the checkout and check the store under that ID
    if (!keyFromWebhook) {
      try {
        const checkout = await (await import("@/polar")).polar.checkouts.get({ id: checkoutId });
        const orderId = (checkout as any)?.orderId ?? (checkout as any)?.order_id;
        if (orderId) {
          keyFromWebhook = getLicenseKeyForId(orderId);
        }
        // Also try customer-based key we store in webhook as fallback
        const customerId = (checkout as any)?.customerId ?? (checkout as any)?.customer_id;
        if (!keyFromWebhook && customerId) {
          keyFromWebhook = getLicenseKeyForId(`customer:${customerId}`);
        }
      } catch {}
    }

    if (keyFromWebhook) {
      return NextResponse.json({
        licenseKey: keyFromWebhook,
        source: "webhook",
      });
    }

    // Fallback: Call Polar directly (with retries inside the function)
    // Now uses org-level licenseKeys.list which works with the backend token
    const keyInfo = await resolveLicenseKeyFromCheckout(checkoutId);

    if (!keyInfo) {
      return NextResponse.json(
        { error: "Could not find a license key for this checkout. Check your email or Polar customer portal." },
        { status: 404 }
      );
    }

    return NextResponse.json({
      ...keyInfo,
      source: "polar_api",
    });
  } catch (err: any) {
    console.error("[Polar] resolve-key error", err);
    return NextResponse.json(
      { error: "Failed to resolve license key" },
      { status: 500 }
    );
  }
}
