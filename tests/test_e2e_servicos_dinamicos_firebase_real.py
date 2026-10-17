#!/usr/bin/env python3
"""
Testes E2E com Firebase REAL para validar extração dinâmica de serviços.
Reutiliza tenant 7394370553 existente com profissionais cadastrados.
"""

import pytest
import asyncio
from firebase_admin import firestore
from services.firebase_service_async import (
    buscar_subcolecao,
)
from services.classificador_conversa import (
    classificar_intencao_conversacional,
    extrair_features_conversa,
)


@pytest.mark.asyncio
async def test_e2e_01_carrega_catalogo_real():
    """E2E 1: Carrega catálogo real do tenant do Firestore"""
    tenant_id = "7394370553"

    profs_dict = await buscar_subcolecao(f"Clientes/{tenant_id}/Profissionais") or {}

    assert profs_dict, f"Nenhum profissional encontrado para tenant {tenant_id}"

    # Construir catálogo
    catalogo_servicos = []
    for p in profs_dict.values():
        for s in (p.get("servicos") or []):
            s = str(s).strip()
            if s:
                catalogo_servicos.append(s)
    catalogo_servicos = sorted(set(catalogo_servicos))

    print(f"\n[E2E_01] Tenant: {tenant_id}")
    print(f"  Profissionais: {len(profs_dict)}")
    print(f"  Catálogo: {catalogo_servicos}")

    assert len(catalogo_servicos) > 0, "Catalogo deveria ter servicos"


@pytest.mark.asyncio
async def test_e2e_02_classifica_com_catalogo_real():
    """E2E 2: Classificacao com catalogo real retorna agendamento_direto para novo servico"""
    tenant_id = "7394370553"

    profs_dict = await buscar_subcolecao(f"Clientes/{tenant_id}/Profissionais") or {}

    catalogo_servicos = []
    for p in profs_dict.values():
        for s in (p.get("servicos") or []):
            s = str(s).strip()
            if s:
                catalogo_servicos.append(s)
    catalogo_servicos = sorted(set(catalogo_servicos))

    # Se há pelo menos 2 serviços, testar novo agendamento com serviço diferente
    if len(catalogo_servicos) >= 2:
        servico_1 = catalogo_servicos[0]
        servico_2 = catalogo_servicos[1]

        ctx = {
            "draft_agendamento": {"servico": servico_1},
            "estado_fluxo": "aguardando_data"
        }

        texto = f"quero agendar {servico_2} hoje"
        resultado = classificar_intencao_conversacional(
            texto,
            ctx,
            catalogo_servicos=catalogo_servicos
        )

        print(f"\n[E2E_02] Novo servico diferente do draft")
        print(f"  Draft: {servico_1}, Texto: {servico_2}")
        print(f"  Intenção: {resultado['intencao_conversacional']}")
        print(f"  Motivo: {resultado.get('motivo', 'N/A')}")

        assert resultado["intencao_conversacional"] == "agendamento_direto", \
            f"Esperado 'agendamento_direto', obtido {resultado['intencao_conversacional']}"
        assert resultado["features"]["servico_mencionado"] == servico_2


@pytest.mark.asyncio
async def test_e2e_03_features_com_catalogo_real():
    """E2E 3: Features extrae serviço mencionado do catálogo real"""
    tenant_id = "7394370553"

    profs_dict = await buscar_subcolecao(f"Clientes/{tenant_id}/Profissionais") or {}

    catalogo_servicos = []
    for p in profs_dict.values():
        for s in (p.get("servicos") or []):
            s = str(s).strip()
            if s:
                catalogo_servicos.append(s)
    catalogo_servicos = sorted(set(catalogo_servicos))

    if catalogo_servicos:
        servico_real = catalogo_servicos[0]

        features = extrair_features_conversa(
            f"quero {servico_real}",
            ctx={},
            catalogo_servicos=catalogo_servicos
        )

        print(f"\n[E2E_03] Extração de features com catálogo real")
        print(f"  Serviço real: {servico_real}")
        print(f"  Mencionado: {features['servico_mencionado']}")
        print(f"  tem_contexto_servico: {features['tem_contexto_servico']}")

        assert features["servico_mencionado"] == servico_real
        assert features["tem_contexto_servico"] is True


