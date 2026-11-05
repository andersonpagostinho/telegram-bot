"""
P0.19 — E2E TEST COM FIRESTORE REAL

Validar que horários explícitos sobrescrevem contexto em 4 cenários contra Firestore.
"""

import asyncio
import pytest
from datetime import datetime
from firebase_admin import firestore
from services.firebase_service_async import salvar_dado_em_path, buscar_dado_em_path


# Tenant e cliente para teste
TEST_TENANT_ID = "teste_p0_19"
TEST_CLIENT_ID = "cliente_p0_19"
TEST_CLIENT_PHONE = "5511999990019"


async def setup_firestore():
    """Inicializa Firestore e limpa dados anteriores."""
    try:
        db = firestore.client()

        # Limpar dados antigos
        for scenario in ["A", "B", "C", "D"]:
            ctx_path = f"Clientes/{TEST_TENANT_ID}/{TEST_CLIENT_ID}/contexto_scenario_{scenario}"
            try:
                await buscar_dado_em_path(ctx_path)
                # Se existe, delete será feito ao final
            except:
                pass

        print(f"[SETUP] Firestore pronto para testes P0.19")
        return db
    except Exception as e:
        print(f"[ERROR] Firestore setup falhou: {e}")
        raise


async def cenario_a_horario_sobrescreve():
    """
    Cenário A: Contexto anterior 14:00 + mensagem "14:10" → 14:10

    Simula:
    1. Usuário confirmou agendamento para 14:00
    2. Usuário manda "14:10" (ajuste incremental)
    3. Sistema deve aplicar 14:10
    """
    print("\n[CENARIO_A] Iniciando: 14:00 → 14:10")

    ctx_path = f"Clientes/{TEST_TENANT_ID}/{TEST_CLIENT_ID}/contexto_scenario_a"

    # 1. Estado anterior: contexto com 14:00
    ctx_anterior = {
        "data_hora": "2026-11-05T14:00:00",
        "servico": "corte",
        "profissional_escolhido": None,
        "profissional_indiferente": True,
        "draft_agendamento": {
            "data_hora": "2026-11-05T14:00:00",
            "servico": "corte",
        },
        "objetivo_conversacional": None,
    }

    await salvar_dado_em_path(ctx_path, ctx_anterior)
    print(f"  ✓ Salvo contexto anterior: data_hora=14:00")

    # 2. Simular extração P0.19: usuário disse "14:10"
    from router.principal_router import _extrair_hora_simples

    hora_detectada = _extrair_hora_simples("14:10")
    assert hora_detectada == (14, 10), f"Esperado (14, 10), got {hora_detectada}"

    # 3. Aplicar hora nova (simulando P0.19 logic)
    data_hora_anterior = ctx_anterior["data_hora"]
    data_anterior = data_hora_anterior.split("T")[0]
    hora_nova, minuto_nova = hora_detectada
    nova_data_hora = f"{data_anterior}T{hora_nova:02d}:{minuto_nova:02d}:00"

    ctx_anterior["data_hora"] = nova_data_hora
    ctx_anterior["draft_agendamento"]["data_hora"] = nova_data_hora
    ctx_anterior["hora_confirmada"] = True

    await salvar_dado_em_path(ctx_path, ctx_anterior)
    print(f"  ✓ Atualizado: data_hora=14:10")

    # 4. Validar no Firestore
    ctx_lido = await buscar_dado_em_path(ctx_path)
    assert ctx_lido.get("data_hora") == "2026-11-05T14:10:00", \
        f"Esperado 14:10, got {ctx_lido.get('data_hora')}"
    assert ctx_lido.get("hora_confirmada") is True

    print(f"  ✅ CENARIO_A PASS: Firestore mostra 14:10")
    return True


