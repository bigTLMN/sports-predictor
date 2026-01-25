import type { Metadata } from "next";
import "./globals.css";

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
    <html lang="en">
      <body className="antialiased bg-slate-100">
        {children}
      </body>
    </html>
  );
}