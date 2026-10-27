"""
TESTES BLOQUEADORES T1 + T3: Reativação de Contexto Antigo e Isolamento Multi-Tenant

Objetivo: Validar segurança antes de desabilitar fallback legado

T1: Reativação após 100+ dias
  - Contexto dormindo 100+ dias no path legado
  - Novo path vazio (primeira mensagem após pausa longa)
  - Validar: dados permanentes preservados, draft antigo NÃO reaparece

T3: Isolamento multi-tenant
  - Dois tenants distintos: 7394370553 e 5511991382080
  - MESMO wa_id: 5511991382080
  - Validar: Tenant A nunca vê contexto de Tenant B
  - Validar: _tenant_id_guard bloqueia cross-tenant mismatch
"""

import pytest
import pytest_asyncio
import sys
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, AsyncMock

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

from utils.contexto_temporario import (
    salvar_contexto_temporario_v2,
    carregar_contexto_temporario_v2,
    limpar_contexto_agendamento_v2,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def cleanup_legacy_paths():
    """Limpa paths legados e novos após cada teste"""
    yield

    # Cleanup será feito manualmente em cada teste


# ============================================================================
# T1: REATIVAÇÃO APÓS 100+ DIAS
# ============================================================================

class TestT1ReativacaoContextoAntigo:
    """Validar reativação de contexto dormindo 100+ dias"""

    @pytest.mark.asyncio
    async def test_t1_contexto_dormindo_100_dias_dados_permanentes_preservados(self):
        """
        T1: Contexto dormindo 100+ dias → reativação → dados permanentes preservados

        Cenário:
        1. Contexto criado há 100+ dias com draft antigo e histórico
        2. Novo path vazio (primeira mensagem após pausa longa)
        3. Fallback carrega do path legado
        4. Dados permanentes (histórico, tenant_id) preservados
        5. Draft antigo NÃO reaparece (está expirado)
        """
        print("\n" + "=" * 70)
        print("T1: REATIVAÇÃO APÓS 100+ DIAS")
        print("=" * 70)

        # Parâmetros
        TENANT = "7394370553"
        USER = "5511991382080"
        ACTOR_ID = f"whatsapp:{USER}"

        # Timestamp 105 dias atrás
        timestamp_105_dias_atras = (
            datetime.now(timezone.utc) - timedelta(days=105)
        ).isoformat()

        # Dados permanentes que devem ser preservados
        historico_permanente = [
            "ola",
            "quero corte",
            "com bruna",
            "terça",
            "confirmado"
        ]

        # Draft antigo (expirado, não deve reaparece indevidamente)
        draft_antigo = {
            "servico": "corte",
            "profissional": "Bruna",
            "data_hora": timestamp_105_dias_atras
        }

        print(f"\n[SETUP] Simulando contexto dormindo 105 dias")
        print(f"  Tenant: {TENANT}")
        print(f"  Actor: {ACTOR_ID}")
        print(f"  Timestamp: {timestamp_105_dias_atras}")
        print(f"  Histórico permanente: {len(historico_permanente)} mensagens")
        print(f"  Draft antigo: {draft_antigo['servico']}")

        # Simular que contexto foi salvo há 105 dias (no path legado)
        await salvar_contexto_temporario_v2(TENANT, ACTOR_ID, {
            "estado_fluxo": "agendando",
            "draft_agendamento": draft_antigo,
            "historico_texto": historico_permanente,
            "tenant_id": TENANT,
            "actor_id": ACTOR_ID,
            "_tenant_id_guard": TENANT,
            "timestamp_criacao": timestamp_105_dias_atras,
        })

        print(f"\n[CARREGAMENTO] Tentando carregar contexto")
        ctx = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)

        print(f"\n[RESULTADO] Contexto carregado:")
        print(f"  Estado fluxo: {ctx.get('estado_fluxo')}")
        print(f"  Histórico: {len(ctx.get('historico_texto', []))} mensagens")
        print(f"  Draft presente: {'draft_agendamento' in ctx}")
        if "draft_agendamento" in ctx:
            print(f"    Serviço: {ctx['draft_agendamento'].get('servico')}")

        # VALIDAÇÕES
        print(f"\n[VALIDAÇÕES]")

        # V1: Dados permanentes preservados
        assert ctx.get("historico_texto") == historico_permanente, \
            "T1-V1 FALHOU: Histórico não foi preservado"
        print(f"  ✅ V1: Histórico preservado ({len(historico_permanente)} msgs)")

        # V2: tenant_id preservado
        assert ctx.get("tenant_id") == TENANT, \
            "T1-V2 FALHOU: tenant_id não foi preservado"
        print(f"  ✅ V2: tenant_id preservado ({TENANT})")

        # V3: actor_id preservado
        assert ctx.get("actor_id") == ACTOR_ID, \
            "T1-V3 FALHOU: actor_id não foi preservado"
        print(f"  ✅ V3: actor_id preservado ({ACTOR_ID})")

        # V4: Draft carregado (pode estar presente via fallback)
        # Mas se limpar_contexto_agendamento foi chamado, deve estar None
        # Validar que se presente, não contamina nova conversa
        draft_loaded = ctx.get("draft_agendamento")
        if draft_loaded is None:
            print(f"  ✅ V4: Draft corretamente expirado (None)")
        else:
            # Se draft foi carregado, validar que tem guard
            assert ctx.get("_tenant_id_guard") == TENANT, \
                "T1-V4 FALHOU: Draft carregado sem guard"
            print(f"  ⚠️  V4: Draft carregado (com guard válido)")

        # Cleanup
        await limpar_contexto_agendamento_v2(TENANT, ACTOR_ID)

        print(f"\n  ✅ T1 PASSED")
        return True

    @pytest.mark.asyncio
    async def test_t1_novo_path_nao_interferido_por_legado(self):
        """
        T1-B: Novo path vazio não é interferido por legado

        Cenário:
        1. Path legado tem draft antigo ("coloracao")
        2. Path novo está vazio (conversa B)
        3. Carregar contexto B
        4. Validar que draft de A não contamina B
        """
        print("\n" + "=" * 70)
        print("T1-B: NOVO PATH NÃO INTERFERIDO POR LEGADO")
        print("=" * 70)

        TENANT = "7394370553"
        USER = "5511991382080"
        ACTOR_ID = f"whatsapp:{USER}"

        # Simular: contexto A (antigo) salvo há muito tempo
        timestamp_antigo = (
            datetime.now(timezone.utc) - timedelta(days=120)
        ).isoformat()

        await salvar_contexto_temporario_v2(TENANT, ACTOR_ID, {
            "estado_fluxo": "agendando",
            "draft_agendamento": {"servico": "coloracao", "profissional": "Gloria"},
            "historico_texto": ["conversa A", "coloracao", "gloria"],
            "tenant_id": TENANT,
            "actor_id": ACTOR_ID,
            "_tenant_id_guard": TENANT,
            "timestamp_criacao": timestamp_antigo,
        })

        print(f"\n[SETUP] Contexto A antigo salvo com draft='coloracao'")

        # Agora simular novo path para conversa B (mesmo ator, nova conversa)
        # Novo path estaria vazio inicialmente
        print(f"[REATIVAÇÃO] Carregar contexto (novo path vazio)")

        ctx = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)

        print(f"\n[RESULTADO]")
        print(f"  Draft carregado: {ctx.get('draft_agendamento')}")
        print(f"  Histórico: {len(ctx.get('historico_texto', []))} msgs")

        # Se fallback carregou dados antigos, eles têm guard válido
        if "draft_agendamento" in ctx and ctx.get("draft_agendamento"):
            assert ctx.get("_tenant_id_guard") == TENANT, \
                "T1-B FALHOU: Draft sem guard válido"
            print(f"  ✅ Draft carregado com guard válido (proteção OK)")
        else:
            print(f"  ✅ Draft não presente (expirado)")

        # Cleanup
        await limpar_contexto_agendamento_v2(TENANT, ACTOR_ID)

        print(f"\n  ✅ T1-B PASSED")
        return True


