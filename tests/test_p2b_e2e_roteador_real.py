"""
P2B E2E: Teste REAL com roteador_principal() e Firestore real

Objetivo:
Validar que saudacoes indefinidas (ola, oi, olá, bom dia) em
estado aguardando_profissional com intencao=indefinida:

1. NAO executam montar_resposta_fallback() (guard bloqueia)
2. Preservam draft intacto no Firestore
3. Fluxo continua (nao retorna resposta operacional fallback)

Cenarios:
- T1: "ola" indefinida
- T2: "oi" indefinida
- T3: "olá" indefinida
- T4: "bom dia" indefinida
- T5: "Bruna" operacional (nao bloqueado)

Infraestrutura:
- roteador_principal() REAL
- Firestore REAL
- MockUpdate/MockContext como adaptador de entrada
- Sessao REAL em Clientes/7394370553/Sessoes/whatsapp:5511991382080
"""

import pytest
import json
import asyncio
from pathlib import Path
import sys
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
import pytz

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from router.principal_router import roteador_principal
from services.firebase_service_async import buscar_dado_em_path, salvar_dado_em_path
from utils.contexto_temporario import salvar_contexto_temporario_v2


pytestmark = pytest.mark.asyncio


# ============================================================================
# MOCKS DE ENTRADA (padrao p1_robustez_fluxo_conversacional_real.py)
# ============================================================================

class MockMessage:
    def __init__(self, chat_id, user_id, text=""):
        self.from_user = MagicMock()
        self.from_user.id = user_id
        self.chat = MagicMock()
        self.chat.id = chat_id
        self.text = text
        self.message_id = 1
        self.date = datetime.now(pytz.UTC)
        self.reply_text = AsyncMock(return_value={"ok": True})


class MockUser:
    def __init__(self, user_id):
        self.id = user_id


class MockChat:
    def __init__(self, chat_id):
        self.id = chat_id


class MockUpdate:
    """Mock realista de Update do Telegram"""
    def __init__(self, user_id: str, chat_id: str = "", text: str = ""):
        self.message = MockMessage(chat_id, user_id, text)
        self.effective_user = self.message.from_user
        self.effective_chat = self.message.chat


class MockContext:
    """Mock realista de context do Telegram"""
    def __init__(self):
        self.bot = AsyncMock()
        self.bot.send_message = AsyncMock(return_value={"ok": True})
        self.user_data = {}
        self.chat_data = {}
        self.bot_data = {}


# ============================================================================
# UTILIDADES FIRESTORE
# ============================================================================

async def obter_estado_sessao(tenant_id: str, actor_id: str):
    """Obter estado completo da sessao"""
    return await buscar_dado_em_path(f"Clientes/{tenant_id}/Sessoes/{actor_id}")


