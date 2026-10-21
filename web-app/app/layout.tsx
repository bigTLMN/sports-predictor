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
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('edge-analytics-theme');if(t!=='light')document.documentElement.classList.add('dark')}catch(e){document.documentElement.classList.add('dark')}try{var n=parseInt(localStorage.getItem('edge-analytics-font'),10);if(!(n>=12&&n<=18))n=18;document.documentElement.style.fontSize=n+'px'}catch(e){document.documentElement.style.fontSize='18px'}})();`,
          }}
        />
      </head>
      <body className="antialiased font-sans bg-slate-100 dark:bg-slate-950">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}