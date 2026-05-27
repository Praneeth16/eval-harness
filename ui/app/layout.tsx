import type { Metadata } from "next";
import "./globals.css";
import { fontVars } from "./fonts";
import { Sidebar } from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "eval-harness",
  description:
    "Self-evolving eval harness for production AI agents. Agents learn from their own failures here.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${fontVars} dark`}>
      <body className="bg-canvas text-ink-primary antialiased">
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 min-w-0">{children}</main>
        </div>
      </body>
    </html>
  );
}
