import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Checagem otimista de navegação: redireciona antes de renderizar a página.
 * A autorização real é feita pela API (401/403); o cookie `sad_papel` só
 * indica o perfil da sessão e é gravado no login (ver `setStoredUser`).
 */
const AREAS: Record<string, string[]> = {
  "/gestor": ["GESTOR"],
  "/admin": ["GESTOR"],
  "/campo": ["CAMPO", "GESTOR"],
  "/vigia": ["VIGIA", "GESTOR"],
};

const INICIO_POR_PAPEL: Record<string, string> = {
  GESTOR: "/gestor/dashboard",
  CAMPO: "/campo/manejo",
  VIGIA: "/vigia/ronda",
};

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const area = Object.keys(AREAS).find((p) => pathname === p || pathname.startsWith(`${p}/`));
  if (!area) return NextResponse.next();

  const papel = request.cookies.get("sad_papel")?.value;
  if (!papel) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  if (!AREAS[area].includes(papel)) {
    return NextResponse.redirect(new URL(INICIO_POR_PAPEL[papel] ?? "/login", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/gestor/:path*", "/admin/:path*", "/campo/:path*", "/vigia/:path*"],
};
