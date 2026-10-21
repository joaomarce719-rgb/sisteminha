"""Alertas gerados nas rondas noturnas (RF-021)."""

RONDA_BASE = {
    "data_hora_ronda": "2026-10-20T02:00:00",
    "temperatura_agua_c": 28,
    "aeradores_instalados": 4,
    "aeradores_ligados": 4,
}


def _ronda(client, headers, ciclo_id, **campos):
    r = client.post(
        "/api/v1/rondas-noturnas/",
        json={**RONDA_BASE, "ciclo_id": ciclo_id, "oxigenio_dissolvido_mg_l": 5.0, **campos},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_o2_critico_gera_alerta_persistido(client, vigia, gestor, novo_ciclo):
    ciclo = novo_ciclo()
    ronda = _ronda(client, vigia, ciclo["id"], oxigenio_dissolvido_mg_l=1.5)
    assert [a["codigo"] for a in ronda["alertas"]] == ["ANOXIA_EMERGENCIA"]
    assert ronda["alertas"][0]["nivel"] == "CRITICO"

    abertos = client.get(f"/api/v1/alertas/?status_alerta=ABERTO&ciclo_id={ciclo['id']}", headers=gestor).json()
    assert len(abertos) == 1


def test_ronda_normal_sem_alerta(client, vigia, novo_ciclo):
    ciclo = novo_ciclo()
    assert _ronda(client, vigia, ciclo["id"])["alertas"] == []


def test_queda_de_energia_gera_alerta(client, vigia, novo_ciclo):
    ciclo = novo_ciclo()
    ronda = _ronda(client, vigia, ciclo["id"], fonte_energia="SEM_ENERGIA_QUEDA")
    assert "SEM_ENERGIA" in [a["codigo"] for a in ronda["alertas"]]


def test_resolver_alerta(client, vigia, gestor, novo_ciclo):
    ciclo = novo_ciclo()
    alerta = _ronda(client, vigia, ciclo["id"], oxigenio_dissolvido_mg_l=3.0)["alertas"][0]

    url = f"/api/v1/alertas/{alerta['id']}/resolver"
    assert client.put(url, json={"observacao": "Aeração ligada"}, headers=vigia).status_code == 403
    r = client.put(url, json={"observacao": "Aeração ligada"}, headers=gestor)
    assert r.status_code == 200
    assert r.json()["status"] == "RESOLVIDO"
    assert client.put(url, json={}, headers=gestor).status_code == 400
