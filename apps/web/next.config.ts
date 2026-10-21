import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  // OAuth callback query strings can contain one-time codes.
  logging: { incomingRequests: false, browserToTerminal: false },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "no-referrer" },
          { key: "X-Frame-Options", value: "DENY" },
          {
            key: "Content-Security-Policy",
            value: "frame-ancestors 'none'; base-uri 'self'; object-src 'none'",
          },
        ],
      },
      { source: "/auth/:path*", headers: [{ key: "Cache-Control", value: "private, no-store" }] },
      {
        source: "/:path(my-wines|occasions|profile)",
        headers: [{ key: "Cache-Control", value: "private, no-store" }],
      },
    ];
  },
};

export default nextConfig;
