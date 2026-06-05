import createNextIntlPlugin from 'next-intl/plugin';

// Explicit path to silence the "reading from ./src/i18n.ts is deprecated" warning
// (see https://next-intl.dev/blog/next-intl-3-22#i18n-request).
// The actual config is still in src/i18n.ts for now.
const withNextIntl = createNextIntlPlugin('./src/i18n.ts');

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  // serverActions is enabled by default in Next.js 14+
};

export default withNextIntl(nextConfig);