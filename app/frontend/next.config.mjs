import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  pageExtensions: ['tsx', 'ts'],
  webpack: (config) => {
    // Ignore .ci_trigger files in pages directory
    config.plugins.push({
      apply: (compiler) => {
        compiler.hooks.normalModuleFactory.tap('IgnoreCITrigger', (nmf) => {
          nmf.hooks.beforeResolve.tap('IgnoreCITrigger', (data) => {
            if (data.request && data.request.includes('.ci_trigger')) {
              return false;
            }
          });
        });
      },
    });
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': path.resolve(__dirname, 'src'),
    };
    return config;
  },
  async rewrites() {
    // Proxy API requests to backend in Docker E2E environment
    const apiBase = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8100';
    return [
      {
        source: '/api/:path*',
        destination: `${apiBase}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
