/**
 * BFF route: Create a Polar Checkout Session dynamically.
 *
 * Uses the modern Polar Checkout API (SDK >= 0.40) which requires `products: string[]`
 * instead of the legacy `productPriceId`.
 *
 * Requires POLAR_ANALYSIS_PRODUCT_ID in .env.
 */
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { polar } from "@/polar";

const BodySchema = z.object({
  customerEmail: z.string().email().optional(),
  customerName: z.string().optional(),
  metadata: z.record(z.string()).optional(),
  productPriceId: z.string().optional(), // for testing / override
  successUrl: z.string().url().optional(), // Optional: only provide if you want a specific return target. For embedded flows we prefer to omit this so the 'success' event can handle everything in-page without navigation.
});

export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => ({}));
    const parsed = BodySchema.safeParse(body);

    if (!parsed.success) {
      return NextResponse.json({ error: "Invalid request" }, { status: 400 });
    }

    const { customerEmail, customerName, metadata, successUrl: clientSuccessUrl } = parsed.data;

    // Using the centralized Polar client from src/polar.ts (as recommended in the official Next.js guide)

    // 2. Resolve the product ID to use for the new checkout API
    // In @polar-sh/sdk >= 0.40+, checkouts.create uses `products: string[]` (array of product IDs)
    // instead of the old `productPriceId`.
    const productId = process.env.POLAR_ANALYSIS_PRODUCT_ID;

    if (!productId) {
      return NextResponse.json(
        {
          error:
            "No Polar product configured. Set POLAR_ANALYSIS_PRODUCT_ID in your .env file.",
        },
        { status: 500 }
      );
    }

    // We no longer need to pre-resolve a price ID for basic one-time products.
    // Polar will use the product's active/default prices.
    // If you need to force a specific price in the future, use the `prices` override map.
    console.log(`[Polar] Creating checkout for product=${productId}`);

    const origin = req.headers.get("origin") || process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

    // 3. Create the checkout session using the modern `products` array (required in SDK v0.40+)
    const checkout = await polar.checkouts.create({
      products: [productId],
      customerEmail,
      customerName,
      metadata: {
        ...metadata,
        source: "contract-review-tool",
      },
      embedOrigin: origin,
      // IMPORTANT: We intentionally do NOT set successUrl by default.
      // For embedded checkout (PolarEmbedCheckout), setting a successUrl often causes
      // a full page navigation/redirect after payment, which destroys in-memory React state
      // (selected file, license key, analyzing state) and sends the user back to the first screen.
      // We rely exclusively on the client-side 'success' event listener to start analysis in-place.
      ...(clientSuccessUrl ? { successUrl: clientSuccessUrl } : {}),
    });

    return NextResponse.json({
      checkoutId: checkout.id,
      checkoutUrl: checkout.url,
    });
  } catch (err: any) {
    console.error("[Polar] create-checkout error", err);

    if (err?.message?.includes("Input validation failed")) {
      return NextResponse.json({ error: err.message }, { status: 400 });
    }

    return NextResponse.json(
      { error: err?.message || "Failed to create checkout" },
      { status: 500 }
    );
  }
}
