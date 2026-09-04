import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Reachly — AI Hiring Assistant",
  description:
    "People search, voice outreach, and structured hiring insights powered by Hunar AI.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
