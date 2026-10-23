import type { NextConfig } from "next";
import { fileURLToPath } from "node:url";
const config: NextConfig = {
  output: "standalone",
  turbopack: { root: fileURLToPath(new URL(".", import.meta.url)) },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.BENCH_AGENTS_API_URL || process.env.BENCHLAB_API_URL || "http://127.0.0.1:8000"}/api/:path*`,
      },
    ];
  },
};
export default config;
