import type { NextConfig } from 'next';

const config: NextConfig = {
  // Ensure the large guide JSON is bundled with each serverless API route.
  outputFileTracingIncludes: {
    '/api/counter-guide/*': ['./data/counter-guide-26.22.json'],
  },
  async rewrites() {
    // Existing local launcher provides this variable and keeps using FastAPI.
    // Public Vercel deployments use the bundled Next.js API routes instead.
    if (!process.env.PICKOU_API_ORIGIN) return [];
    return [{
      source: '/api/counter-guide/:path*',
      destination: `${process.env.PICKOU_API_ORIGIN}/api/counter-guide/:path*`,
    }];
  },
};
export default config;
