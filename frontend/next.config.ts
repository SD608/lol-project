import type { NextConfig } from 'next';
const config: NextConfig = {
  async rewrites() {
    return [{source:'/api/counter-guide/:path*',destination:`${process.env.PICKOU_API_ORIGIN || 'http://127.0.0.1:8000'}/api/counter-guide/:path*`}];
  },
};
export default config;
