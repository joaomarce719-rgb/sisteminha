import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      { source: "/viveiros", destination: "/gestor/viveiros", permanent: false },
      { source: "/simulacao", destination: "/gestor/simulacao", permanent: false },
      { source: "/financeiro", destination: "/gestor/financeiro", permanent: false },
      { source: "/auditoria", destination: "/gestor/auditoria", permanent: false },
      { source: "/usuarios", destination: "/gestor/usuarios", permanent: false },
      { source: "/painel-noturno", destination: "/gestor/painel-noturno", permanent: false },
      { source: "/biometria", destination: "/campo/biometria", permanent: false },
      { source: "/manejo", destination: "/campo/manejo", permanent: false },
      { source: "/ronda", destination: "/vigia/ronda", permanent: false },
    ];
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