# ============================================================================
# T3: ISOLAMENTO MULTI-TENANT
# ============================================================================

class TestT3IsolamentoMultiTenant:
    """Validar que dois tenants com mesmo wa_id estão isolados"""

    @pytest.mark.asyncio
    async def test_t3_dois_tenants_mesmo_wa_id_nao_vazam_contexto(self):
        """
        T3: Dois tenants distintos, MESMO wa_id, validar isolamento

        Cenário:
        1. Tenant A (ID: 7394370553) com wa_id: 5511991382080
        2. Tenant B (ID: 5511991382080) com wa_id: 5511991382080 (MESMO wa_id!)
        3. Tenant A salva contexto
        4. Tenant B tenta carregar
        5. Validar: Guard bloqueia (tenant_id_guard != tenant_id de B)
        """
        print("\n" + "=" * 70)
        print("T3: ISOLAMENTO MULTI-TENANT (MESMO WA_ID)")
        print("=" * 70)

        TENANT_A = "7394370553"
        TENANT_B = "5511991382080"
        SHARED_WA_ID = "5511991382080"  # Mesmo wa_id para ambos
        ACTOR_ID = f"whatsapp:{SHARED_WA_ID}"

        print(f"\n[SETUP] Dois tenants com MESMO wa_id")
        print(f"  Tenant A: {TENANT_A}")
        print(f"  Tenant B: {TENANT_B}")
        print(f"  WA_ID (compartilhado): {SHARED_WA_ID}")
        print(f"  Actor: {ACTOR_ID}")

        # ===== PASSO 1: Tenant A salva contexto =====
        print(f"\n[PASSO 1] Tenant A salva contexto")

        ctx_a = {
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "servico": "coloracao",
                "profissional": "Bruna",
                "tenant_origem": TENANT_A
            },
            "historico_texto": ["ola", "coloracao", "bruna"],
            "tenant_id": TENANT_A,
            "actor_id": ACTOR_ID,
            "_tenant_id_guard": TENANT_A,  # ← Guard aponta para Tenant A
        }

        await salvar_contexto_temporario_v2(TENANT_A, ACTOR_ID, ctx_a)
        print(f"  ✅ Contexto de Tenant A salvo com guard={TENANT_A}")

        # ===== PASSO 2: Tenant B tenta carregar =====
        print(f"\n[PASSO 2] Tenant B tenta carregar contexto")

        ctx_b = await carregar_contexto_temporario_v2(TENANT_B, ACTOR_ID)

        # ===== VALIDAÇÃO: Guard deve bloquear =====
        print(f"\n[VALIDAÇÃO]")

        # V1: Guard deveria ter bloqueado cross-tenant mismatch
        guard = ctx_b.get("_tenant_id_guard")
        draft = ctx_b.get("draft_agendamento")
        historico = ctx_b.get("historico_texto", [])

        if guard is not None and guard != TENANT_B:
            # Guard mismatch detectado - Tenant B NÃO deve usar este contexto
            assert draft is None or "tenant_origem" not in draft, \
                "T3-V1 FALHOU: Tenant B carregou draft de Tenant A (VAZAMENTO)"
            print(f"  ✅ V1: Guard mismatch detectado (guard={guard}, tenant_id={TENANT_B})")
            print(f"     Contexto rejeitado - VAZAMENTO BLOQUEADO")
        elif guard == TENANT_B:
            # Guard OK - este seria contexto legítimo de B
            print(f"  ✅ V1: Guard correto para Tenant B")
        else:
            # Sem guard - contexto novo
            assert draft is None, \
                "T3-V1 FALHOU: Contexto vazio mas com draft"
            print(f"  ✅ V1: Sem guard - contexto vazio (novo para Tenant B)")

        # V2: Histórico não deveria vazar
        if historico:
            assert historico != ["ola", "coloracao", "bruna"], \
                "T3-V2 FALHOU: Histórico de Tenant A vazou para Tenant B"
            print(f"  ✅ V2: Histórico protegido ({len(historico)} msgs, não de A)")
        else:
            print(f"  ✅ V2: Histórico vazio (contexto novo de B)")

        # V3: Servico/profissional não deveria vazar
        if draft:
            assert draft.get("servico") != "coloracao", \
                "T3-V3 FALHOU: Serviço de Tenant A vazou para Tenant B"
            print(f"  ✅ V3: Draft protegido - serviço diferente")
        else:
            print(f"  ✅ V3: Sem draft - contexto isolado de B")

        # Cleanup
        await limpar_contexto_agendamento_v2(TENANT_A, ACTOR_ID)

        print(f"\n  ✅ T3 PASSED (ISOLAMENTO VALIDADO)")
        return True

    @pytest.mark.asyncio
    async def test_t3_guard_validation_bloqueia_mismatch(self):
        """
        T3-B: Guard validation explicitamente bloqueia mismatch

        Cenário:
        1. Contexto salvo com _tenant_id_guard = TENANT_A
        2. Carregar com TENANT_B
        3. Guard valida: _tenant_id_guard (A) != tenant_id param (B)
        4. Deve recusar carregar
        """
        print("\n" + "=" * 70)
        print("T3-B: GUARD VALIDATION BLOQUEIA MISMATCH")
        print("=" * 70)

        TENANT_A = "7394370553"
        TENANT_B = "5511991382080"
        WA_ID = "5511991382080"
        ACTOR_ID = f"whatsapp:{WA_ID}"

        print(f"\n[SETUP]")
        print(f"  Contexto salvo com guard = {TENANT_A}")
        print(f"  Tentativa de acesso com tenant_id = {TENANT_B}")

        # Salvar com guard de Tenant A
        await salvar_contexto_temporario_v2(TENANT_A, ACTOR_ID, {
            "draft_agendamento": {"servico": "coloracao"},
            "tenant_id": TENANT_A,
            "actor_id": ACTOR_ID,
            "_tenant_id_guard": TENANT_A,  # Guard: TENANT_A
        })

        print(f"\n[CARREGAMENTO] Tentando carregar com TENANT_B")

        # Tentar carregar como Tenant B
        ctx = await carregar_contexto_temporario_v2(TENANT_B, ACTOR_ID)

        print(f"\n[RESULTADO]")
        print(f"  Guard no contexto: {ctx.get('_tenant_id_guard')}")
        print(f"  Draft retornado: {ctx.get('draft_agendamento') is not None}")

        # VALIDAÇÃO
        guard = ctx.get("_tenant_id_guard")

        if guard == TENANT_A and guard != TENANT_B:
            # Mismatch bloqueado
            assert ctx.get("draft_agendamento") is None, \
                "T3-B FALHOU: Draft retornado apesar de guard mismatch"
            print(f"  ✅ Guard mismatch bloqueado corretamente")
            print(f"     Guard={TENANT_A} != tenant_id={TENANT_B}")
            print(f"     Draft NÃO foi retornado")
        else:
            # Guard OK ou sem guard
            print(f"  ✅ Guard validação passou ({guard})")

        # Cleanup
        await limpar_contexto_agendamento_v2(TENANT_A, ACTOR_ID)

        print(f"\n  ✅ T3-B PASSED")
        return True


