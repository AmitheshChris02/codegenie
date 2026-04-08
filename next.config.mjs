/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    typedRoutes: true
  },
  webpack: (config) => {
    return config;
  }
};

export default nextConfig;
