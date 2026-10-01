import type { Metadata } from "next";
import "./globals.css";

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
      <body className="antialiased">{children}</body>
    </html>
  );
}
