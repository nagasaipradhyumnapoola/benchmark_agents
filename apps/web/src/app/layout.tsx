import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { Providers } from "@/components/providers";
import { Workspace } from "@/components/workspace";
import "./globals.css";
export const metadata: Metadata = {
  title: "BenchLab — Experimental systems laboratory",
  description:
    "Local-first AI benchmarking with independently verified evidence.",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`dark ${GeistSans.variable} ${GeistMono.variable}`}
    >
      <body>
        <a href="#main-content" className="skip-link">
          Skip to content
        </a>
        <Providers>
          <Workspace>{children}</Workspace>
        </Providers>
      </body>
    </html>
  );
}
