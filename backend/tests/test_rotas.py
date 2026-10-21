"""Rotas com barra final também precisam existir sem ela.

O Next.js remove a barra final (308) antes do rewrite para o backend; se a rota só
existir com barra, o FastAPI redireciona (307) para o host do backend, o navegador
perde o header Authorization nesse redirecionamento entre origens e a sessão cai.
"""

from src.main import app


def test_toda_rota_com_barra_tem_versao_sem_barra():
    # O schema OpenAPI lista as rotas já com o prefixo dos routers incluídos
    rotas = {(metodo, caminho) for caminho, ops in app.openapi()["paths"].items() for metodo in ops}
    sem_par = sorted(
        f"{metodo} {caminho}"
        for metodo, caminho in rotas
        if caminho != "/" and caminho.endswith("/") and (metodo, caminho.rstrip("/")) not in rotas
    )
    assert not sem_par, sem_par


def test_biometria_sem_barra_responde_direto(client, gestor, novo_ciclo):
    ciclo = novo_ciclo()
    r = client.get(f"/api/v1/ciclos/{ciclo['id']}/biometrias", headers=gestor, follow_redirects=False)
    assert r.status_code == 200, r.status_code
