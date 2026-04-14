import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { AuthProvider } from "@/components/auth/auth-provider";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import "./globals.css";

const geist = Geist({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans"
});

const geistMono = Geist_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-mono"
});

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1
};

export const metadata: Metadata = {
  title: "Satta",
  description: "Community-driven prediction markets with live matching, moderation, and settlement."
};

export default async function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user }
  } = await supabase.auth.getUser();

  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${geist.variable} ${geistMono.variable}`} suppressHydrationWarning>
        <AuthProvider initialAccessToken={null} initialUser={user ?? null}>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
