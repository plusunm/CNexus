import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "CNexus — Mind 概览",
  description: "Observational Cognition Platform — 心智系统实时状态总览",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