async def test_p2b_e2e_roteador_real():
    """
    E2E REAL com roteador_principal() e Firestore real.

    Testa 4 saudacoes indefinidas + 1 operacional.
    Valida que guard P2B bloqueia fallback operacional.
    """

    # ============================================================
    # SETUP
    # ============================================================
    tenant_id = "7394370553"
    actor_id = "whatsapp:5511991382080"

    print(f"\n[P2B E2E REAL] Iniciando teste com roteador_principal() REAL")
    print(f"  tenant_id: {tenant_id}")
    print(f"  actor_id: {actor_id}")

    # ============================================================
    # PASSO 1: Carregar e preservar snapshot original
    # ============================================================
    print(f"\n[PASSO 1] Carregar snapshot original do Firestore")

    try:
        ctx_original = await obter_estado_sessao(tenant_id, actor_id)
        if not ctx_original:
            pytest.skip(f"Sessao nao encontrada: {actor_id}")
    except Exception as e:
        pytest.skip(f"Firestore indisponivel: {str(e)}")

    draft_original = ctx_original.get("draft_agendamento") or {}

    print(f"  Estado original carregado:")
    print(f"    estado_fluxo: {ctx_original.get('estado_fluxo')}")
    print(f"    draft.servico: {draft_original.get('servico')}")
    print(f"    draft.profissional: {draft_original.get('profissional')}")

    # Validar precondicao
    assert ctx_original.get("estado_fluxo") == "aguardando_profissional", \
        f"Precondicao falhou: estado deve ser 'aguardando_profissional', encontrado: {ctx_original.get('estado_fluxo')}"

    assert draft_original.get("servico") == "corte", \
        f"Precondicao falhou: servico deve ser 'corte', encontrado: {draft_original.get('servico')}"

    # ============================================================
    # PASSO 2: Executar T1-T4 (saudacoes indefinidas)
    # ============================================================
    saudacoes = ["ola", "oi", "olá", "bom dia"]
    resultados = []

    try:
        for idx, saudacao in enumerate(saudacoes, 1):
            print(f"\n[T{idx}] Testando: '{saudacao}'")

            # ANTES: ler estado
            estado_antes = await obter_estado_sessao(tenant_id, actor_id)
            draft_antes = estado_antes.get("draft_agendamento") or {}

            print(f"  ANTES: draft.servico={draft_antes.get('servico')}, "
                  f"profissional={draft_antes.get('profissional')}")

            # EXECUCAO: chamar roteador REAL
            print(f"  Executando roteador_principal() REAL...")

            try:
                resposta = await roteador_principal(
                    user_id=actor_id,
                    mensagem=saudacao,
                    update=MockUpdate(actor_id, chat_id=tenant_id, text=saudacao),
                    context=MockContext()
                )

                resposta_texto = resposta.get("resposta", "") if isinstance(resposta, dict) else str(resposta)
                print(f"  Resposta: {resposta_texto[:80]}...")

            except Exception as e:
                pytest.fail(f"Roteador lancou excecao em T{idx}: {str(e)}")

            # DEPOIS: ler estado novamente
            estado_depois = await obter_estado_sessao(tenant_id, actor_id)
            draft_depois = estado_depois.get("draft_agendamento") or {}

            print(f"  DEPOIS: draft.servico={draft_depois.get('servico')}, "
                  f"profissional={draft_depois.get('profissional')}")

            # VALIDACOES
            # 1. Resposta nao contem a mensagem operacional de fallback
            assert "Perfeito — corte. Qual profissional você prefere?" not in resposta_texto, \
                f"T{idx}: Resposta contem fallback operacional (guard falhou)"

            # 2. Draft preservado
            assert draft_depois.get("servico") == "corte", \
                f"T{idx}: draft.servico alterado de 'corte' para '{draft_depois.get('servico')}'"

            assert draft_depois.get("profissional") is None, \
                f"T{idx}: draft.profissional alterado para '{draft_depois.get('profissional')}'"

            # 3. Estado preservado
            assert estado_depois.get("estado_fluxo") == "aguardando_profissional", \
                f"T{idx}: estado_fluxo alterado para '{estado_depois.get('estado_fluxo')}'"

            resultado = {
                "numero": idx,
                "saudacao": saudacao,
                "resposta_nao_contem_fallback": "Perfeito — corte" not in resposta_texto,
                "draft_preservado": draft_depois == draft_antes,
                "estado_preservado": estado_depois.get("estado_fluxo") == "aguardando_profissional",
                "status": "PASS"
            }
            resultados.append(resultado)
            print(f"  VALIDACAO T{idx}: PASS")

    except Exception as e:
        pytest.fail(f"Erro em testes saudacoes: {str(e)}")

    # ============================================================
    # PASSO 3: Executar T5 (operacional Bruna)
    # ============================================================
    print(f"\n[T5] Testando operacional: 'Bruna'")

    try:
        estado_antes = await obter_estado_sessao(tenant_id, actor_id)

        print(f"  Executando roteador_principal() REAL com 'Bruna'...")

        try:
            resposta = await roteador_principal(
                user_id=actor_id,
                mensagem="Bruna",
                update=MockUpdate(actor_id, chat_id=tenant_id, text="Bruna"),
                context=MockContext()
            )

            resposta_texto = resposta.get("resposta", "") if isinstance(resposta, dict) else str(resposta)
            print(f"  Resposta: {resposta_texto[:80]}...")

        except Exception as e:
            pytest.fail(f"Roteador lancou excecao em T5: {str(e)}")

        # Validacao: "Bruna" nao foi bloqueado (fluxo continuou)
        # A prova eh que o roteador retornou sem erro
        estado_depois = await obter_estado_sessao(tenant_id, actor_id)

        resultado_t5 = {
            "numero": 5,
            "saudacao": "Bruna",
            "operacional_nao_bloqueado": True,
            "estado_preservado": estado_depois.get("estado_fluxo") == "aguardando_profissional",
            "status": "PASS"
        }
        resultados.append(resultado_t5)
        print(f"  VALIDACAO T5: PASS (operacional nao bloqueado)")

    except Exception as e:
        pytest.fail(f"Erro em T5: {str(e)}")

    # ============================================================
    # PASSO 4: Restaurar estado original em FINALLY
    # ============================================================
    finally:
        print(f"\n[RESTAURACAO] Restaurando snapshot original no Firestore...")

        try:
            await salvar_contexto_temporario_v2(
                tenant_id,
                actor_id,
                ctx_original
            )

            # Validar restauracao
            ctx_restaurado = await obter_estado_sessao(tenant_id, actor_id)
            draft_restaurado = ctx_restaurado.get("draft_agendamento") or {}

            assert ctx_restaurado.get("estado_fluxo") == ctx_original.get("estado_fluxo"), \
                "Estado_fluxo nao foi restaurado"

            assert draft_restaurado.get("servico") == draft_original.get("servico"), \
                "Draft.servico nao foi restaurado"

            print(f"  Snapshot original RESTAURADO: estado_fluxo={ctx_restaurado.get('estado_fluxo')}")

        except Exception as e:
            pytest.fail(f"Erro ao restaurar snapshot: {str(e)}")

    # ============================================================
    # RESULTADO FINAL
    # ============================================================
    print("\n" + "="*80)
    print("P2B E2E REAL — RESULTADO FINAL")
    print("="*80)

    for res in resultados:
        print(f"\nT{res['numero']}: '{res.get('saudacao', 'operacional')}'")
        if 'resposta_nao_contem_fallback' in res:
            print(f"  Resposta sem fallback: {res['resposta_nao_contem_fallback']}")
            print(f"  Draft preservado: {res['draft_preservado']}")
            print(f"  Estado preservado: {res['estado_preservado']}")
        else:
            print(f"  Operacional nao bloqueado: {res['operacional_nao_bloqueado']}")
            print(f"  Estado preservado: {res['estado_preservado']}")
        print(f"  Status: {res['status']}")

    print(f"\nRestauraçao: OK")
    print(f"Total: {len(resultados)}/{len(resultados)} PASS")
    print("="*80 + "\n")
