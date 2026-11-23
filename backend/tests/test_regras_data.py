"""Regra de data retroativa e validação da data de um registro dentro do ciclo."""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from src.services.regras_ciclo import validar_data_no_ciclo
from src.services.regras_data import exigir_retroativo_para_data_passada


def test_hoje_sem_retroativo_passa():
    exigir_retroativo_para_data_passada(date.today(), False, "A data da compra")


def test_passada_sem_retroativo_da_422_citando_retroativo():
    with pytest.raises(HTTPException) as exc:
        exigir_retroativo_para_data_passada(date.today() - timedelta(days=1), False, "A data da compra")
    assert exc.value.status_code == 422
    assert "retroativo" in exc.value.detail


def test_passada_com_retroativo_passa():
    exigir_retroativo_para_data_passada(date.today() - timedelta(days=30), True, "A data da compra")


def test_futura_da_422_mesmo_com_retroativo():
    with pytest.raises(HTTPException) as exc:
        exigir_retroativo_para_data_passada(date.today() + timedelta(days=1), True, "A data da compra")
    assert exc.value.status_code == 422
    assert "futuro" in exc.value.detail


def test_preparo_aceita_data_anterior_ao_povoamento():
    ciclo = SimpleNamespace(data_povoamento=date.today() - timedelta(days=10))
    anterior = ciclo.data_povoamento - timedelta(days=5)

    validar_data_no_ciclo(ciclo, anterior, "A data do uso", fase="PREPARO")

    with pytest.raises(HTTPException) as exc:
        validar_data_no_ciclo(ciclo, anterior, "A data do uso")
    assert exc.value.status_code == 422
    assert "anterior ao povoamento" in exc.value.detail


def test_preparo_continua_recusando_data_futura():
    ciclo = SimpleNamespace(data_povoamento=date.today())
    with pytest.raises(HTTPException) as exc:
        validar_data_no_ciclo(ciclo, date.today() + timedelta(days=1), "A data do uso", fase="PREPARO")
    assert "futuro" in exc.value.detail
