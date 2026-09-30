import type { Metadata } from "next";
import { Fraunces, Source_Sans_3 } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";

const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
});

const body = Source_Sans_3({
  subsets: ["latin"],
  variable: "--font-body",
});

export const metadata: Metadata = {
  title: "LeaderPulse — Feedback, Poll & Grade",
  description: "Campaign-based leader feedback, polling and unique employee ranking",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${display.variable} ${body.variable}`}>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
