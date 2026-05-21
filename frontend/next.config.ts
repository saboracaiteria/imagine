import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  basePath: process.env.GITHUB_ACTIONS ? '/imagine' : '',
  images: {
    unoptimized: true, // Required for static export
  },
};

export default nextConfig;
