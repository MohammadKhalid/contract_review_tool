// Compatibility layer.
// New code should prefer importing directly from `@/polar` (official guide pattern).
import { polar } from "@/polar";

// ------------------------------------------------------------------
// In-memory webhook store (used by the Polar webhook handler and
// the resolve-key BFF route). This is intentionally simple and
// dev-only. In production you should persist granted keys in a DB
// or rely solely on Polar's licenseKeys.list / order lookups.
// ------------------------------------------------------------------
const grantedKeys = new Map<string, string>();

export function getLicenseKeyForId(id: string): string | undefined {
  return grantedKeys.get(id);
}

export function storeLicenseKey(id: string, key: string) {
  grantedKeys.set(id, key);
  // Auto-expire after 1 hour to prevent memory leaks in dev
  setTimeout(() => grantedKeys.delete(id), 60 * 60 * 1000);
}

export interface ResolvedLicenseKey {
  licenseKey: string;
  displayKey?: string;
  expiresAt?: string | null;
  usage?: number;
  limitUsage?: number | null;
  status?: string;
}

/**
 * Resolve the license key granted for a specific checkout.
 * Includes retry logic because benefit fulfillment can take a few seconds.
 */
export async function resolveLicenseKeyFromCheckout(
  checkoutId: string
): Promise<ResolvedLicenseKey | null> {
  const maxRetries = 6;
  const delayMs = 1500;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const checkout = await polar.checkouts.get({ id: checkoutId });

      const customerId =
        checkout?.customerId ??
        (checkout as any)?.customer_id ??
        (checkout as any)?.customer?.id;

      const orderId = (checkout as any)?.orderId ?? (checkout as any)?.order_id;

      console.log(`[Polar] resolve attempt ${attempt}/${maxRetries} for ${checkoutId}`, {
        status: checkout?.status,
        hasCustomerId: !!customerId,
        hasOrderId: !!orderId,
      });

      if (!checkout || checkout.status !== "succeeded") {
        if (attempt === maxRetries) return null;
        await new Promise((res) => setTimeout(res, delayMs));
        continue;
      }

      // Strategy 0 (most precise): Fetch the specific order and extract its license keys.
      // This is the best way to get the exact key for this checkout/purchase.
      if (orderId) {
        try {
          const order = await polar.orders.get({ id: orderId });
          const orderLicenseKeys = (order as any)?.licenseKeys || (order as any)?.license_keys || [];
          if (Array.isArray(orderLicenseKeys) && orderLicenseKeys.length > 0) {
            const key = orderLicenseKeys[0];
            const actualKey = typeof key === 'string' ? key : key.key;
            if (actualKey) {
              console.log("[Polar] ✅ Found license key directly on the order object");
              return {
                licenseKey: actualKey,
                displayKey: key.displayKey,
                expiresAt: key.expiresAt,
                usage: key.usage,
                limitUsage: key.limitUsage,
                status: key.status,
              };
            }
          }
        } catch (e: any) {
          console.log("[Polar] orders.get for specific order failed:", e?.message || e);
        }
      }

      // Strategy 1: Use org-level licenseKeys.list (works with backend access token)
      const orgId = process.env.POLAR_ORGANIZATION_ID;
      if (orgId && customerId) {
        try {
          const pageIterator: any = await polar.licenseKeys.list({
            organizationId: orgId,
            limit: 50,
          });

          const allKeys: any[] = [];

          if (Array.isArray(pageIterator)) {
            allKeys.push(...pageIterator);
          } else if (pageIterator?.result?.items) {
            allKeys.push(...pageIterator.result.items);
          } else if (pageIterator?.items) {
            allKeys.push(...pageIterator.items);
          } else {
            try {
              for await (const page of pageIterator) {
                const pageItems = page?.result?.items || page?.items || [];
                if (Array.isArray(pageItems)) allKeys.push(...pageItems);
              }
            } catch (iterErr) {
              console.log("[Polar] Could not iterate PageIterator for licenseKeys");
            }
          }

          const matchingKeys = allKeys.filter((k: any) =>
            k?.customerId === customerId ||
            k?.customer_id === customerId ||
            k?.customer?.id === customerId
          );

          if (matchingKeys.length > 0) {
            const key = matchingKeys[0];
            console.log("[Polar] ✅ Found license key via org-level licenseKeys.list");
            return {
              licenseKey: key.key,
              displayKey: key.displayKey,
              expiresAt: key.expiresAt,
              usage: key.usage,
              limitUsage: key.limitUsage,
              status: key.status,
            };
          } else {
            console.log(`[Polar] Org-level licenseKeys.list returned ${allKeys.length} keys total, 0 matched customer ${customerId}`);
          }
        } catch (e: any) {
          console.log("[Polar] org-level licenseKeys.list failed:", e?.message || e);
        }
      }

      // Strategy 2 (new): Try to find the order for this customer and check if it has license keys attached
      if (orgId && customerId) {
        try {
          const ordersIterator: any = await polar.orders.list({
            organizationId: orgId,
            customerId,
            limit: 10,
          });

          const orders: any[] = [];
          if (Array.isArray(ordersIterator)) {
            orders.push(...ordersIterator);
          } else if (ordersIterator?.result?.items) {
            orders.push(...ordersIterator.result.items);
          } else {
            try {
              for await (const page of ordersIterator) {
                const items = page?.result?.items || page?.items || [];
                if (Array.isArray(items)) orders.push(...items);
              }
            } catch {}
          }

          // Look for any license keys on the recent orders
          for (const order of orders) {
            const orderLicenseKeys = order?.licenseKeys || order?.license_keys;
            if (Array.isArray(orderLicenseKeys) && orderLicenseKeys.length > 0) {
              const key = orderLicenseKeys[0];
              console.log("[Polar] ✅ Found license key attached to order", order.id);
              return {
                licenseKey: key.key || key,
                displayKey: key.displayKey,
                expiresAt: key.expiresAt,
                usage: key.usage,
                limitUsage: key.limitUsage,
                status: key.status,
              };
            }
          }
        } catch (e: any) {
          console.log("[Polar] orders.list attempt failed:", e?.message || e);
        }
      }

      // Strategy 2: Fallback to customerPortal (sometimes works)
      if (customerId) {
        try {
          const resp: any = await (polar as any).customerPortal?.licenseKeys?.list?.({
            customerId,
            limit: 10,
          });
          const items = resp?.items ?? resp ?? [];
          if (items.length > 0) {
            const key = items[0];
            console.log("[Polar] ✅ Found license key via customerPortal.licenseKeys.list");
            return {
              licenseKey: key.key,
              displayKey: key.displayKey,
              expiresAt: key.expiresAt,
              usage: key.usage,
              limitUsage: key.limitUsage,
              status: key.status,
            };
          }
        } catch (e: any) {
          console.log("[Polar] customerPortal.licenseKeys.list attempt failed");
        }
      }

      // Strategy 3: Sometimes keys are embedded directly on the checkout after success
      const directKeys =
        (checkout as any)?.licenseKeys ||
        (checkout as any)?.license_keys ||
        (checkout as any)?.licenseKey;
      if (directKeys) {
        const key = Array.isArray(directKeys) ? directKeys[0] : directKeys;
        if (key) {
          console.log("[Polar] ✅ Found license key directly on checkout");
          return {
            licenseKey: key.key || key,
            displayKey: key.displayKey,
            expiresAt: key.expiresAt,
            usage: key.usage,
            limitUsage: key.limitUsage,
            status: key.status,
          };
        }
      }

      if (attempt < maxRetries) {
        console.log(`[Polar] No license key found yet for checkout ${checkoutId}. Retrying (${attempt}/${maxRetries})...`);
        await new Promise((res) => setTimeout(res, delayMs));
      }
    } catch (err: any) {
      console.error(`[Polar] Error resolving license key (attempt ${attempt}):`, err?.message || err);
      if (attempt < maxRetries) {
        await new Promise((res) => setTimeout(res, delayMs));
      }
    }
  }

  return null;
}

// Re-export the main client for convenience
export { polar } from "@/polar";

