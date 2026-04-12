import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Trading Platform",
  description: "Multi-role trading workstation",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
