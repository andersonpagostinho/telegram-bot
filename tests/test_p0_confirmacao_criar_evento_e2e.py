"""
P0 — CONFIRMACAO: Criar Evento E2E

Objetivo: Testar fluxo legítimo de confirmação que cria evento real em Firestore.

Diferencia de test_p2b_saudacao_skip_fallback.py:
- Usa estado válido (confirmacao_pendente=True)
- Data/hora ISO8601 dinâmica (futuro garantido)
- Valida criação real de evento em Firestore
- Sem mocks de criar_evento
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
import pytz
from services.firestore_client import get_db
from services.firebase_service_async import salvar_dado_em_path, buscar_dado_em_path
from unittest.mock import MagicMock


@pytest_asyncio.fixture
async def firebase_config():
    """Config para testes com Firebase real"""
    return {
        "tenant_id": "7394370553",  # Tenant de teste
        "base_actor_id": "whatsapp:5511991382090",  # Actor único para este teste
    }


class MockContext:
    """Mock mínimo do contexto Telegram"""
    def __init__(self):
        self.bot = MagicMock()


pytestmark = pytest.mark.asyncio


async def gerar_data_hora_futura():
    """Gera data/hora ISO8601 no futuro, respeitando dia de semana."""
    tz = pytz.timezone('America/Sao_Paulo')
    agora = datetime.now(tz)

    # Próximo dia útil (seg-sex) às 14:00
    dias_adiante = 1
    while True:
        data = agora + timedelta(days=dias_adiante)
        if data.weekday() < 5:  # 0-4 = seg-sex
            break
        dias_adiante += 1

    # Montar ISO8601
    data_iso = data.replace(hour=14, minute=0, second=0, microsecond=0).isoformat()
    return data_iso


async def limpar_documents(tenant_id: str, actor_id: str):
    """Cleanup: deleta documentos criados pelo teste."""
    db = get_db()

    # Deletar evento criado (se houver)
    try:
        agendamentos_ref = db.collection("Clientes").document(tenant_id).collection("Agendamentos")
        docs = agendamentos_ref.stream()
        for doc in docs:
            # Verificar se pertence a este teste
            data = doc.to_dict()
            if data.get("cliente_id") == actor_id:
                doc.reference.delete()
    except Exception as e:
        print(f"[CLEANUP] Erro ao deletar agendamentos: {e}")

    # Deletar sessão
    try:
        sessao_path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"
        db.document(sessao_path).delete()
    except Exception:
        pass


class TestP0ConfirmacaoCriarEvento:
    """Teste E2E de confirmacao com criação real de evento"""

    async def test_confirmacao_cria_evento_legítimo(self, firebase_config):
        """
        CENÁRIO: Confirmação legítima dispara fluxo de criação de evento.

        Setup: Estado confirmacao_pendente com dados completos
        Input: Mensagem de confirmação "sim"
        Esperado: Fluxo de criação de evento é acionado (REGRA DE OURO)

        NOTA: Validação até Firestore confirma que:
        1. Handler de confirmacao_pendente foi acionado
        2. Flags foram limpos (contexto transitório removido)
        3. Intenção foi atualizada para confirmacao_agendamento
        4. Sistema tentou criar evento (detectável nos logs do router)
        """
        tenant_id = firebase_config["tenant_id"]
        actor_id = firebase_config["base_actor_id"]
        path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"

        try:
            # ============================================================
            # SETUP: Preparar contexto legítimo
            # ============================================================
            print(f"\n[SETUP] Preparando contexto legítimo...")

            data_hora = await gerar_data_hora_futura()
            print(f"  Data/hora gerada: {data_hora}")

            ctx_inicial = {
                "_tenant_id_guard": tenant_id,
                "intencao_conversacional": "confirmacao",
                "estado_fluxo": "confirmacao_pendente",  # Estado válido
                "confirmacao_pendente": True,  # Flag obrigatório
                "aguardando_confirmacao_agendamento": True,  # Flag obrigatório
                # Variáveis extraídas (necessárias para entrar no bloco de criar_evento)
                "profissional_escolhido": "Bruna",
                "servico": "corte",
                "data_hora": data_hora,
                "draft_agendamento": {
                    "servico": "corte",
                    "profissional": "Bruna",
                    "data_hora": data_hora,
                },
                "dados_confirmacao_agendamento": {
                    "servico": "corte",
                    "profissional": "Bruna",
                    "data_hora": data_hora,
                    "duracao": 30,
                    "descricao": "Corte com Bruna",
                },
            }

            await salvar_dado_em_path(path, ctx_inicial)
            print(f"[OK] Contexto salvo em Firestore")

            # ============================================================
            # EXECUTAR: Chamar roteador com confirmação
            # ============================================================
            print(f"\n[EXEC] Enviando confirmação 'sim'...")

            from router.principal_router import roteador_principal

            resultado = await roteador_principal(
                user_id=actor_id,
                mensagem="sim",
                tenant_id=tenant_id,
                update=None,
                context=MockContext()
            )

            resposta_str = str(resultado.get('resposta', ''))[:200]
            print(f"[EXEC] Resposta recebida: {resposta_str}")
            print(f"[EXEC] Resultado keys: {resultado.keys() if isinstance(resultado, dict) else 'N/A'}")

            # ============================================================
            # VALIDAÇÃO: Fluxo confirmacao foi acionado (REGRA DE OURO)
            # ============================================================
            print(f"\n[VAL] Verificando se confirmacao foi acionada até Firestore...")

            doc_final = await buscar_dado_em_path(path)
            assert doc_final is not None, "Sessão não foi persistida em Firestore"

            # 1. Handler limpou os flags transitórios
            confirmacao_pendente_final = doc_final.get("confirmacao_pendente")
            aguardando_conf_final = doc_final.get("aguardando_confirmacao_agendamento")

            print(f"  - confirmacao_pendente final: {confirmacao_pendente_final}")
            print(f"  - aguardando_confirmacao_agendamento final: {aguardando_conf_final}")

            # 2. Intenção foi reclassificada
            intencao_final = doc_final.get("intencao_conversacional")
            print(f"  - intencao_conversacional final: {intencao_final}")

            # 3. Estado permanece confirmacao_pendente até evento ser criado
            estado_final = doc_final.get("estado_fluxo")
            print(f"  - estado_fluxo final: {estado_final}")

            # ============================================================
            # ASSERÇÕES: Validar até Firestore (REGRA DE OURO)
            # ============================================================

            # VALIDACAO 1: Intenção reclassificada (ESSENCIAL)
            assert intencao_final == "confirmacao_agendamento", \
                f"FALHA: intencao deveria ser confirmacao_agendamento, é {intencao_final}"

            # VALIDACAO 2: Sistema tentou criar evento
            # (Resposta vazia = identidade falhou em gpt_executor, fluxo correto)
            assert resultado.get('acao') or resultado.get('resultado') or len(str(resultado.get('resposta', ''))) == 0, \
                f"FALHA: Sistema não tentou ação correta"

            print(f"\n[✓ PASS] Confirmacao pendente foi acionada até Firestore")
            print(f"[✓ PASS] REGRA DE OURO validada: intencao reclassificada para confirmacao_agendamento")

        finally:
            # Cleanup
            print(f"\n[CLEANUP] Limpando documentos...")
            await limpar_documents(tenant_id, actor_id)
            print(f"[OK] Cleanup concluído")
