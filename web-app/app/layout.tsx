import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Edge Analytics | AI Sports Prediction",
  description: "Find the Value. Beat the Odds. Daily AI-driven sports betting analysis.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased bg-slate-100">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}