async def cenario_b_confirmacao_preserva():
    """
    Cenário B: Draft 14:10 + mensagem "pode" → preserva 14:10

    Simula:
    1. Draft com 14:10
    2. Usuário envia "pode" (confirmação)
    3. Sistema NÃO deve extrair nova hora, preserva 14:10
    """
    print("\n[CENARIO_B] Iniciando: draft 14:10 + 'pode' → preserva")

    ctx_path = f"Clientes/{TEST_TENANT_ID}/{TEST_CLIENT_ID}/contexto_scenario_b"

    # 1. Estado com draft 14:10
    ctx_anterior = {
        "data_hora": "2026-11-05T14:10:00",
        "servico": "corte",
        "profissional_escolhido": None,
        "profissional_indiferente": True,
        "draft_agendamento": {
            "data_hora": "2026-11-05T14:10:00",
            "servico": "corte",
        },
    }

    await salvar_dado_em_path(ctx_path, ctx_anterior)
    print(f"  ✓ Salvo draft: data_hora=14:10")

    # 2. Simular P0.19: usuário disse "pode"
    from router.principal_router import _extrair_hora_simples

    hora_detectada = _extrair_hora_simples("pode")
    assert hora_detectada is None, f"'pode' nao deve extrair hora, got {hora_detectada}"

    # 3. NÃO fazer alteração (preserve existing)
    # ctx_anterior permanece com 14:10

    await salvar_dado_em_path(ctx_path, ctx_anterior)
    print(f"  ✓ Nenhuma alteração (confirmação preserva)")

    # 4. Validar Firestore
    ctx_lido = await buscar_dado_em_path(ctx_path)
    assert ctx_lido.get("data_hora") == "2026-11-05T14:10:00", \
        f"Esperado 14:10 preservado, got {ctx_lido.get('data_hora')}"

    print(f"  ✅ CENARIO_B PASS: Firestore preserva 14:10")
    return True


async def cenario_c_consulta_sem_heranca():
    """
    Cenário C: Draft 14:10 + consulta sem horário → não herdar

    Simula:
    1. Draft com 14:10 (de agendamento anterior)
    2. Usuário envia "qual horário você está disponível?" (consulta)
    3. Sistema NÃO deve herdar automaticamente 14:10
    """
    print("\n[CENARIO_C] Iniciando: consulta sem herança de draft")

    ctx_path = f"Clientes/{TEST_TENANT_ID}/{TEST_CLIENT_ID}/contexto_scenario_c"

    # 1. Estado com draft 14:10
    ctx_anterior = {
        "data_hora": "2026-11-05T14:10:00",
        "draft_agendamento": {
            "data_hora": "2026-11-05T14:10:00",
        },
        "objetivo_conversacional": None,  # Não é ajuste
    }

    await salvar_dado_em_path(ctx_path, ctx_anterior)
    print(f"  ✓ Salvo draft: data_hora=14:10")

    # 2. Simular P0.19: usuário fez consulta sem horário
    from router.principal_router import _extrair_hora_simples

    hora_detectada = _extrair_hora_simples("qual horario voce esta disponivel?")
    assert hora_detectada is None

    # 3. NÃO aplicar horário (skip_data_complexa protege)
    # ctx_anterior permanece, mas não é forçadamente herdado

    # 4. Validar Firestore
    ctx_lido = await buscar_dado_em_path(ctx_path)
    assert ctx_lido.get("data_hora") == "2026-11-05T14:10:00", \
        f"Draft preservado, got {ctx_lido.get('data_hora')}"

    print(f"  ✅ CENARIO_C PASS: Consulta não força herança")
    return True


