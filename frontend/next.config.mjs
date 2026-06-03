import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin();

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  // serverActions is enabled by default in Next.js 14+
};

export default withNextIntl(nextConfig);