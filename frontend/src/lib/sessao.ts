import { useMemo, useSyncExternalStore } from "react";
import type { StoredUser } from "./api";

function assinarStorage(aviso: () => void) {
  window.addEventListener("storage", aviso);
  return () => window.removeEventListener("storage", aviso);
}

const semAssinatura = () => () => {};

/**
 * Sessão salva no localStorage, lida sem setState em efeito.
 *
 * `montado` é false no servidor e durante a hidratação (o localStorage ainda
 * não pode ser lido), evitando redirecionar antes de conhecer a sessão.
 */
export function useSessao(): { montado: boolean; user: StoredUser | null } {
  const bruto = useSyncExternalStore(
    assinarStorage,
    () => localStorage.getItem("sad_user"),
    () => null
  );
  const montado = useSyncExternalStore(semAssinatura, () => true, () => false);
  const user = useMemo(() => (bruto ? (JSON.parse(bruto) as StoredUser) : null), [bruto]);
  return { montado, user };
}
