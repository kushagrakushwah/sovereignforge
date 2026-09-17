import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Dockerfile copies .next/standalone into the runtime image
  output: "standalone",
};

export default nextConfig;
