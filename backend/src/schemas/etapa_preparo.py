"""SAD Carcinicultura — Schemas Pydantic das etapas do preparo."""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

TipoEtapa = Literal["SECAGEM", "CALAGEM", "ADUBACAO", "ABASTECIMENTO", "TRATAMENTO_AGUA", "OUTRA"]
StatusEtapa = Literal["PENDENTE", "EM_ANDAMENTO", "CONCLUIDA", "NAO_REALIZADA"]

# lista sugerida criada ao planejar o ciclo, nesta ordem
ETAPAS_SUGERIDAS: tuple[TipoEtapa, ...] = ("SECAGEM", "CALAGEM", "ADUBACAO", "ABASTECIMENTO", "TRATAMENTO_AGUA")
# o povoamento espera estas etapas serem resolvidas (concluídas ou não realizadas)
STATUS_ETAPA_EM_ABERTO = ("PENDENTE", "EM_ANDAMENTO")


class EtapaPreparoUpdate(BaseModel):
    """Campos que o gestor e o campo atualizam; só os enviados mudam. As datas podem ser futuras."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: StatusEtapa | None = None
    data_inicio: date | None = None
    data_fim: date | None = None
    observacao: str | None = Field(None, max_length=255)

    @model_validator(mode="after")
    def status_nao_nulo(self) -> "EtapaPreparoUpdate":
        if "status" in self.model_fields_set and self.status is None:
            raise ValueError("O status da etapa não pode ser vazio.")
        return self


class EtapaPreparoCreate(EtapaPreparoUpdate):
    tipo: TipoEtapa
    status: StatusEtapa = "PENDENTE"
    # sem ordem, a etapa vai para o fim da lista; Integer = 32 bits
    ordem: int | None = Field(None, ge=1, le=2_147_483_647)


class EtapaPreparoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ciclo_id: UUID
    tipo: TipoEtapa
    status: StatusEtapa
    data_inicio: date | None
    data_fim: date | None
    observacao: str | None
    ordem: int
