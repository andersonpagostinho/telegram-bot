"""
Fixture Firebase Real para todos os testes P0.1 e FASE 2.4F

Converte testes mock para usar Firestore real:
- Tenant: 7394370553
- Cliente: 7371670478
- WhatsApp: 5511991382080 -> whatsapp:5511991382080

Uso:
    pytest tests/test_p01_*.py --firebase-real
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Path setup
raiz_projeto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, raiz_projeto)

import pytest
from services.firestore_client import get_db
from services.firebase_service_async import (
    atualizar_dado_em_path,
    buscar_dado_em_path,
    salvar_dado_em_path
)
from utils.contexto_temporario import (
    salvar_contexto_temporario_v2,
    carregar_contexto_temporario_v2
)
from services.identidade_service import normalizar_actor_id


@pytest.fixture(scope="session")
def firebase_config():
    """Configuracao Firebase real (production)"""
    return {
        "tenant_id": "7394370553",
        "cliente_id": "7371670478",
        "wa_id": "5511991382080",
        "actor_id": normalizar_actor_id("whatsapp", "5511991382080"),
        "db": get_db()
    }


@pytest.fixture(scope="function")
async def firebase_contexto(firebase_config):
    """
    Contexto Firebase real para cada teste

    Fornece:
    - db (Firestore real)
    - tenant_id
    - cliente_id
    - actor_id
    - funções: salvar(), carregar(), limpar()
    """
    config = firebase_config

    class FirebaseContexto:
        def __init__(self, cfg):
            self.db = cfg["db"]
            self.tenant_id = cfg["tenant_id"]
            self.cliente_id = cfg["cliente_id"]
            self.wa_id = cfg["wa_id"]
            self.actor_id = cfg["actor_id"]

        async def salvar(self, dados_ctx: dict):
            """Salvar contexto no Firestore"""
            await salvar_contexto_temporario_v2(
                self.tenant_id,
                self.cliente_id,
                dados_ctx
            )
            return dados_ctx

        async def carregar(self):
            """Carregar contexto do Firestore"""
            return await carregar_contexto_temporario_v2(
                self.tenant_id,
                self.cliente_id
            )

        async def limpar(self):
            """Limpar contexto anterior"""
            try:
                ref = self.db.collection("Clientes").document(self.tenant_id).collection("Sessoes").document(self.cliente_id)
                await asyncio.to_thread(ref.delete)
            except:
                pass

        async def setup_confirmacao_pendente(self):
            """Setup padrao: confirmacao pendente com alternativas"""
            ctx = {
                "estado_fluxo": "agandando",
                "modo_escolha_horario": True,  # Estado corrompido
                "intencao_conversacional": "confirmacao_agendamento",
                "aguardando_confirmacao_agendamento": True,
                "dados_confirmacao_agendamento": {
                    "profissional": "Gloria",
                    "servico": "Corte",
                    "data_hora": (datetime.now() + timedelta(days=1)).isoformat() + "T14:00:00",
                    "duracao": 30,
                    "descricao": "Corte com Gloria"
                },
                "draft_agendamento": {
                    "profissional": "Gloria",
                    "data_hora": (datetime.now() + timedelta(days=1)).isoformat() + "T14:00:00",
                    "servico": "Corte",
                    "modo_prechecagem": True
                },
                "alternativa_profissional": ["Bruna", "Joana"],
                "ultima_opcao_profissionais": ["Gloria", "Bruna", "Joana"],
                "horarios_sugeridos": ["15:00", "16:00", "17:00"],
                "servico": "Corte",
                "profissional_escolhido": "Gloria",
                "data_hora": (datetime.now() + timedelta(days=1)).isoformat() + "T14:00:00",
                "ultima_acao": "criar_evento"
            }
            return await self.salvar(ctx)

    fc = FirebaseContexto(config)
    await fc.limpar()
    yield fc
    await fc.limpar()


def pytest_configure(config):
    """Configurar pytest para Firebase real"""
    config.addinivalue_line(
        "markers",
        "firebase_real: marca teste como Firebase real (nao mock)"
    )
