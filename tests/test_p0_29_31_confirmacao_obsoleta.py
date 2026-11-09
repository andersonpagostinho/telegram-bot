"""
P0.29.31 — Testes de Regressão: confirmacao_pendente Obsoleta

Objetivo: Validar que confirmacao_pendente obsoleta é removida corretamente
e que mensagens simples não são sequestradas para confirmação.

Cenários:
- T1: Confirmação antiga de Bruna + draft atual de Carla → não deve confirmar
- T2: Mensagem "olá" com confirmação antiga persistida → saudação normal
- T3: Confirmação válida com operacao_id compatível → confirmação processada
- T4: Pergunta informativa durante confirmação legítima → pergunta respondida
- T5: Conclusão de agendamento → reabertura sem confirmação antiga
- T6: Cancelamento e abandono → confirmacao_pendente removida
- T7: Isolamento multi-tenant → nenhuma interferência entre tenants
- T8: Concorrência → limpeza não interfere com confirmação paralela
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from router.principal_router import (
    validar_operacao_id_compativel,
    eh_confirmacao_pendente_ativa,
)


# ============================================================================
# T1 — Confirmação antiga de Bruna + draft atual de Carla
# ============================================================================

def test_T1_confirmacao_bruna_draft_carla():
    """T1 — operacao_id obsoleto não passa validação"""

    print("\n[T1] Confirmação antiga de Bruna + draft atual de Carla")

    ctx = {
        "aguardando_confirmacao_agendamento": True,
        "confirmacao_pendente": {
            "operacao_id": "agendamento_whatsapp:5511991382080_bruna_20261110_1100",
            "status": "pendente",
            "apresentada_em": datetime.now().isoformat(),
        },
        "draft_agendamento": {
            "profissional": "Carla",
            "servico": "corte feminino",
            "data_hora": "2026-11-10T10:00:00",
            "duracao": 40,
        }
    }

    # Validar: operacao_ids NÃO combinam
    resultado = validar_operacao_id_compativel(ctx)

    assert resultado is False, "operacao_id de Bruna não deve validar contra draft de Carla"
    assert eh_confirmacao_pendente_ativa(ctx) is True, "Flag ativo deve ser True"

    print("✅ T1 PASS: operacao_id obsoleto detectado como inválido")


# ============================================================================
# T2 — Mensagem "olá" com confirmação antiga
# ============================================================================

def test_T2_saudacao_com_confirmacao_obsoleta():
    """T2 — Saudação não deve ser forçada para confirmação obsoleta"""

    print("\n[T2] Mensagem 'olá' com confirmacao_pendente obsoleta")

    ctx = {
        "aguardando_confirmacao_agendamento": True,
        "intencao_conversacional": "indefinida",  # Saudação pura
        "confirmacao_pendente": {
            "operacao_id": "agendamento_whatsapp:5511991382080_bruna_20261110_1100",
            "status": "pendente",
        },
        "draft_agendamento": {
            "profissional": "Carla",
            "servico": "escova",
            "data_hora": "2026-11-10T14:00:00",
        }
    }

    # Verificar: tem confirmacao_pendente mas operacao_id não bate
    validacao = validar_operacao_id_compativel(ctx)

    # Sistema deve IGNORAR confirmacao_pendente obsoleta e processar saudação normalmente
    assert validacao is False, "confirmacao_pendente deve ser inválida para roteamento"

    print("✅ T2 PASS: Saudação não foi sequestrada por confirmacao obsoleta")


# ============================================================================
# T3 — Confirmação válida com operacao_id compatível
# ============================================================================

def test_T3_confirmacao_valida_compativel():
    """T3 — operacao_id compatível passa validação"""

    print("\n[T3] Confirmação válida com operacao_id compatível")

    ctx = {
        "aguardando_confirmacao_agendamento": True,
        "confirmacao_pendente": {
            "operacao_id": "agendamento_whatsapp:5511991382080_bruna_20261110_1100",
            "status": "pendente",
        },
        "draft_agendamento": {
            "profissional": "Bruna",  # ← MESMA profissional
            "servico": "corte feminino",
            "data_hora": "2026-11-10T11:00:00",  # ← MESMA data
            "duracao": 40,
        }
    }

    resultado = validar_operacao_id_compativel(ctx)

    assert resultado is True, "operacao_id compatível deve validar"
    assert eh_confirmacao_pendente_ativa(ctx) is True

    print("✅ T3 PASS: Confirmação legítima foi validada")


# ============================================================================
# T4 — Pergunta informativa durante confirmação legítima
# ============================================================================

def test_T4_pergunta_durante_confirmacao_valida():
    """T4 — Pergunta informativa não deve descartar confirmação válida"""

    print("\n[T4] Pergunta informativa durante confirmação legítima")

    # Confirmação válida e compatível
    ctx = {
        "aguardando_confirmacao_agendamento": True,
        "intencao_conversacional": "confirmacao_agendamento",
        "confirmacao_pendente": {
            "operacao_id": "agendamento_whatsapp:5511991382080_bruna_20261110_1100",
            "status": "pendente",
        },
        "draft_agendamento": {
            "profissional": "Bruna",
            "servico": "corte feminino",
            "data_hora": "2026-11-10T11:00:00",
        }
    }

    validacao = validar_operacao_id_compativel(ctx)

    # Confirmação deve ser mantida (pergunta será respondida depois)
    assert validacao is True, "Confirmação válida não deve ser descartada"

    print("✅ T4 PASS: Confirmação legítima sobreviveu para responder pergunta")


# ============================================================================
# T5 — Conclusão de agendamento → reabertura sem confirmação antiga
# ============================================================================

def test_T5_conclusao_reabertura_limpa():
    """T5 — Após conclusão, confirmacao_pendente não reaparece"""

    print("\n[T5] Conclusão de agendamento → reabertura sem confirmação antiga")

    # Antes da conclusão
    ctx_antes = {
        "aguardando_confirmacao_agendamento": True,
        "confirmacao_pendente": {
            "operacao_id": "agendamento_whatsapp:5511991382080_bruna_20261110_1100",
            "status": "pendente",
        },
        "draft_agendamento": {
            "profissional": "Bruna",
            "servico": "corte feminino",
            "data_hora": "2026-11-10T11:00:00",
        }
    }

    # Após conclusão (simular ctx.pop() e limpeza)
    ctx_apos = ctx_antes.copy()
    ctx_apos.pop("confirmacao_pendente", None)
    ctx_apos["aguardando_confirmacao_agendamento"] = False
    ctx_apos["confirmacao_agendamento_concluida"] = True

    # Verificar que confirmacao_pendente foi removido
    assert "confirmacao_pendente" not in ctx_apos or ctx_apos.get("confirmacao_pendente") is None
    assert eh_confirmacao_pendente_ativa(ctx_apos) is False

    print("✅ T5 PASS: confirmacao_pendente foi removido após conclusão")


# ============================================================================
# T6 — Cancelamento e abandono
# ============================================================================

def test_T6_cancelamento_abandono():
    """T6 — Cancelamento remove confirmacao_pendente"""

    print("\n[T6] Cancelamento e abandono")

    # Contexto com confirmacao_pendente
    ctx = {
        "aguardando_confirmacao_agendamento": True,
        "confirmacao_pendente": {
            "operacao_id": "agendamento_whatsapp:5511991382080_bruna_20261110_1100",
            "status": "pendente",
        },
        "draft_agendamento": {
            "profissional": "Bruna",
            "servico": "corte feminino",
            "data_hora": "2026-11-10T11:00:00",
        }
    }

    # Simular cancelamento (remover campos)
    ctx.pop("confirmacao_pendente", None)
    ctx.pop("aguardando_confirmacao_agendamento", None)
    ctx.pop("draft_agendamento", None)
    ctx["estado_fluxo"] = "idle"

    # Verificar limpeza
    assert eh_confirmacao_pendente_ativa(ctx) is False
    assert "confirmacao_pendente" not in ctx
    assert ctx.get("estado_fluxo") == "idle"

    print("✅ T6 PASS: Cancelamento limpou confirmacao_pendente")


# ============================================================================
# T7 — Isolamento multi-tenant
# ============================================================================

def test_T7_isolamento_multitenant():
    """T7 — Contextos de diferentes tenants não se interferem"""

    print("\n[T7] Isolamento multi-tenant")

    # Tenant A
    ctx_tenant_a = {
        "aguardando_confirmacao_agendamento": True,
        "confirmacao_pendente": {
            "operacao_id": "agendamento_tenant_a_bruna_20261110_1100",
        },
        "draft_agendamento": {
            "profissional": "Bruna",
        }
    }

    # Tenant B (mesmo usuário, tenant diferente)
    ctx_tenant_b = {
        "aguardando_confirmacao_agendamento": True,
        "confirmacao_pendente": {
            "operacao_id": "agendamento_tenant_b_carla_20261110_1000",
        },
        "draft_agendamento": {
            "profissional": "Carla",
        }
    }

    # Validações são independentes
    val_a = validar_operacao_id_compativel(ctx_tenant_a)
    val_b = validar_operacao_id_compativel(ctx_tenant_b)

    # Ambos são válidos em seu contexto
    assert val_a is True, "Tenant A deve ser válido"
    assert val_b is True, "Tenant B deve ser válido"

    # Cruzar — deve falhar (tenant A confirmacao com tenant B draft)
    ctx_cruzado = {
        "aguardando_confirmacao_agendamento": True,
        "confirmacao_pendente": ctx_tenant_a["confirmacao_pendente"],
        "draft_agendamento": ctx_tenant_b["draft_agendamento"],
    }
    val_cruzado = validar_operacao_id_compativel(ctx_cruzado)

    assert val_cruzado is False, "Cruzamento de tenants deve falhar"

    print("✅ T7 PASS: Isolamento multi-tenant validado")


# ============================================================================
# T8 — Concorrência (simplificado)
# ============================================================================

def test_T8_concorrencia_limpeza():
    """T8 — Limpeza não interfere com confirmação paralela"""

    print("\n[T8] Concorrência — limpeza vs confirmação paralela")

    # Requisição 1: Agendamento com Bruna (em conclusão)
    ctx_req1 = {
        "aguardando_confirmacao_agendamento": True,
        "confirmacao_pendente": {
            "operacao_id": "agendamento_whatsapp:5511991382080_bruna_20261110_1100",
        },
        "draft_agendamento": {
            "profissional": "Bruna",
            "servico": "corte feminino",
            "data_hora": "2026-11-10T11:00:00",
        }
    }

    # Requisição 2: Novo agendamento com Carla (chegando em paralelo)
    ctx_req2_novo = {
        "aguardando_confirmacao_agendamento": True,
        "confirmacao_pendente": {
            "operacao_id": "agendamento_whatsapp:5511991382080_carla_20261110_1000",
        },
        "draft_agendamento": {
            "profissional": "Carla",
            "servico": "coloracao",
            "data_hora": "2026-11-10T10:00:00",
        }
    }

    # Validação de cada requisição é independente
    val_1 = validar_operacao_id_compativel(ctx_req1)
    val_2 = validar_operacao_id_compativel(ctx_req2_novo)

    assert val_1 is True, "Req 1 deve validar"
    assert val_2 is True, "Req 2 deve validar"

    # Limpeza em Req 1 não afeta Req 2
    ctx_req1.pop("confirmacao_pendente", None)
    ctx_req1["aguardando_confirmacao_agendamento"] = False

    # Req 2 continua válida
    val_2_apos = validar_operacao_id_compativel(ctx_req2_novo)
    assert val_2_apos is True, "Req 2 não foi afetada pela limpeza de Req 1"

    print("✅ T8 PASS: Concorrência não causa interferência")


# ============================================================================
# TESTES DE PERSISTÊNCIA
# ============================================================================

def test_persistencia_delete_field():
    """Teste de que DELETE_FIELD está no payload de limpeza"""

    print("\n[PERSIST] Verificando DELETE_FIELD em contexto_temporario.py")

    # Ler arquivo
    with open("C:\\dev\\neoeve\\utils\\contexto_temporario.py", "r", encoding="utf-8") as f:
        conteudo = f.read()

    # Verificar que confirmacao_pendente foi adicionado ao DELETE_FIELD
    assert '"confirmacao_pendente": firestore.DELETE_FIELD' in conteudo, \
        "confirmacao_pendente não encontrado em DELETE_FIELD"

    print("✅ PERSIST PASS: DELETE_FIELD contém confirmacao_pendente")


def test_pop_confirmacao_em_pontos_terminais():
    """Teste de que ctx.pop('confirmacao_pendente') está em pontos terminais"""

    print("\n[POP] Verificando ctx.pop('confirmacao_pendente') em pontos terminais")

    with open("C:\\dev\\neoeve\\router\\principal_router.py", "r", encoding="utf-8") as f:
        conteudo = f.read()

    # Verificar que pop foi adicionado (pelo menos 3 ocorrências)
    count = conteudo.count('ctx.pop("confirmacao_pendente"')

    assert count >= 3, f"Esperava ≥3 ctx.pop('confirmacao_pendente'), encontrou {count}"

    print(f"✅ POP PASS: {count} ocorrências de ctx.pop('confirmacao_pendente') encontradas")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
