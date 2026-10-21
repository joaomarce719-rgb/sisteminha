"""SAD Carcinicultura — Pacote de modelos SQLAlchemy.

Importa todos os modelos para que o metadata do Base os registre
e o Alembic / init_db() possam criar as tabelas.
"""

from src.models.auditoria import LogAuditoria
from src.models.biometria import Biometria
from src.models.ciclo_produtivo import CicloProdutivo
from src.models.custo_operacional import CustoOperacional
from src.models.manejo_alimentar import ManejoAlimentar
from src.models.monitoramento_aerador import MonitoramentoAerador
from src.models.organizacao import Organizacao
from src.models.propriedade import Propriedade
from src.models.ronda_noturna import RondaNoturna
from src.models.simulacao_despesca import SimulacaoDespesca
from src.models.tabela_alimentar import TabelaAlimentar
from src.models.tabela_preco import TabelaPrecoMercado
from src.models.usuario import Usuario
from src.models.viveiro import Viveiro

__all__ = [
    "Biometria",
    "CicloProdutivo",
    "CustoOperacional",
    "LogAuditoria",
    "ManejoAlimentar",
    "MonitoramentoAerador",
    "Organizacao",
    "Propriedade",
    "RondaNoturna",
    "SimulacaoDespesca",
    "TabelaAlimentar",
    "TabelaPrecoMercado",
    "Usuario",
    "Viveiro",
]
