import { Polar } from "@polar-sh/sdk";

let _polar: Polar | null = null;

/**
 * Returns a properly configured Polar SDK client.
 *
 * IMPORTANT: The @polar-sh/sdk v0.7.x (our direct dep) does NOT support a `server` option.
 * It only understands `serverURL` or `serverIdx`. Passing `server: "sandbox"` is ignored
 * and the client would always hit production api.polar.sh (causing 401 with sandbox tokens).
 *
 * We therefore derive `serverURL` explicitly from POLAR_SERVER.
 */
export function getPolarClient(): Polar {
  if (!_polar) {
    if (!process.env.POLAR_ACCESS_TOKEN) {
      throw new Error("POLAR_ACCESS_TOKEN is not configured");
    }

    const server = (process.env.POLAR_SERVER || "sandbox").toLowerCase();
    const isProd = server === "production" || server === "prod";

    console.log(
      `[polar] Creating new SDK client (v0.40+) → server=${server}`
    );

    _polar = new Polar({
      accessToken: process.env.POLAR_ACCESS_TOKEN,
      // Modern versions of @polar-sh/sdk support the `server` option directly
      server: isProd ? "production" : "sandbox",
    });

    // Helpful for debugging: expose what the SDK actually resolved
    try {
      const internalBase = (_polar as any).baseURL?.toString?.();
      if (internalBase) {
        console.log(`[polar] SDK internal baseURL = ${internalBase}`);
      }
    } catch {
      // ignore
    }
  }
  return _polar;
}

/**
 * Force the next getPolarClient() call to create a fresh instance.
 * Useful in development when you change POLAR_SERVER or the client factory code.
 */
export function resetPolarClient(): void {
  if (_polar) {
    console.log("[polar] Resetting cached Polar client (will recreate on next use)");
  }
  _polar = null;
}

// For backward compatibility in some routes
export const polar = new Proxy({} as Polar, {
  get(target, prop) {
    return getPolarClient()[prop as keyof Polar];
  }
});

