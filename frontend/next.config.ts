/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // Only proxy in development, not in production
    if (process.env.NODE_ENV === 'development') {
      return [
        {
          source: '/api/:path*',
          destination: 'http://localhost:8000/api/:path*', // Proxy to FastAPI backend in dev
        },
      ];
    }
    return [];
  },
};

module.exports = nextConfig;
