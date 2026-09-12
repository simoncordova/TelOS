import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Telos",
  description: "Encuentra tu propósito y el sistema para sostenerlo.",
  manifest: "/manifest.json",
  icons: {
    icon: [
      { url: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: "/icon-192.png",
  },
};

export const viewport = {
  themeColor: "#d9b26a",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      {/* h-full + overflow-hidden (no min-h-full): la conversación
          necesita un marco de altura FIJA para que solo el chat scrollee
          por dentro -- con min-h-full, la página entera crecía con cada
          mensaje y el header/sidebar/input se perdían de vista (bug real
          reportado probando la app desplegada). */}
      <body className="flex h-full flex-col overflow-hidden">{children}</body>
    </html>
  );
}
