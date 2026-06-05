import { validateEvent, WebhookVerificationError } from "@polar-sh/sdk/webhooks";
import { storeLicenseKey } from "@/lib/polar";

// Note: getLicenseKeyForId is also provided by @/lib/polar for use by
// other server routes (e.g. resolve-key). It is deliberately NOT exported
// from this route handler file.

/**
 * Polar Webhook Handler (manual validation)
 *
 * This is more reliable than the high-level Webhooks() helper in some
 * Next.js + Docker + Turbopack environments.
 *
 * NOTE: Only route-handler exports (POST, GET, etc.) are allowed here.
 * Shared helpers like getLicenseKeyForId / storeLicenseKey live in
 * src/lib/polar.ts so Next.js type checking for routes doesn't complain.
 */
export async function POST(request: Request) {
  const body = await request.text();
  const headers: Record<string, string> = {};

  request.headers.forEach((value, key) => {
    headers[key] = value;
  });

  try {
    const payload = validateEvent(body, headers, process.env.POLAR_WEBHOOK_SECRET!);

    console.log(`[Polar Webhook] ${payload.type}`);

    // === Order Events ===
    if (payload.type === "order.paid") {
      const order = payload.data;
      console.log("[Polar] Order paid:", {
        orderId: order.id,
        customerId: order.customerId,
        productId: order.productId,
        amount: (order as any).amount ?? order.totalAmount ?? order.netAmount,
      });
    }

    // === Benefit Grant Events (Most reliable for License Keys) ===
    if (payload.type === "benefit_grant.created") {
      const grant: any = payload.data;

      console.log("[Polar] Benefit grant created:", {
        grantId: grant.id,
        benefitId: grant.benefitId,
        customerId: grant.customerId,
        orderId: grant.orderId,
        type: grant.benefitType,
      });

      if (grant.benefitType === "license_keys") {
        console.log("[Polar] Raw license_keys grant object:", JSON.stringify(grant, null, 2));

        const licenseKey =
          grant.properties?.key ||
          grant.key ||
          grant.licenseKey ||
          grant.benefit?.properties?.key ||
          grant.benefit?.properties?.licenseKey ||
          grant.properties?.licenseKey ||
          (Array.isArray(grant.properties?.keys) ? grant.properties.keys[0] : null);

        if (licenseKey) {
          console.log("[Polar] ✅ License Key granted via webhook:", licenseKey);

          if (grant.orderId) {
            storeLicenseKey(grant.orderId, licenseKey);
          }
          if (grant.checkoutId) {
            storeLicenseKey(grant.checkoutId, licenseKey);
          }
          if (grant.customerId) {
            storeLicenseKey(`customer:${grant.customerId}`, licenseKey);
          }
        } else {
          console.warn("[Polar] ⚠️ Saw license_keys benefit grant but could not find the key in known locations.");
        }
      }
    }

    if (payload.type === "benefit_grant.updated") {
      console.log("[Polar] Benefit grant updated:", (payload.data as any).id);
    }

    if (payload.type === "benefit_grant.revoked") {
      console.log("[Polar] Benefit grant revoked:", (payload.data as any).id);
    }

    return new Response(null, { status: 200 });
  } catch (error) {
    if (error instanceof WebhookVerificationError) {
      console.error("[Polar Webhook] Signature verification failed");
      return new Response("Invalid signature", { status: 403 });
    }

    console.error("[Polar Webhook] Error:", error);
    return new Response("Internal server error", { status: 500 });
  }
}
