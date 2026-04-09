import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "AAMSIR - Intelligent Document Retrieval",
  description:
    "Adaptive Architecture for Multi-Strategy Information Retrieval",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full flex antialiased">
        <Sidebar />
        <main className="flex-1 flex flex-col min-h-screen ml-0 lg:ml-64 transition-[margin] duration-300">
          {children}
        </main>
      </body>
    </html>
  );
}
