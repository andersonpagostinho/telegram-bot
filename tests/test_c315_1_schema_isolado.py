#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TESTES C3.15.1 — SCHEMA ISOLADO POR ACTOR

Responsabilidade: Validar infraestrutura do novo path

Clientes/{tenant_id}/Donos/{actor_id}/onboarding/ativo

Testes coberando:
1. Construção correta do path
2. Isolamento de actor A/B
3. Isolamento de tenant
4. Schema mínimo
5. Validação de schema
6. Conversão de legacy
7. Firestore real (write/read/cleanup)

IMPORTANTE:
- Usar Firestore REAL conforme padrão projeto
- Não modificar dados de produção
- Tenant 7394370553 não deve ser tocado
- Testes usam tenant de teste com cleanup automático
"""

import pytest
import sys
import time
from datetime import datetime
import pytz

# Adicionar services ao path
sys.path.insert(0, "/workspace/services")
sys.path.insert(0, "/workspace")

from services.onboarding_isolado_schema import (
    criar_documento_onboarding_isolado,
    validar_documento_onboarding_isolado,
    validar_isolamento,
    obter_ref_onboarding_isolado,
    converter_legacy_para_isolado,
    ETAPAS_ONBOARDING,
    STATUS_ONBOARDING
)
from services.firestore_client import get_db


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def db():
    """Retorna cliente Firestore real (OPCIONAL em C3.15.1)"""
    try:
        return get_db()
    except Exception as e:
        print(f"⚠️  Firestore não disponível: {e}")
        return None


@pytest.fixture
def tenant_teste():
    """Gera ID de tenant único para teste"""
    return f"test_c315_1_{int(time.time())}"


@pytest.fixture
def actor_teste_1():
    """Primeiro actor para teste"""
    return f"5521{int(time.time()) % 1000000:06d}"


@pytest.fixture
def actor_teste_2():
    """Segundo actor para teste"""
    return f"5522{int(time.time()) % 1000000:06d}"


# ==============================================================================
# T1: CONSTRUÇÃO CORRETA DO PATH
# ==============================================================================

def test_path_construction(db, tenant_teste, actor_teste_1):
    """
    Verifica que path novo é construído corretamente.

    Path esperado:
    Clientes/{tenant_id}/Donos/{actor_id}/onboarding/ativo
    """

    # Construir referência
    doc_ref = obter_ref_onboarding_isolado(db, tenant_teste, actor_teste_1)

    # Verificar path
    path_str = doc_ref.path

    assert f"Clientes/{tenant_teste}" in path_str, f"Tenant não está no path: {path_str}"
    assert f"Donos/{actor_teste_1}" in path_str, f"Actor não está no path: {path_str}"
    assert "onboarding/ativo" in path_str, f"onboarding/ativo não está no path: {path_str}"

    print(f"✅ T1: Path construído corretamente: {path_str}")


# ==============================================================================
# T2: ISOLAMENTO DE ACTOR A/B
# ==============================================================================

def test_actor_isolation(tenant_teste, actor_teste_1, actor_teste_2):
    """
    Verifica que actor A não acessa documento de actor B.

    Dois atores diferentes devem ter documentos diferentes.
    """

    # Criar documentos para dois atores
    doc_a = criar_documento_onboarding_isolado(
        tenant_teste, actor_teste_1, "Dono A", "a@exemplo.com"
    )
    doc_b = criar_documento_onboarding_isolado(
        tenant_teste, actor_teste_2, "Dono B", "b@exemplo.com"
    )

    # Verificar que não são o mesmo documento
    assert doc_a.get("actor_id") != doc_b.get("actor_id"), "Actors devem ser diferentes"
    assert doc_a.get("dono_nome") != doc_b.get("dono_nome"), "Nomes devem ser diferentes"
    assert doc_a != doc_b, "Documentos devem ser diferentes"

    # Verificar isolamento
    assert validar_isolamento(doc_a, doc_b), "Documentos devem estar isolados"

    print(f"✅ T2: Actor isolamento funciona corretamente")


# ==============================================================================
# T3: ISOLAMENTO DE TENANT
# ==============================================================================

def test_tenant_isolation(db, actor_teste_1):
    """
    Verifica que mesmo actor em tenants diferentes = documentos diferentes.
    """

    tenant_1 = f"tenant_1_{int(time.time())}"
    tenant_2 = f"tenant_2_{int(time.time())}"

    # Criar documentos para mesma actor em tenants diferentes
    doc_1 = criar_documento_onboarding_isolado(tenant_1, actor_teste_1, "Dono", "d@...")
    doc_2 = criar_documento_onboarding_isolado(tenant_2, actor_teste_1, "Dono", "d@...")

    # Verificar que tenant_id é diferente
    assert doc_1.get("tenant_id") != doc_2.get("tenant_id"), "Tenants devem ser diferentes"

    # Verificar paths são diferentes
    ref_1 = obter_ref_onboarding_isolado(db, tenant_1, actor_teste_1)
    ref_2 = obter_ref_onboarding_isolado(db, tenant_2, actor_teste_1)

    path_1 = ref_1.path
    path_2 = ref_2.path

    assert path_1 != path_2, f"Paths devem ser diferentes: {path_1} vs {path_2}"
    assert tenant_1 in path_1 and tenant_1 not in path_2, "Tenant 1 só deve estar em path_1"
    assert tenant_2 in path_2 and tenant_2 not in path_1, "Tenant 2 só deve estar em path_2"

    print(f"✅ T3: Tenant isolamento funciona corretamente")


# ==============================================================================
# T4: SCHEMA MÍNIMO
# ==============================================================================

def test_schema_minimo(tenant_teste, actor_teste_1):
    """
    Verifica que documento tem todos os campos mínimos obrigatórios.
    """

    doc = criar_documento_onboarding_isolado(
        tenant_teste, actor_teste_1, "Nome", "email@..."
    )

    # Campos obrigatórios
    campos_obrigatorios = [
        "tenant_id", "actor_id",
        "onboarding_status", "onboarding_etapa_atual", "onboarding_indice",
        "criado_em", "criado_por", "atualizado_em"
    ]

    for campo in campos_obrigatorios:
        assert campo in doc, f"Campo obrigatório faltando: {campo}"
        assert doc[campo] is not None, f"Campo não deve ser None: {campo}"

    # Verificar valores padrão
    assert doc["onboarding_status"] == "em_progresso"
    assert doc["onboarding_etapa_atual"] == "nome_negocio"
    assert doc["onboarding_indice"] == 0

    print(f"✅ T4: Schema mínimo contém todos os campos necessários")


# ==============================================================================
# T5: VALIDAÇÃO DE SCHEMA
# ==============================================================================

def test_validacao_schema(tenant_teste, actor_teste_1):
    """
    Verifica que validador rejeita documentos inválidos.
    """

    # Documento válido
    doc_valido = criar_documento_onboarding_isolado(tenant_teste, actor_teste_1, "N", "e@...")
    valido, motivo = validar_documento_onboarding_isolado(doc_valido)
    assert valido, f"Documento válido foi rejeitado: {motivo}"

    # Documento inválido: falta tenant_id
    doc_invalido_1 = doc_valido.copy()
    del doc_invalido_1["tenant_id"]
    valido, motivo = validar_documento_onboarding_isolado(doc_invalido_1)
    assert not valido, "Documento sem tenant_id deveria ser rejeitado"
    assert "tenant_id" in motivo, f"Motivo deve mencionar tenant_id: {motivo}"

    # Documento inválido: status inválido
    doc_invalido_2 = doc_valido.copy()
    doc_invalido_2["onboarding_status"] = "status_invalido"
    valido, motivo = validar_documento_onboarding_isolado(doc_invalido_2)
    assert not valido, "Documento com status inválido deveria ser rejeitado"
    assert "status" in motivo.lower(), f"Motivo deve mencionar status: {motivo}"

    # Documento inválido: indice fora de intervalo
    doc_invalido_3 = doc_valido.copy()
    doc_invalido_3["onboarding_indice"] = 999
    valido, motivo = validar_documento_onboarding_isolado(doc_invalido_3)
    assert not valido, "Documento com indice fora de intervalo deveria ser rejeitado"

    print(f"✅ T5: Validador rejeita documentos inválidos corretamente")


# ==============================================================================
# T6: CONVERSÃO LEGACY → NOVO
# ==============================================================================

def test_converter_legacy_para_isolado(tenant_teste, actor_teste_1):
    """
    Verifica conversão de documento legacy para novo formato.
    """

    # Simulou documento legacy (de Configuracao/negocio)
    legacy_doc = {
        "dono_actor_id": actor_teste_1,
        "dono_nome": "Maria Silva",
        "dono_email": "maria@exemplo.com",
        "onboarding_status": "em_progresso",
        "onboarding_etapa_atual": "segmento",
        "onboarding_indice": 1,
        "criado_em": "2026-09-26T10:00:00Z",
        "criado_por": actor_teste_1,
        "atualizado_em": "2026-09-26T11:00:00Z",
        "nome_negocio": "Salão da Maria",
        "segmento": "Salão de Beleza",
        "endereco": "Rua A, 123"
    }

    # Converter
    novo_doc = converter_legacy_para_isolado(legacy_doc, tenant_teste, actor_teste_1)

    # Verificar que dados foram copiados
    assert novo_doc.get("dono_nome") == "Maria Silva"
    assert novo_doc.get("segmento") == "Salão de Beleza"
    assert novo_doc.get("nome_negocio") == "Salão da Maria"
    assert novo_doc.get("onboarding_etapa_atual") == "segmento"
    assert novo_doc.get("onboarding_indice") == 1

    # Verificar que foi marcado como migrado
    assert novo_doc.get("migrado_de_legacy") == True
    assert novo_doc.get("migrado_em") is not None

    # Verificar que passou na validação
    valido, motivo = validar_documento_onboarding_isolado(novo_doc)
    assert valido, f"Documento convertido é inválido: {motivo}"

    print(f"✅ T6: Conversão de legacy para isolado funciona corretamente")


# ==============================================================================
# T7: FIRESTORE REAL — WRITE/READ/CLEANUP
# ==============================================================================

@pytest.mark.firestore_real
def test_firestore_write_read_cleanup(db, tenant_teste, actor_teste_1):
    """
    Testa escrita e leitura no caminho novo usando Firestore REAL.

    IMPORTANTE:
    - Usa tenant de teste (não produção)
    - Faz cleanup automático
    - Valida isolamento estrutural
    """

    # Criar documento
    doc = criar_documento_onboarding_isolado(tenant_teste, actor_teste_1, "Teste", "teste@...")

    # Validar documento antes de escrever
    valido, motivo = validar_documento_onboarding_isolado(doc)
    assert valido, f"Documento inválido: {motivo}"

    # Obter referência
    ref = obter_ref_onboarding_isolado(db, tenant_teste, actor_teste_1)

    # ===== ESCREVER =====
    try:
        ref.set(doc)
        print(f"   Documento escrito em {ref.path}")
    except Exception as e:
        pytest.fail(f"Falha ao escrever: {e}")

    # ===== LER =====
    try:
        snapshot = ref.get()
    except Exception as e:
        pytest.fail(f"Falha ao ler: {e}")

    assert snapshot.exists, f"Documento não foi escrito: {ref.path}"

    # ===== VALIDAR DADOS =====
    dados_lidos = snapshot.to_dict()
    assert dados_lidos.get("actor_id") == actor_teste_1, "actor_id mismatch"
    assert dados_lidos.get("tenant_id") == tenant_teste, "tenant_id mismatch"
    assert dados_lidos.get("onboarding_status") == "em_progresso", "Status incorrect"

    print(f"   Documento lido e validado: {dados_lidos.get('actor_id')}")

    # ===== CLEANUP (deletar documento de teste) =====
    try:
        ref.delete()
        print(f"   Documento deletado")
    except Exception as e:
        pytest.fail(f"Falha ao deletar: {e}")

    # ===== VERIFICAR CLEANUP =====
    snapshot_pos = ref.get()
    assert not snapshot_pos.exists, "Cleanup falhou — documento ainda existe"

    print(f"✅ T7: Firestore real (write/read/cleanup) funciona corretamente")


# ==============================================================================
# T8: VALIDAÇÃO DE OWNERSHIP
# ==============================================================================

def test_validacao_ownership(tenant_teste, actor_teste_1):
    """
    Verifica que criado_por deve ser igual a actor_id.
    """

    # Criar documento válido
    doc_valido = criar_documento_onboarding_isolado(tenant_teste, actor_teste_1, "N", "e@...")

    valido, _ = validar_documento_onboarding_isolado(doc_valido)
    assert valido, "Documento com ownership correto deve ser válido"

    # Criar documento com ownership incorreto
    doc_invalido = doc_valido.copy()
    doc_invalido["criado_por"] = "outro_actor"

    valido, motivo = validar_documento_onboarding_isolado(doc_invalido)
    assert not valido, "Documento com ownership incorreto deveria ser rejeitado"
    assert "criado_por" in motivo, f"Motivo deve mencionar criado_por: {motivo}"

    print(f"✅ T8: Validação de ownership funciona corretamente")


# ==============================================================================
# T9: ETAPAS VÁLIDAS
# ==============================================================================

def test_etapas_validas(tenant_teste, actor_teste_1):
    """
    Verifica que apenas etapas pré-definidas são aceitas.
    """

    # Testar cada etapa válida
    for etapa in ETAPAS_ONBOARDING:
        doc = criar_documento_onboarding_isolado(tenant_teste, actor_teste_1, "N", "e@...")
        doc["onboarding_etapa_atual"] = etapa

        valido, motivo = validar_documento_onboarding_isolado(doc)
        assert valido, f"Etapa válida foi rejeitada: {etapa} — {motivo}"

    # Testar etapa inválida
    doc = criar_documento_onboarding_isolado(tenant_teste, actor_teste_1, "N", "e@...")
    doc["onboarding_etapa_atual"] = "etapa_invalida"

    valido, motivo = validar_documento_onboarding_isolado(doc)
    assert not valido, "Etapa inválida deveria ser rejeitada"

    print(f"✅ T9: Etapas válidas são respeitadas")


# ==============================================================================
# T10: IMUTABILIDADE PARCIAL (criado_em, criado_por)
# ==============================================================================

def test_imutabilidade_criacao(tenant_teste, actor_teste_1):
    """
    Verifica que criado_em e criado_por não mudam após criação.
    """

    doc = criar_documento_onboarding_isolado(tenant_teste, actor_teste_1, "N", "e@...")
    criado_em_original = doc.get("criado_em")
    criado_por_original = doc.get("criado_por")

    # Simular tentativa de alterar
    doc["criado_em"] = "2025-01-01T00:00:00Z"  # Alterar
    doc["criado_por"] = "outro_ator"  # Alterar

    # Validação deveria rejeitar porque criado_por != actor_id
    valido, motivo = validar_documento_onboarding_isolado(doc)
    assert not valido, "Documento com criado_por alterado deveria ser rejeitado"

    print(f"✅ T10: Imutabilidade de criação é validada")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
