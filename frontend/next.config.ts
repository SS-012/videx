import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // Disable caching in development to ensure changes are visible
  ...(process.env.NODE_ENV === 'development' && {
    onDemandEntries: {
      maxInactiveAge: 25 * 1000,
      pagesBufferLength: 2,
    },
  }),
};

export default nextConfig;
