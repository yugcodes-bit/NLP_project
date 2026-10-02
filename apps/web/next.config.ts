import type { NextConfig } from "next";

// Static export (ADR-003): the site is plain files, hostable anywhere for free.
const nextConfig: NextConfig = {
  output: "export",
  reactStrictMode: true,
  images: { unoptimized: true },
};

export default nextConfig;