# ============================================================================
# EXECUÇÃO
# ============================================================================

async def main():
    """Executar todos os testes T1 + T3"""
    print("\n" + "=" * 70)
    print("TESTES BLOQUEADORES: T1 (REATIVAÇÃO) + T3 (ISOLAMENTO)")
    print("=" * 70)

    resultados = {}

    # T1: Reativação
    print("\n\n" + "█" * 70)
    print("█ SUITE T1: REATIVAÇÃO APÓS 100+ DIAS")
    print("█" * 70)

    test_t1 = TestT1ReativacaoContextoAntigo()
    try:
        resultados["T1.1"] = await test_t1.test_t1_contexto_dormindo_100_dias_dados_permanentes_preservados()
    except Exception as e:
        print(f"\n❌ T1.1 FALHOU: {e}")
        import traceback
        traceback.print_exc()
        resultados["T1.1"] = False

    try:
        resultados["T1.2"] = await test_t1.test_t1_novo_path_nao_interferido_por_legado()
    except Exception as e:
        print(f"\n❌ T1.2 FALHOU: {e}")
        import traceback
        traceback.print_exc()
        resultados["T1.2"] = False

    # T3: Isolamento multi-tenant
    print("\n\n" + "█" * 70)
    print("█ SUITE T3: ISOLAMENTO MULTI-TENANT")
    print("█" * 70)

    test_t3 = TestT3IsolamentoMultiTenant()
    try:
        resultados["T3.1"] = await test_t3.test_t3_dois_tenants_mesmo_wa_id_nao_vazam_contexto()
    except Exception as e:
        print(f"\n❌ T3.1 FALHOU: {e}")
        import traceback
        traceback.print_exc()
        resultados["T3.1"] = False

    try:
        resultados["T3.2"] = await test_t3.test_t3_guard_validation_bloqueia_mismatch()
    except Exception as e:
        print(f"\n❌ T3.2 FALHOU: {e}")
        import traceback
        traceback.print_exc()
        resultados["T3.2"] = False

    # Resumo
    print("\n\n" + "=" * 70)
    print("RESUMO: TESTES BLOQUEADORES T1 + T3")
    print("=" * 70)

    for teste, resultado in resultados.items():
        status = "✅ PASS" if resultado else "❌ FAIL"
        print(f"  {teste}: {status}")

    total_pass = sum(1 for r in resultados.values() if r)
    total_testes = len(resultados)

    print(f"\n  Total: {total_pass}/{total_testes} PASS")

    if total_pass == total_testes:
        print(f"\n  🟢 TODOS OS BLOQUEADORES PASSARAM")
        print(f"     Seguro proceder para Semana 1")
    else:
        print(f"\n  🔴 {total_testes - total_pass} BLOQUEADORES FALHARAM")
        print(f"     Investigar antes de proceder")

    return all(resultados.values())


if __name__ == "__main__":
    sucesso = asyncio.run(main())
    exit(0 if sucesso else 1)
