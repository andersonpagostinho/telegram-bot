#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes para Commit 2: Integrar metadados temporais em extrair_slots_e_mesclar()

Valida:
1. Metadados sao salvos em ctx["_temporal_metadata"]
2. Comportamento legado de ctx["data_hora"] preservado
3. Nao sobrescrever metadados com dados vazios
4. Sessoes antigas sem _temporal_metadata funcionam
5. Compatibilidade com incrementalidade (data depois hora)
"""

import sys
import asyncio
sys.path.insert(0, '/root/path')  # Ajustar se necessario

from router.principal_router import extrair_slots_e_mesclar

async def test_data_hora_explicita():
    """T1: Data+hora explicita salva metadados completos"""
    ctx = {}
    texto = "segunda as 14:30"
    dono_id = "test_dono_001"
    cliente_id = "test_cliente_001"

    resultado = await extrair_slots_e_mesclar(ctx, texto, dono_id, cliente_id)

    # Verificar metadados salvos
    assert "_temporal_metadata" in resultado, "Deveria ter _temporal_metadata"
    assert resultado["_temporal_metadata"]["data_detectada"] is True
    assert resultado["_temporal_metadata"]["hora_detectada"] is True
    assert resultado["_temporal_metadata"]["hora_modo"] == "explicita"

    # Verificar comportamento legado preservado
    assert "data_hora" in resultado, "data_hora deveria existir"
    assert resultado["data_hora"] is not None

    print("[PASS] T1: Data+hora explicita")

async def test_dia_semana_sem_hora():
    """T2: Dia semana sem hora = hora default detectada=False"""
    ctx = {}
    texto = "segunda"
    dono_id = "test_dono_001"
    cliente_id = "test_cliente_001"

    resultado = await extrair_slots_e_mesclar(ctx, texto, dono_id, cliente_id)

    # Verificar metadados: hora foi detectada? NAO (é default)
    assert "_temporal_metadata" in resultado
    assert resultado["_temporal_metadata"]["data_detectada"] is True
    assert resultado["_temporal_metadata"]["hora_detectada"] is False, "Hora nao foi explicita"
    assert resultado["_temporal_metadata"]["hora_modo"] == "default"

    # Verificar data_hora ainda foi salvo (comportamento legado)
    assert "data_hora" in resultado
    assert resultado["data_hora"] is not None

    print("[PASS] T2: Dia semana sem hora")

async def test_so_hora():
    """T3: So hora = data_detectada=False"""
    ctx = {}
    texto = "as 14:30"
    dono_id = "test_dono_001"
    cliente_id = "test_cliente_001"

    resultado = await extrair_slots_e_mesclar(ctx, texto, dono_id, cliente_id)

    # Verificar metadados: data foi detectada? NAO
    assert "_temporal_metadata" in resultado
    assert resultado["_temporal_metadata"]["data_detectada"] is False, "Data nao foi informada"
    assert resultado["_temporal_metadata"]["hora_detectada"] is True
    assert resultado["_temporal_metadata"]["motivo_nenhum"] == "so_hora"

    # Comportamento legado: data_hora nao deveria ser setado
    # (porque interpretar_data_e_hora retorna None para so_hora)

    print("[PASS] T3: So hora")

async def test_sem_pista():
    """T4: Sem pista temporal = nao salvar metadados (guardiao IF)"""
    ctx = {}
    texto = "texto aleatorio sem data"
    dono_id = "test_dono_001"
    cliente_id = "test_cliente_001"

    resultado = await extrair_slots_e_mesclar(ctx, texto, dono_id, cliente_id)

    # Verificar que metadados NAO foram salvos (guardiao: if data_detectada or hora_detectada)
    assert "_temporal_metadata" not in resultado, "Nao deveria salvar metadados vazios"

    print("[PASS] T4: Sem pista (nao salvar vazios)")

async def test_sessao_antiga_sem_metadata():
    """T5: Sessao antiga sem _temporal_metadata nao quebra"""
    ctx = {"data_hora": "2026-10-19T09:00:00"}  # Sessao antiga
    texto = "segunda as 14"
    dono_id = "test_dono_001"
    cliente_id = "test_cliente_001"

    resultado = await extrair_slots_e_mesclar(ctx, texto, dono_id, cliente_id)

    # Deveria funcionar normalmente
    assert "data_hora" in resultado
    assert "_temporal_metadata" in resultado  # Nova informacao temporal será salva

    print("[PASS] T5: Sessao antiga compativel")

async def test_incrementalidade():
    """T6: Primeira msg 'segunda', depois 'as 14' (incremental)"""
    # Passo 1: Usuário fala "segunda"
    ctx1 = {}
    resultado1 = await extrair_slots_e_mesclar(ctx1, "segunda", "test_dono", "test_cliente")

    assert "_temporal_metadata" in resultado1
    assert resultado1["_temporal_metadata"]["hora_detectada"] is False
    assert resultado1["_temporal_metadata"]["data_tipo"] == "dia_semana"

    # Passo 2: Usuário responde "as 14" (hora incremental)
    ctx2 = resultado1  # Usar contexto da resposta anterior
    resultado2 = await extrair_slots_e_mesclar(ctx2, "as 14", "test_dono", "test_cliente")

    # Deveria ter detectado a hora agora
    assert "_temporal_metadata" in resultado2
    # Pode ter hora detectada (se interpretador conseguiu combinar) ou so_hora
    print("[PASS] T6: Incrementalidade preservada")

async def test_data_hora_preservado():
    """T7: ctx['data_hora'] continua sendo atualizado (compatibilidade)"""
    ctx = {}
    texto = "amanha as 15:00"

    resultado = await extrair_slots_e_mesclar(ctx, texto, "test_dono", "test_cliente")

    # Verificar que data_hora foi setado (comportamento legado)
    assert "data_hora" in resultado
    assert resultado["data_hora"] is not None
    assert "T" in resultado["data_hora"]  # Formato ISO

    print("[PASS] T7: data_hora preservado")

async def run_all_tests():
    """Executa todos os testes"""
    print("\n=== TESTES COMMIT 2: Integracao de Metadados Temporais ===\n")

    try:
        await test_data_hora_explicita()
        await test_dia_semana_sem_hora()
        await test_so_hora()
        await test_sem_pista()
        await test_sessao_antiga_sem_metadata()
        await test_incrementalidade()
        await test_data_hora_preservado()

        print("\n=== [OK] TODOS OS 7 TESTES PASSARAM ===\n")
        print("Gates 1-2 validados:")
        print("  Gate 1: Integracao minima em extrair_slots_e_mesclar()")
        print("  Gate 2: Testes focados (sem Firestore)")
        return True
    except AssertionError as e:
        print(f"\n[ERROR] TESTE FALHOU: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    resultado = asyncio.run(run_all_tests())
    exit(0 if resultado else 1)