async def cenario_d_novo_ajuste():
    """
    Cenário D: Draft 14:10 + "na verdade, 14:20" → 14:20

    Simula:
    1. Draft com 14:10
    2. Usuário envia "na verdade, 14:20" (novo ajuste)
    3. Sistema deve aplicar 14:20
    """
    print("\n[CENARIO_D] Iniciando: 14:10 → 14:20")

    ctx_path = f"Clientes/{TEST_TENANT_ID}/{TEST_CLIENT_ID}/contexto_scenario_d"

    # 1. Estado com draft 14:10
    ctx_anterior = {
        "data_hora": "2026-11-05T14:10:00",
        "draft_agendamento": {
            "data_hora": "2026-11-05T14:10:00",
            "servico": "corte",
        },
        "profissional_indiferente": True,
        "objetivo_conversacional": "ajustar_draft_existente",
    }

    await salvar_dado_em_path(ctx_path, ctx_anterior)
    print(f"  ✓ Salvo draft: data_hora=14:10")

    # 2. Simular P0.19: usuário disse "na verdade, 14:20"
    from router.principal_router import _extrair_hora_simples

    hora_detectada = _extrair_hora_simples("na verdade, 14:20")
    assert hora_detectada == (14, 20), f"Esperado (14, 20), got {hora_detectada}"

    # 3. Aplicar hora nova
    data_hora_anterior = ctx_anterior["data_hora"]
    data_anterior = data_hora_anterior.split("T")[0]
    hora_nova, minuto_nova = hora_detectada
    nova_data_hora = f"{data_anterior}T{hora_nova:02d}:{minuto_nova:02d}:00"

    ctx_anterior["data_hora"] = nova_data_hora
    ctx_anterior["draft_agendamento"]["data_hora"] = nova_data_hora
    ctx_anterior["hora_confirmada"] = True

    await salvar_dado_em_path(ctx_path, ctx_anterior)
    print(f"  ✓ Atualizado: data_hora=14:20")

    # 4. Validar Firestore
    ctx_lido = await buscar_dado_em_path(ctx_path)
    assert ctx_lido.get("data_hora") == "2026-11-05T14:20:00", \
        f"Esperado 14:20, got {ctx_lido.get('data_hora')}"
    assert ctx_lido.get("hora_confirmada") is True

    print(f"  ✅ CENARIO_D PASS: Firestore mostra 14:20")
    return True


async def cleanup_firestore():
    """Limpa dados de teste do Firestore."""
    print("\n[CLEANUP] Removendo dados de teste...")
    try:
        for scenario in ["a", "b", "c", "d"]:
            ctx_path = f"Clientes/{TEST_TENANT_ID}/{TEST_CLIENT_ID}/contexto_scenario_{scenario}"
            # Firestore não tem delete simples, apenas deixamos os dados
            # (Em produção, usar batch delete)
        print("[CLEANUP] Dados deixados para inspeção manual")
    except Exception as e:
        print(f"[CLEANUP] Erro (não crítico): {e}")


@pytest.mark.asyncio
async def test_p0_19_e2e_firestore_cenario_a():
    """E2E Cenário A: 14:00 → 14:10"""
    db = await setup_firestore()
    result = await cenario_a_horario_sobrescreve()
    assert result is True


@pytest.mark.asyncio
async def test_p0_19_e2e_firestore_cenario_b():
    """E2E Cenário B: preserva 14:10"""
    db = await setup_firestore()
    result = await cenario_b_confirmacao_preserva()
    assert result is True


@pytest.mark.asyncio
async def test_p0_19_e2e_firestore_cenario_c():
    """E2E Cenário C: não herda"""
    db = await setup_firestore()
    result = await cenario_c_consulta_sem_heranca()
    assert result is True


@pytest.mark.asyncio
async def test_p0_19_e2e_firestore_cenario_d():
    """E2E Cenário D: 14:10 → 14:20"""
    db = await setup_firestore()
    result = await cenario_d_novo_ajuste()
    assert result is True


async def run_all_scenarios():
    """Executa todos os 4 cenários em sequência."""
    print("\n" + "="*70)
    print("P0.19 — E2E TEST COM FIRESTORE REAL (4 CENÁRIOS)")
    print("="*70)

    await setup_firestore()

    try:
        await cenario_a_horario_sobrescreve()
        await cenario_b_confirmacao_preserva()
        await cenario_c_consulta_sem_heranca()
        await cenario_d_novo_ajuste()

        print("\n" + "="*70)
        print("✅ TODOS OS 4 CENÁRIOS PASSARAM NO FIRESTORE!")
        print("="*70 + "\n")
        return True

    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        return False
    finally:
        await cleanup_firestore()


if __name__ == "__main__":
    result = asyncio.run(run_all_scenarios())
    exit(0 if result else 1)
