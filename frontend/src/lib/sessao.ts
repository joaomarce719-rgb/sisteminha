import { useMemo, useSyncExternalStore } from "react";
import { lerUsuarioDaAba, type StoredUser } from "./api";

function assinarStorage(aviso: () => void) {
  window.addEventListener("storage", aviso);
  return () => window.removeEventListener("storage", aviso);
}

const semAssinatura = () => () => {};

/**
 * Sessão desta aba (ver lib/api.ts), lida sem setState em efeito.
 *
 * Uma aba com sessão própria não muda quando outra aba entra com outro usuário;
 * a que ainda não tem sessão acompanha o último login (evento "storage").
 *
 * `montado` é false no servidor e durante a hidratação (o storage ainda
 * não pode ser lido), evitando redirecionar antes de conhecer a sessão.
 */
export function useSessao(): { montado: boolean; user: StoredUser | null } {
  const bruto = useSyncExternalStore(assinarStorage, lerUsuarioDaAba, () => null);
  const montado = useSyncExternalStore(semAssinatura, () => true, () => false);
  const user = useMemo(() => (bruto ? (JSON.parse(bruto) as StoredUser) : null), [bruto]);
  return { montado, user };
}
