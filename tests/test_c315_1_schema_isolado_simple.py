#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TESTES C3.15.1 — SCHEMA ISOLADO (VERSÃO SIMPLIFICADA SEM FIREBASE)

Testes de validação da infraestrutura do novo path:
Clientes/{tenant_id}/Donos/{actor_id}/onboarding/ativo

Executável sem dependência de Firestore (útil em C3.15.1).
"""

import sys
import time
from datetime import datetime
import pytz

sys.path.insert(0, "/workspace/services")
sys.path.insert(0, "/workspace")

from services.onboarding_isolado_schema import (
    criar_documento_onboarding_isolado,
    validar_documento_onboarding_isolado,
    validar_isolamento,
    converter_legacy_para_isolado,
    ETAPAS_ONBOARDING,
    STATUS_ONBOARDING
)


# ==============================================================================
# TESTES
# ==============================================================================

def test_1_schema_creation():
    """T1: Criação correta do schema"""
    tenant_id = "test_tenant_001"
    actor_id = "5521987654321"

    doc = criar_documento_onboarding_isolado(
        tenant_id, actor_id, "Dono Teste", "teste@exemplo.com"
    )

    # Validar estrutura
    assert "tenant_id" in doc
    assert "actor_id" in doc
    assert "onboarding_status" in doc
    assert "onboarding_etapa_atual" in doc
    assert "onboarding_indice" in doc

    # Validar valores
    assert doc["tenant_id"] == tenant_id
    assert doc["actor_id"] == actor_id
    assert doc["onboarding_status"] == "em_progresso"
    assert doc["onboarding_etapa_atual"] == "nome_negocio"
    assert doc["onboarding_indice"] == 0

    print("[PASS] T1: Schema criado corretamente")
    return True


def test_2_isolamento_actor():
    """T2: Isolamento entre actors"""
    tenant_id = "test_tenant_002"
    actor_a = "5521111111111"
    actor_b = "5522222222222"

    doc_a = criar_documento_onboarding_isolado(tenant_id, actor_a, "Dono A", "a@...")
    doc_b = criar_documento_onboarding_isolado(tenant_id, actor_b, "Dono B", "b@...")

    # Verificar isolamento
    assert doc_a.get("actor_id") != doc_b.get("actor_id")
    assert doc_a.get("dono_nome") != doc_b.get("dono_nome")
    assert validar_isolamento(doc_a, doc_b) == True

    print("[PASS] T2: Isolamento entre actors funciona")
    return True


def test_3_isolamento_tenant():
    """T3: Isolamento entre tenants"""
    actor_id = "5521987654321"
    tenant_1 = "tenant_1"
    tenant_2 = "tenant_2"

    doc_1 = criar_documento_onboarding_isolado(tenant_1, actor_id, "Dono", "d@...")
    doc_2 = criar_documento_onboarding_isolado(tenant_2, actor_id, "Dono", "d@...")

    # Verificar isolamento
    assert doc_1.get("tenant_id") != doc_2.get("tenant_id")
    assert validar_isolamento(doc_1, doc_2) == True

    print("[PASS] T3: Isolamento entre tenants funciona")
    return True


def test_4_schema_minimo():
    """T4: Schema contém todos os campos mínimos"""
    doc = criar_documento_onboarding_isolado("t1", "a1", "N", "e@...")

    campos_obrigatorios = [
        "tenant_id", "actor_id",
        "onboarding_status", "onboarding_etapa_atual", "onboarding_indice",
        "criado_em", "criado_por", "atualizado_em"
    ]

    for campo in campos_obrigatorios:
        assert campo in doc, f"Campo faltando: {campo}"
        assert doc[campo] is not None, f"Campo vazio: {campo}"

    print("[PASS] T4: Schema contém todos os campos mínimos")
    return True


def test_5_validacao_schema():
    """T5: Validação de schema"""
    # Documento válido
    doc_valido = criar_documento_onboarding_isolado("t1", "a1", "N", "e@...")
    valido, motivo = validar_documento_onboarding_isolado(doc_valido)
    assert valido, f"Documento válido rejeitado: {motivo}"

    # Documento inválido (falta tenant_id)
    doc_invalido = doc_valido.copy()
    del doc_invalido["tenant_id"]
    valido, motivo = validar_documento_onboarding_isolado(doc_invalido)
    assert not valido, "Deveria rejeitar falta de tenant_id"

    # Documento com status inválido
    doc_invalido2 = doc_valido.copy()
    doc_invalido2["onboarding_status"] = "status_invalido"
    valido, motivo = validar_documento_onboarding_isolado(doc_invalido2)
    assert not valido, "Deveria rejeitar status inválido"

    print("[PASS] T5: Validação de schema funciona")
    return True


def test_6_conversao_legacy():
    """T6: Conversão de legacy para isolado"""
    legacy_doc = {
        "dono_actor_id": "5521987654321",
        "dono_nome": "Maria Silva",
        "dono_email": "maria@exemplo.com",
        "onboarding_status": "em_progresso",
        "onboarding_etapa_atual": "segmento",
        "onboarding_indice": 1,
        "criado_em": "2026-09-26T10:00:00Z",
        "criado_por": "5521987654321",
        "atualizado_em": "2026-09-26T11:00:00Z",
        "nome_negocio": "Salão da Maria",
        "segmento": "Salão de Beleza"
    }

    novo_doc = converter_legacy_para_isolado(legacy_doc, "tenant_1", "5521987654321")

    # Verificar dados copiados
    assert novo_doc.get("dono_nome") == "Maria Silva"
    assert novo_doc.get("segmento") == "Salão de Beleza"
    assert novo_doc.get("onboarding_etapa_atual") == "segmento"
    assert novo_doc.get("migrado_de_legacy") == True

    # Validar documento
    valido, motivo = validar_documento_onboarding_isolado(novo_doc)
    assert valido, f"Documento convertido inválido: {motivo}"

    print("[PASS] T6: Conversão de legacy funciona")
    return True


def test_7_ownership_validation():
    """T7: Validação de ownership"""
    doc_valido = criar_documento_onboarding_isolado("t1", "a1", "N", "e@...")
    valido, _ = validar_documento_onboarding_isolado(doc_valido)
    assert valido, "Ownership correto deveria ser válido"

    # Ownership incorreto
    doc_invalido = doc_valido.copy()
    doc_invalido["criado_por"] = "outro_ator"
    valido, motivo = validar_documento_onboarding_isolado(doc_invalido)
    assert not valido, "Ownership incorreto deveria ser rejeitado"

    print("[PASS] T7: Validação de ownership funciona")
    return True


def test_8_etapas_validas():
    """T8: Validação de etapas"""
    # Testar etapas válidas
    for etapa in ETAPAS_ONBOARDING:
        doc = criar_documento_onboarding_isolado("t1", "a1", "N", "e@...")
        doc["onboarding_etapa_atual"] = etapa

        valido, motivo = validar_documento_onboarding_isolado(doc)
        assert valido, f"Etapa válida rejeitada: {etapa} — {motivo}"

    # Testar etapa inválida
    doc = criar_documento_onboarding_isolado("t1", "a1", "N", "e@...")
    doc["onboarding_etapa_atual"] = "etapa_invalida"
    valido, motivo = validar_documento_onboarding_isolado(doc)
    assert not valido, "Etapa inválida deveria ser rejeitada"

    print("[PASS] T8: Validação de etapas funciona")
    return True


def test_9_indice_intervalo():
    """T9: Validação de índice"""
    doc = criar_documento_onboarding_isolado("t1", "a1", "N", "e@...")

    # Índice fora de intervalo
    doc["onboarding_indice"] = 999
    valido, motivo = validar_documento_onboarding_isolado(doc)
    assert not valido, "Índice fora de intervalo deveria ser rejeitado"

    print("[PASS] T9: Validação de índice funciona")
    return True


def test_10_status_valido():
    """T10: Validação de status"""
    doc = criar_documento_onboarding_isolado("t1", "a1", "N", "e@...")

    # Testar status válidos
    for status in STATUS_ONBOARDING:
        doc["onboarding_status"] = status
        valido, _ = validar_documento_onboarding_isolado(doc)
        assert valido, f"Status válido rejeitado: {status}"

    # Testar status inválido
    doc["onboarding_status"] = "status_invalido"
    valido, motivo = validar_documento_onboarding_isolado(doc)
    assert not valido, "Status inválido deveria ser rejeitado"

    print("[PASS] T10: Validação de status funciona")
    return True


# ==============================================================================
# EXECUÇÃO
# ==============================================================================

if __name__ == "__main__":
    tests = [
        test_1_schema_creation,
        test_2_isolamento_actor,
        test_3_isolamento_tenant,
        test_4_schema_minimo,
        test_5_validacao_schema,
        test_6_conversao_legacy,
        test_7_ownership_validation,
        test_8_etapas_validas,
        test_9_indice_intervalo,
        test_10_status_valido
    ]

    print("\n" + "="*70)
    print("C3.15.1 TESTES — SCHEMA ISOLADO")
    print("="*70 + "\n")

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test_func.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[FAIL] {test_func.__name__}: ERRO — {e}")
            failed += 1

    print("\n" + "="*70)
    print(f"RESULTADO: {passed}/10 PASS, {failed}/10 FAIL")
    print("="*70 + "\n")

    exit(0 if failed == 0 else 1)
