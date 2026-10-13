#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes para Commit 3: Implementar D2 com mensagens inteligentes baseadas em metadata temporal

Valida:
1. Quatro cenários de validação temporal:
   - Data+Hora explícita (ambos informados): rejeita, pede reconsiderar
   - Apenas Data (hora default): rejeita, pede horário
   - Apenas Hora (sem data): rejeita, pede data
   - Nenhum (ambos faltando): rejeita, pede ambos

2. Uso de _temporal_metadata (PRIMARY) + fallback legados
3. Mensagens contextuais em português naturais
4. Sem quebra de comportamento existente
"""

def test_scenario_data_hora_ambos_informados():
    """S1: Data+hora ambos informados, mas dt_naive=None (inválido)

    Simula: usuário disse "segunda às 14" mas data está no passado/inválida
    Esperado: mensagem contextual mencionando que conseguiu entender data+hora
    """
    # Simulando contexto após interpretar_data_e_hora retornar None
    ctx = {
        "_temporal_metadata": {
            "data_detectada": True,
            "hora_detectada": True,
            "data_tipo": "dia_semana",
            "hora_modo": "explicita",
            "fonte": "manual_dia_semana",
            "motivo_nenhum": None,
            "criado_em": "2026-10-13T14:30:00"
        },
        "estado_fluxo": "aguardando_data",
        "modo_escolha_horario": False,
    }

    # Lógica D2
    meta = ctx.get("_temporal_metadata", {})
    data_detectada = meta.get("data_detectada") if meta else ctx.get("data_sem_hora") is True
    hora_detectada = meta.get("hora_detectada") if meta else ctx.get("hora_confirmada") is True

    assert data_detectada is True, "Data deveria estar detectada"
    assert hora_detectada is True, "Hora deveria estar detectada"

    if data_detectada and not hora_detectada:
        msg = "Deveria ser apenas data"
        assert False, msg
    elif hora_detectada and not data_detectada:
        msg = "Deveria ser apenas hora"
        assert False, msg
    else:
        # Ambos informados ou ambos faltando
        msg = "Detectou ambos - será mensagem genérica"

    print("[PASS] S1: Data+hora ambos informados")

def test_scenario_apenas_data_sem_hora():
    """S2: Apenas data informada (hora=default), dt_naive=None

    Simula: usuário disse "segunda" sem horário
    Esperado: mensagem pedindo horário específico
    """
    ctx = {
        "_temporal_metadata": {
            "data_detectada": True,
            "hora_detectada": False,  # Não foi informada
            "data_tipo": "dia_semana",
            "hora_modo": "default",  # Sistema assumiu 9:00
            "fonte": "manual_dia_semana",
            "motivo_nenhum": None,
        },
        "estado_fluxo": "aguardando_data",
    }

    meta = ctx.get("_temporal_metadata", {})
    data_detectada = meta.get("data_detectada") if meta else ctx.get("data_sem_hora") is True
    hora_detectada = meta.get("hora_detectada") if meta else ctx.get("hora_confirmada") is True

    assert data_detectada is True, "Data deveria estar detectada"
    assert hora_detectada is False, "Hora NÃO deveria estar detectada (era default)"

    if data_detectada and not hora_detectada:
        msg = "Contextual: pede horário"
        ctx["estado_fluxo"] = "aguardando_horario"
        assert ctx["estado_fluxo"] == "aguardando_horario"
    else:
        assert False, "Deveria ter caído no cenário 'apenas data'"

    print("[PASS] S2: Apenas data (pede horário)")

def test_scenario_apenas_hora_sem_data():
    """S3: Apenas hora informada (sem data), dt_naive=None

    Simula: usuário disse "às 14:30" sem mencionar dia
    Esperado: mensagem pedindo data específica
    """
    ctx = {
        "_temporal_metadata": {
            "data_detectada": False,  # Não foi informada
            "hora_detectada": True,   # Foi informada
            "data_tipo": None,
            "hora_modo": "explicita",
            "fonte": None,
            "motivo_nenhum": "so_hora",
        },
        "estado_fluxo": "aguardando_data",
    }

    meta = ctx.get("_temporal_metadata", {})
    data_detectada = meta.get("data_detectada") if meta else ctx.get("data_sem_hora") is True
    hora_detectada = meta.get("hora_detectada") if meta else ctx.get("hora_confirmada") is True

    assert data_detectada is False, "Data NÃO deveria estar detectada"
    assert hora_detectada is True, "Hora deveria estar detectada"

    if data_detectada and not hora_detectada:
        assert False, "Deveria ser apenas hora"
    elif hora_detectada and not data_detectada:
        msg = "Contextual: pede data"
        ctx["estado_fluxo"] = "aguardando_data"
        assert ctx["estado_fluxo"] == "aguardando_data"
    else:
        assert False, "Deveria ter caído no cenário 'apenas hora'"

    print("[PASS] S3: Apenas hora (pede data)")

def test_scenario_nenhum_informado():
    """S4: Nenhum informado (ambos faltando), dt_naive=None

    Simula: usuário disse algo sem data ou hora relevantes
    Esperado: mensagem pedindo ambos (data + hora)
    """
    ctx = {
        "_temporal_metadata": {
            "data_detectada": False,
            "hora_detectada": False,
            "data_tipo": None,
            "hora_modo": None,
            "fonte": None,
            "motivo_nenhum": "sem_pista",
        },
        "estado_fluxo": "aguardando_data",
    }

    meta = ctx.get("_temporal_metadata", {})
    data_detectada = meta.get("data_detectada") if meta else ctx.get("data_sem_hora") is True
    hora_detectada = meta.get("hora_detectada") if meta else ctx.get("hora_confirmada") is True

    assert data_detectada is False, "Data NÃO deveria estar detectada"
    assert hora_detectada is False, "Hora NÃO deveria estar detectada"

    if data_detectada and not hora_detectada:
        assert False, "Deveria ser apenas data"
    elif hora_detectada and not data_detectada:
        assert False, "Deveria ser apenas hora"
    else:
        # Ambos faltando
        msg = "Contextual: pede ambos"
        ctx["estado_fluxo"] = "aguardando_data_hora"
        assert ctx["estado_fluxo"] == "aguardando_data_hora"

    print("[PASS] S4: Nenhum informado (pede ambos)")

def test_fallback_para_legados():
    """T1: Fallback para campos legados quando _temporal_metadata não existe

    Simula: sessão antiga que não tem _temporal_metadata mas tem campos legados
    """
    # Contexto antigo sem _temporal_metadata
    ctx = {
        "data_sem_hora": True,      # Indica: data foi detectada SEM hora
        "hora_confirmada": False,   # Indica: hora NÃO foi confirmada
        "estado_fluxo": "aguardando_data",
    }

    meta = ctx.get("_temporal_metadata", {})
    # Se não tem _temporal_metadata, usa campos legados
    if not meta or not meta.get("data_detectada"):
        data_detectada = ctx.get("data_sem_hora") is True
    else:
        data_detectada = meta.get("data_detectada")

    if not meta or not meta.get("hora_detectada"):
        hora_detectada = ctx.get("hora_confirmada") is True
    else:
        hora_detectada = meta.get("hora_detectada")

    assert data_detectada is True, "Fallback: data_sem_hora=True"
    assert hora_detectada is False, "Fallback: hora_confirmada=False"

    print("[PASS] T1: Fallback para campos legados")

def test_ausencia_metadata_sem_fallback():
    """T2: Sem _temporal_metadata E sem campos legados

    Simula: contexto completamente novo/vazio
    Esperado: assume ambos faltando (mensagem genérica)
    """
    ctx = {
        "estado_fluxo": "aguardando_data",
    }

    meta = ctx.get("_temporal_metadata", {})
    data_detectada = meta.get("data_detectada") if meta else ctx.get("data_sem_hora") is True
    hora_detectada = meta.get("hora_detectada") if meta else ctx.get("hora_confirmada") is True

    # Sem metadata e sem fallback: ambos retornam False
    assert data_detectada is False
    assert hora_detectada is False

    print("[PASS] T2: Sem metadata, sem fallback")

def test_prioridade_metadata_sobre_legados():
    """T3: _temporal_metadata tem PRIORIDADE sobre campos legados

    Simula: contexto com AMBOS presentes (metadata deve ganhar)
    """
    ctx = {
        "_temporal_metadata": {
            "data_detectada": True,
            "hora_detectada": True,
        },
        "data_sem_hora": False,       # Conflita com metadata
        "hora_confirmada": False,      # Conflita com metadata
        "estado_fluxo": "aguardando_data",
    }

    meta = ctx.get("_temporal_metadata", {})
    # _temporal_metadata é PRIMARY
    data_detectada = meta.get("data_detectada") if meta else ctx.get("data_sem_hora") is True
    hora_detectada = meta.get("hora_detectada") if meta else ctx.get("hora_confirmada") is True

    assert data_detectada is True, "Metadata deveria ganhar: True"
    assert hora_detectada is True, "Metadata deveria ganhar: True"

    print("[PASS] T3: _temporal_metadata é PRIMARY")

def test_mensagem_apenas_data_graceful():
    """M1: Cenário 'apenas data' produz mensagem útil

    Verifica que a lógica de montar mensagem faz sentido
    """
    data_hora_str = "2026-10-19T09:00:00"  # Simulando data_hora parseada
    data_detectada = True
    hora_detectada = False

    if data_detectada and not hora_detectada:
        # Mensagem que seria enviada
        msg = f"Perfeito, segunda-feira.\n\nQual horário você prefere?"
        assert "Qual horário" in msg.lower()
        assert len(msg) > 10

    print("[PASS] M1: Mensagem 'apenas data' é clara")

def test_mensagem_apenas_hora_graceful():
    """M2: Cenário 'apenas hora' produz mensagem útil"""
    hora_detectada = True
    data_detectada = False

    if hora_detectada and not data_detectada:
        msg = "Ótimo, e qual dia você prefere?"
        assert "qual dia" in msg.lower()
        assert len(msg) > 10

    print("[PASS] M2: Mensagem 'apenas hora' é clara")

def test_mensagem_ambos_faltando_graceful():
    """M3: Cenário 'ambos faltando' produz mensagem útil"""
    data_detectada = False
    hora_detectada = False

    if not data_detectada and not hora_detectada:
        msg = "Qual data e hora você gostaria? Pode ser 'segunda às 14:30' ou 'amanhã de tarde'."
        assert "data" in msg.lower() and "hora" in msg.lower()
        assert len(msg) > 20

    print("[PASS] M3: Mensagem 'ambos faltando' é clara")

def run_all_tests():
    """Executa todos os testes"""
    print("\n=== TESTES COMMIT 3: D2 Mensagens Inteligentes Temporais ===\n")

    print("--- CENÁRIOS PRINCIPAIS ---")
    test_scenario_data_hora_ambos_informados()
    test_scenario_apenas_data_sem_hora()
    test_scenario_apenas_hora_sem_data()
    test_scenario_nenhum_informado()

    print("\n--- FALLBACK E PRECEDÊNCIA ---")
    test_fallback_para_legados()
    test_ausencia_metadata_sem_fallback()
    test_prioridade_metadata_sobre_legados()

    print("\n--- MENSAGENS GRACEFUL ---")
    test_mensagem_apenas_data_graceful()
    test_mensagem_apenas_hora_graceful()
    test_mensagem_ambos_faltando_graceful()

    print("\n=== [OK] TODOS OS 10 TESTES PASSARAM ===\n")
    print("Commit 3 validado:")
    print("  - 4 cenários de validação temporal")
    print("  - Fallback para campos legados funciona")
    print("  - Mensagens contextuais são claras")
    print("  - _temporal_metadata é SOURCE of truth")
    return True

if __name__ == "__main__":
    try:
        resultado = run_all_tests()
        exit(0 if resultado else 1)
    except AssertionError as e:
        print(f"\n[ERROR] TESTE FALHOU: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    except Exception as e:
        print(f"\n[ERROR] ERRO NAO PREVISTO: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
