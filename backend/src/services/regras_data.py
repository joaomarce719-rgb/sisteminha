"""SAD Carcinicultura — Regra de data dos lançamentos retroativos (compras, usos de insumo e vendas)."""

from datetime import date, datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status

from src.config import get_settings


@lru_cache
def _fuso(nome: str) -> ZoneInfo:
    return ZoneInfo(nome)


def hoje_da_fazenda() -> date:
    """Data de hoje no fuso da fazenda: com o servidor em UTC, date.today() já vira o dia às 21h."""
    return datetime.now(_fuso(get_settings().fazenda_fuso_horario)).date()


def exigir_retroativo_para_data_passada(data: date, retroativo: bool, rotulo: str) -> None:
    """Recusa data futura sempre e data passada sem a marca de lançamento retroativo."""
    hoje = hoje_da_fazenda()
    if data > hoje:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{rotulo} não pode estar no futuro.",
        )
    if data < hoje and not retroativo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{rotulo} é anterior a hoje: marque o lançamento como retroativo para registrar uma data passada.",
        )
