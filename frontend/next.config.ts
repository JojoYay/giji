import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",   // Firebase Hosting 用の静的エクスポート
  trailingSlash: true, // Firebase Hosting は index.html で解決するため
};

export default nextConfig;
