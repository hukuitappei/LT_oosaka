import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: {
    API_URL: process.env.API_URL || "http://localhost:8000",
  },
};

if (process.env.NEXT_OUTPUT === "standalone") {
  nextConfig.output = "standalone";
}

export default nextConfig;
