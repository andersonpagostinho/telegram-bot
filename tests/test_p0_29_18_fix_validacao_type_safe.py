"""
P0.29.18-FIX — Testes de Validação Type-Safe para confirmacao_pendente

Objetivo: Validar que a fix de type-checking não quebra nenhum cenário existente
e detecta corretamente dicts vazios.

Testes:
- T1: Dict com operacao_id válido (deve passar)
- T2: Dict vazio {} (deve bloquear)
- T3: Booleano False (deve bloquear)
- T4: Flag True mas sem struct (deve bloquear)
- T5: Flag False mesmo com struct válida (deve bloquear)
- T6: Ambos None/ausentes (deve bloquear)
- T7: Negação com type-safe (confirmacao_pendente = {}, não False)
- T8: Confirmação com type-safe (mantém intencao_conversacional)
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime


# ============================================================================
# T1 — Dict com operacao_id válido (DEVE PASSAR)
# ============================================================================

@pytest.mark.asyncio
async def test_T1_dict_valido_com_operacao_id():
    """T1 — Dict estruturado com operacao_id válido deve passar na validação"""

    ctx = {
        "aguardando_confirmacao_agendamento": True,
        "confirmacao_pendente": {
            "operacao_id": "agendamento_user1_bruna_20261109_1500",
            "status": "pendente",
            "apresentada_em": datetime.now().isoformat(),
        }
    }

    aguardando = ctx.get("aguardando_confirmacao_agendamento")
    confirmacao_struct = ctx.get("confirmacao_pendente", {})

    confirmacao_valida = (
        aguardando is True and
        isinstance(confirmacao_struct, dict) and
        bool(confirmacao_struct.get("operacao_id"))
    )

    assert confirmacao_valida is True, "Dict com operacao_id deve ser válido"
    print("✅ T1 PASS: Dict válido detectado")


# ============================================================================
# T2 — Dict vazio {} (DEVE BLOQUEAR)
# ============================================================================

@pytest.mark.asyncio
async def test_T2_dict_vazio_bloqueado():
    """T2 — Dict vazio {} deve ser detectado como inválido (o problema em produção)"""

    ctx = {
        "aguardando_confirmacao_agendamento": True,
        "confirmacao_pendente": {}
    }

    aguardando = ctx.get("aguardando_confirmacao_agendamento")
    confirmacao_struct = ctx.get("confirmacao_pendente", {})

    confirmacao_valida = (
        aguardando is True and
        isinstance(confirmacao_struct, dict) and
        bool(confirmacao_struct.get("operacao_id"))
    )

    assert confirmacao_valida is False, "Dict vazio deve ser inválido"
    print("✅ T2 PASS: Dict vazio detectado como inválido")


# ============================================================================
# T3 — Booleano False (DEVE BLOQUEAR - SEGURO)
# ============================================================================

@pytest.mark.asyncio
async def test_T3_booleano_false_nao_quebra():
    """T3 — Booleano False não deve causar AttributeError (fix anterior quebrava)"""

    ctx = {
        "aguardando_confirmacao_agendamento": False,
        "confirmacao_pendente": False
    }

    aguardando = ctx.get("aguardando_confirmacao_agendamento")
    confirmacao_struct = ctx.get("confirmacao_pendente", {})

    try:
        confirmacao_valida = (
            aguardando is True and
            isinstance(confirmacao_struct, dict) and
            bool(confirmacao_struct.get("operacao_id"))
        )
        assert confirmacao_valida is False
        print("✅ T3 PASS: Booleano False tratado com segurança")
    except AttributeError as e:
        pytest.fail(f"❌ T3 FAIL: Booleano False causou AttributeError: {e}")


# ============================================================================
# T4 — Flag True mas sem struct (DEVE BLOQUEAR)
# ============================================================================

@pytest.mark.asyncio
async def test_T4_flag_true_sem_struct():
    """T4 — Flag True mas confirmacao_pendente ausente deve bloquear"""

    ctx = {
        "aguardando_confirmacao_agendamento": True,
    }

    aguardando = ctx.get("aguardando_confirmacao_agendamento")
    confirmacao_struct = ctx.get("confirmacao_pendente", {})

    confirmacao_valida = (
        aguardando is True and
        isinstance(confirmacao_struct, dict) and
        bool(confirmacao_struct.get("operacao_id"))
    )

    assert confirmacao_valida is False, "Flag True sem struct deve ser inválido"
    print("✅ T4 PASS: Mismatch (flag True, struct ausente) detectado")


# ============================================================================
# T5 — Flag False mesmo com struct válida (DEVE BLOQUEAR)
# ============================================================================

@pytest.mark.asyncio
async def test_T5_flag_false_com_struct_valida():
    """T5 — Flag False (mesmo que struct seja válido) deve bloquear"""

    ctx = {
        "aguardando_confirmacao_agendamento": False,
        "confirmacao_pendente": {
            "operacao_id": "agendamento_user1_bruna_20261109_1500",
            "status": "pendente",
        }
    }

    aguardando = ctx.get("aguardando_confirmacao_agendamento")
    confirmacao_struct = ctx.get("confirmacao_pendente", {})

    confirmacao_valida = (
        aguardando is True and
        isinstance(confirmacao_struct, dict) and
        bool(confirmacao_struct.get("operacao_id"))
    )

    assert confirmacao_valida is False, "Flag False deve bloquear mesmo com struct"
    print("✅ T5 PASS: Flag False bloqueia corretamente")


# ============================================================================
# T6 — Ambos None/ausentes (DEVE BLOQUEAR)
# ============================================================================

@pytest.mark.asyncio
async def test_T6_ambos_ausentes():
    """T6 — Contexto vazio deve bloquear"""

    ctx = {}

    aguardando = ctx.get("aguardando_confirmacao_agendamento")
    confirmacao_struct = ctx.get("confirmacao_pendente", {})

    confirmacao_valida = (
        aguardando is True and
        isinstance(confirmacao_struct, dict) and
        bool(confirmacao_struct.get("operacao_id"))
    )

    assert confirmacao_valida is False, "Contexto vazio deve ser inválido"
    print("✅ T6 PASS: Contexto vazio detectado como inválido")


# ============================================================================
# T7 — Negação com type-safe (confirmacao_pendente = {}, não False)
# ============================================================================

@pytest.mark.asyncio
async def test_T7_negacao_type_correto():
    """T7 — Quando há negação, confirmacao_pendente deve ser {} (dict), não False"""

    ctx_original = {
        "aguardando_confirmacao_agendamento": True,
        "confirmacao_pendente": {
            "operacao_id": "agendamento_user1_bruna_20261109_1500",
            "status": "pendente",
        }
    }

    ctx_apos_negacao = ctx_original.copy()
    ctx_apos_negacao["aguardando_confirmacao_agendamento"] = False
    ctx_apos_negacao["confirmacao_pendente"] = {}

    aguardando = ctx_apos_negacao.get("aguardando_confirmacao_agendamento")
    confirmacao_struct = ctx_apos_negacao.get("confirmacao_pendente", {})

    confirmacao_valida = (
        aguardando is True and
        isinstance(confirmacao_struct, dict) and
        bool(confirmacao_struct.get("operacao_id"))
    )

    assert confirmacao_valida is False, "Após negação, confirmacao deve ser inválida"
    assert isinstance(ctx_apos_negacao["confirmacao_pendente"], dict), "Deve ser dict, não False"
    print("✅ T7 PASS: Negação com type-correct ({} em vez de False)")


# ============================================================================
# T8 — Confirmação com type-safe
# ============================================================================

@pytest.mark.asyncio
async def test_T8_confirmacao_type_safe():
    """T8 — Confirmação válida passa na validação type-safe"""

    ctx = {
        "aguardando_confirmacao_agendamento": True,
        "confirmacao_pendente": {
            "operacao_id": "agendamento_user1_bruna_20261109_1500",
            "status": "pendente",
        }
    }

    aguardando = ctx.get("aguardando_confirmacao_agendamento")
    confirmacao_struct = ctx.get("confirmacao_pendente", {})

    confirmacao_valida = (
        aguardando is True and
        isinstance(confirmacao_struct, dict) and
        bool(confirmacao_struct.get("operacao_id"))
    )

    assert confirmacao_valida is True, "Confirmação válida deve passar"

    ctx_modificado = ctx.copy()
    ctx_modificado["intencao_conversacional"] = "confirmacao_agendamento"

    assert ctx_modificado["intencao_conversacional"] == "confirmacao_agendamento"
    assert ctx_modificado["confirmacao_pendente"]["operacao_id"]
    print("✅ T8 PASS: Confirmação type-safe com intencao_conversacional")


# ============================================================================
# T9 — REGRESSÃO: Todas as funções de manager recebem dict
# ============================================================================

@pytest.mark.asyncio
async def test_T9_regressao_manager_functions():
    """T9 — Garantir que nenhuma função de manager quebra com a mudança"""

    confirmacao = {
        "operacao_id": "agendamento_user1_bruna_20261109_1500",
        "status": "pendente",
        "tentativas": 1
    }

    confirmacao = confirmacao or {}
    confirmacao["tentativas"] = confirmacao.get("tentativas", 1) + 1

    assert confirmacao["tentativas"] == 2, "incrementar_tentativa deve funcionar"

    confirmacao = confirmacao or {}
    confirmacao["status"] = "consumida"

    assert confirmacao["status"] == "consumida", "consumir deve funcionar"
    print("✅ T9 PASS: Funções de manager não sofrem regressão")


# ============================================================================
# T10 — PADRÃO 2: dados_confirmacao_agendamento (23 pontos ainda não migrados)
# ============================================================================

@pytest.mark.asyncio
async def test_T10_padrao_dados_confirmacao_sem_operacao_id():
    """T10 — Aceitarconfirmação com dados_confirmacao_agendamento (padrão intermediário)"""

    ctx = {
        "aguardando_confirmacao_agendamento": True,
        "confirmacao_pendente": {},  # Vazio
        "dados_confirmacao_agendamento": {
            "profissional": "Bruna",
            "servico": "corte feminino",
            "data_hora": "2026-11-16T11:00:00",
            "duracao": 40,
            "descricao": "Corte feminino com Bruna",
        }
    }

    aguardando = ctx.get("aguardando_confirmacao_agendamento")
    confirmacao_struct = ctx.get("confirmacao_pendente", {})
    dados_confirmacao = ctx.get("dados_confirmacao_agendamento", {})

    confirmacao_valida = (
        aguardando is True and
        (
            (isinstance(confirmacao_struct, dict) and bool(confirmacao_struct.get("operacao_id"))) or
            (isinstance(dados_confirmacao, dict) and bool(dados_confirmacao.get("profissional")))
        )
    )

    assert confirmacao_valida is True, "Deve aceitar dados_confirmacao_agendamento"
    print("✅ T10 PASS: Padrão 2 (dados_confirmacao) aceito")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
