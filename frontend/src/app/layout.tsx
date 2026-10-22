import type { Metadata } from "next";
import "./globals.css";
import { ToastProvider, Toaster } from "@/components/ui/toast";

export const metadata: Metadata = {
  title: "SAD Carcinicultura — Sistema de Apoio à Decisão",
  description:
    "Sistema bioeconômico para gerenciamento de viveiros de camarão Litopenaeus vannamei com motor fuzzy e algoritmo ΔV para decisão de despesca.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body className="antialiased bg-[#f8fafc] text-slate-900 min-h-screen">
        <ToastProvider>
          {children}
          <Toaster />
        </ToastProvider>
      </body>
    </html>
  );
}
