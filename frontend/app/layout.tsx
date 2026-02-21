import type { Metadata } from "next";
import { JetBrains_Mono, Space_Grotesk } from "next/font/google";
import "./globals.css";
import SideNav from "@/components/SideNav";
import RootErrorBoundary from "@/components/RootErrorBoundary";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space",
});

const jetBrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
});

export const metadata: Metadata = {
  title: "Smart Network Traffic Analyzer",
  description: "Enterprise-grade network traffic analytics and ML anomaly detection",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${spaceGrotesk.variable} ${jetBrainsMono.variable} font-sans antialiased`}>
        <RootErrorBoundary>
          <div className="min-h-screen bg-[#0b0f13] text-zinc-100">
            <div className="flex min-h-screen">
              <SideNav />
              <div className="flex-1">
                <main className="px-6 py-6 lg:px-10 lg:py-8">
                  {children}
                </main>
              </div>
            </div>
          </div>
        </RootErrorBoundary>
      </body>
    </html>
  );
}
