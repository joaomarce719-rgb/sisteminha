"""SAD Carcinicultura — Carga de dados de exemplo (viveiros e preços).

Usa a organização mais antiga (criada pelo init_db ao subir a API em modo debug).
"""

from datetime import date
from sqlalchemy import select
from src.database import SessionLocal
from src.models.organizacao import Organizacao
from src.models.usuario import Usuario
from src.models.viveiro import Viveiro
from src.models.tabela_preco import TabelaPrecoMercado
from src.models.enums import RoleUsuario
from src.services.auth_service import hash_password

def seed():
    with SessionLocal() as db:
        org = db.scalars(select(Organizacao).order_by(Organizacao.created_at)).first()
        if org is None:
            print("Nenhuma organização encontrada. Suba a API com APP_DEBUG=true antes do seed.")
            return
        # 1. Usuários
        result = db.execute(select(Usuario).limit(1))
        if result.scalar_one_or_none() is None:
            print("Populando usuários...")
            usuarios = [
                Usuario(
                    nome_completo="Gestor da Fazenda",
                    email="gestor@sad.com",
                    senha_hash=hash_password("senha123"),
                    papel=RoleUsuario.GESTOR,
                    telefone_emergencia="(88) 99999-1111",
                    organizacao_id=org.id,
                ),
                Usuario(
                    nome_completo="Operador de Campo",
                    email="campo@sad.com",
                    senha_hash=hash_password("senha123"),
                    papel=RoleUsuario.CAMPO,
                    telefone_emergencia="(88) 99999-2222",
                    organizacao_id=org.id,
                ),
                Usuario(
                    nome_completo="Vigia Noturno",
                    email="vigia@sad.com",
                    senha_hash=hash_password("senha123"),
                    papel=RoleUsuario.VIGIA,
                    telefone_emergencia="(88) 99999-3333",
                    organizacao_id=org.id,
                ),
            ]
            db.add_all(usuarios)
            db.commit()
            print("Usuários criados com sucesso: gestor@sad.com, campo@sad.com, vigia@sad.com (senha: senha123)")
        else:
            print("Usuários já existem no banco.")

        # 2. Viveiros
        res_v = db.execute(select(Viveiro).where(Viveiro.organizacao_id == org.id).limit(1))
        if res_v.scalar_one_or_none() is None:
            print("Populando viveiros de exemplo...")
            viveiros = [
                Viveiro(
                    organizacao_id=org.id,
                    identificacao="VIV-01",
                    area_util_m2=12000.0,
                    profundidade_media_m=1.4,
                    localizacao="Setor Norte - Açude Principal",
                    status_ativo=True,
                ),
                Viveiro(
                    organizacao_id=org.id,
                    identificacao="VIV-02",
                    area_util_m2=15000.0,
                    profundidade_media_m=1.5,
                    localizacao="Setor Norte - Viveiro 2",
                    status_ativo=True,
                ),
                Viveiro(
                    organizacao_id=org.id,
                    identificacao="VIV-03",
                    area_util_m2=8000.0,
                    profundidade_media_m=1.3,
                    localizacao="Setor Sul - Berçário",
                    status_ativo=True,
                ),
            ]
            db.add_all(viveiros)
            db.commit()
            print("Viveiros criados com sucesso (VIV-01, VIV-02, VIV-03).")

        # 3. Preços de mercado
        res_p = db.execute(select(TabelaPrecoMercado).where(TabelaPrecoMercado.organizacao_id == org.id).limit(1))
        if res_p.scalar_one_or_none() is None:
            print("Populando tabela de preços base...")
            precos = [
                TabelaPrecoMercado(organizacao_id=org.id, faixa_gramatura_min=8.0, faixa_gramatura_max=10.0, preco_por_kg=18.50, vigencia_inicio=date.today()),
                TabelaPrecoMercado(organizacao_id=org.id, faixa_gramatura_min=10.0, faixa_gramatura_max=12.0, preco_por_kg=21.00, vigencia_inicio=date.today()),
                TabelaPrecoMercado(organizacao_id=org.id, faixa_gramatura_min=12.0, faixa_gramatura_max=14.0, preco_por_kg=24.50, vigencia_inicio=date.today()),
                TabelaPrecoMercado(organizacao_id=org.id, faixa_gramatura_min=14.0, faixa_gramatura_max=16.0, preco_por_kg=28.00, vigencia_inicio=date.today()),
                TabelaPrecoMercado(organizacao_id=org.id, faixa_gramatura_min=16.0, faixa_gramatura_max=20.0, preco_por_kg=32.00, vigencia_inicio=date.today()),
            ]
            db.add_all(precos)
            db.commit()
            print("Preços de mercado criados com sucesso.")

if __name__ == "__main__":
    seed()
