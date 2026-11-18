"""SAD Carcinicultura — Regra de data dos lançamentos retroativos (compras, usos de insumo e vendas)."""

from datetime import date

from fastapi import HTTPException, status


def exigir_retroativo_para_data_passada(data: date, retroativo: bool, rotulo: str) -> None:
    """Recusa data futura sempre e data passada sem a marca de lançamento retroativo."""
    hoje = date.today()
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