@pytest.mark.asyncio
async def test_e2e_04_isolamento_multi_tenant():
    """E2E 4: Isolamento — tenant 7394370553 não reconhece serviço de outro tenant"""
    tenant_1 = "7394370553"

    profs_dict_1 = await buscar_subcolecao(f"Clientes/{tenant_1}/Profissionais") or {}

    catalogo_1 = []
    for p in profs_dict_1.values():
        for s in (p.get("servicos") or []):
            s = str(s).strip()
            if s:
                catalogo_1.append(s)
    catalogo_1 = sorted(set(catalogo_1))

    # Criar catálogo imaginário de outro tenant (não existe no Firebase)
    catalogo_2 = ["design_sobrancelha", "micropigmentacao", "depilacao"]

    # Tentar usar serviço do catálogo 2 com catálogo 1
    resultado = classificar_intencao_conversacional(
        "quero design de sobrancelha hoje",
        ctx={},
        catalogo_servicos=catalogo_1
    )

    print(f"\n[E2E_04] Isolamento multi-tenant")
    print(f"  Catálogo tenant 1: {catalogo_1}")
    print(f"  Tentar usar: 'design de sobrancelha'")
    print(f"  Serviço mencionado: {resultado['features']['servico_mencionado']}")

    # Design de sobrancelha não está no catálogo 1, portanto não deveria ser reconhecido
    assert resultado["features"]["servico_mencionado"] is None, \
        "Serviço de outro tenant não deveria ser reconhecido"


@pytest.mark.asyncio
async def test_e2e_05_mesmo_servico_ajuste():
    """E2E 5: Mesmo serviço do draft → ajuste incremental"""
    tenant_id = "7394370553"

    profs_dict = await buscar_subcolecao(f"Clientes/{tenant_id}/Profissionais") or {}

    catalogo_servicos = []
    for p in profs_dict.values():
        for s in (p.get("servicos") or []):
            s = str(s).strip()
            if s:
                catalogo_servicos.append(s)
    catalogo_servicos = sorted(set(catalogo_servicos))

    if catalogo_servicos:
        servico = catalogo_servicos[0]

        ctx = {
            "draft_agendamento": {"servico": servico},
            "estado_fluxo": "aguardando_data"
        }

        resultado = classificar_intencao_conversacional(
            f"quero ver outro horário para {servico}",
            ctx,
            catalogo_servicos=catalogo_servicos
        )

        print(f"\n[E2E_05] Mesmo servico - ajuste")
        print(f"  Serviço: {servico}")
        print(f"  Intenção: {resultado['intencao_conversacional']}")

        assert resultado["intencao_conversacional"] == "ajuste_incremental", \
            f"Esperado 'ajuste_incremental', obtido {resultado['intencao_conversacional']}"


@pytest.mark.asyncio
async def test_e2e_06_profs_carregados_uma_vez():
    """E2E 6: Validar que profs_dict é carregado (simular chamada em principal_router)"""
    tenant_id = "7394370553"
    dono_id = tenant_id

    # Simular carregamento em principal_router linha 4442
    profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}

    catalogo_servicos = []
    for p in profs_dict.values():
        for s in (p.get("servicos") or []):
            s = str(s).strip()
            if s:
                catalogo_servicos.append(s)
    catalogo_servicos = sorted(set(catalogo_servicos))

    print(f"\n[E2E_06] Carregamento simulado em principal_router")
    print(f"  profs_dict carregado: {len(profs_dict)} profissionais")
    print(f"  catalogo_servicos construído: {len(catalogo_servicos)} serviços")
    print(f"  Catálogo: {catalogo_servicos}")

    # Verificar que pode ser reutilizado
    assert len(profs_dict) > 0
    assert len(catalogo_servicos) > 0

    # Simular reuso em interceptos (linha ~7154 no código)
    for s in catalogo_servicos:
        assert isinstance(s, str), f"Serviço deveria ser string, obtido {type(s)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
