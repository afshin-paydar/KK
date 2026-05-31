import type { NextConfig } from "next";

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  transpilePackages: ["@kk/contracts"],
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${BACKEND}/api/:path*` },
      { source: "/enroll", destination: `${BACKEND}/enroll` },
    ];
  },
};

export default nextConfig;
