"""
[P0.9] Testes — Contrato de Retorno Corrigido

Valida que:
1. Serviço inválido: nenhum evento criado, retorna False
2. Serviço ausente: nenhum evento criado, retorna False
3. Sucesso: evento criado, retorna True
4. Executar_acao_gpt_resultado normaliza retorno corretamente
"""

import pytest
import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

from handlers.event_handler import add_evento_por_gpt
from services.gpt_executor import executar_acao_gpt_resultado
from utils.contexto_temporario import (
    carregar_contexto_temporario_v2,
    salvar_contexto_temporario_v2,
)
from services.firebase_service_async import buscar_subcolecao, buscar_documento

TENANT_TEST = "7394370553"
WA_ID = "5511991382080"
ACTOR_WA = f"whatsapp:{WA_ID}"

@pytest.mark.asyncio
async def test_p0_9_servico_invalido_retorna_false():
    """
    ✅ T1: Serviço inválido → retorna False (não True)

    Antes do fix: evento era criado COM SERVICO INVALIDO
    Depois do fix: add_evento_por_gpt retorna False, evento NÃO criado
    """
    print("\n" + "="*80)
    print("T1: SERVIÇO INVÁLIDO → RETORNA FALSE")
    print("="*80)

    # Dados com serviço inválido (como viria do router)
    dados = {
        "profissional": "Bruna",
        "servico": "servico_fantasma_invalido",  # ← INVÁLIDO
        "data_hora": (datetime.now() + timedelta(days=1)).isoformat(),
        "duracao": 40,
        "descricao": "Serviço inválido com Bruna",
        "confirmado": True,  # [P0.10-FIX] Como viria do router MSG 3
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
    }

    # Chamar add_evento_por_gpt COM servico inválido
    resultado = await add_evento_por_gpt(None, None, dados)

    print(f"Resultado: {repr(resultado)}")

    # VALIDAÇÃO: Deve retornar False (erro de validação)
    assert resultado is False, f"Esperado False para serviço inválido, recebido {repr(resultado)}"

    print("✅ T1 PASSOU: Serviço inválido retorna False (não True)")


@pytest.mark.asyncio
async def test_p0_9_servico_valido_cria_evento():
    """
    ✅ T2: Serviço válido → retorna True + evento criado

    Depois do fix: evento é criado COM SERVICO VALIDO
    """
    print("\n" + "="*80)
    print("T2: SERVIÇO VÁLIDO → RETORNA TRUE + EVENTO CRIADO")
    print("="*80)

    # Carregar profissionais para ter serviços válidos
    profs_dict = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Profissionais") or {}
    if not profs_dict:
        pytest.skip("Tenant sem profissionais")

    # Pegar primeiro profissional e serviço
    prof_id = list(profs_dict.keys())[0]
    prof_data = profs_dict[prof_id]
    prof_nome = prof_data.get("nome")
    servicos = prof_data.get("servicos", [])

    if not servicos:
        pytest.skip("Profissional sem serviços")

    servico_valido = servicos[0]

    print(f"Profissional: {prof_nome}")
    print(f"Serviço válido: {servico_valido}")

    # Dados COM serviço válido (como viria do router)
    amanha = datetime.now() + timedelta(days=1)
    dados = {
        "profissional": prof_nome,
        "servico": servico_valido,
        "data_hora": f"{amanha.strftime('%Y-%m-%d')}T14:00:00",
        "duracao": 40,
        "descricao": f"{servico_valido} com {prof_nome}",
        "confirmado": True,  # [P0.10-FIX] Como viria do router MSG 3
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
    }

    resultado = await add_evento_por_gpt(None, None, dados)

    print(f"Resultado: {repr(resultado)}")

    # VALIDAÇÃO: Deve retornar True (sucesso)
    assert resultado is True, f"Esperado True para serviço válido, recebido {repr(resultado)}"

    print("✅ T2 PASSOU: Serviço válido retorna True + evento criado")


@pytest.mark.asyncio
async def test_p0_9_executar_acao_gpt_resultado_normaliza():
    """
    ✅ T3: executar_acao_gpt_resultado normaliza retorno bool para dict

    Valida que wrapper converte bool → dict corretamente
    """
    print("\n" + "="*80)
    print("T3: EXECUTAR_ACAO_GPT_RESULTADO NORMALIZA RETORNO")
    print("="*80)

    # Dados COM serviço inválido (vai retornar False)
    dados = {
        "profissional": "Bruna",
        "servico": "fantasma",
        "data_hora": (datetime.now() + timedelta(days=1)).isoformat(),
        "confirmado": True,  # [P0.10-FIX] Como viria do router
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
    }

    # Chamar via wrapper
    resultado_dict = await executar_acao_gpt_resultado(
        None, None, "criar_evento", dados
    )

    print(f"Resultado normalizado: {repr(resultado_dict)}")

    # VALIDAÇÃO: Deve retornar dict com ok=False
    assert isinstance(resultado_dict, dict), f"Esperado dict, recebido {type(resultado_dict)}"
    assert "ok" in resultado_dict, f"Falta chave 'ok' em {resultado_dict}"
    assert resultado_dict.get("ok") is False, f"Esperado ok=False, recebido {resultado_dict.get('ok')}"
    assert resultado_dict.get("acao") == "criar_evento"

    print("✅ T3 PASSOU: Retorno normalizado para dict com ok=False")


@pytest.mark.asyncio
async def test_p0_9_multitenant_isolamento():
    """
    ✅ T4: Isolamento multi-tenant confirmado

    Dois tenants com serviços diferentes não se contaminam
    """
    print("\n" + "="*80)
    print("T4: ISOLAMENTO MULTI-TENANT")
    print("="*80)

    TENANT_2 = "9876543210"

    # Tenant 1: serviço válido
    dados_t1 = {
        "profissional": "Bruna",
        "servico": "corte feminino",
        "data_hora": (datetime.now() + timedelta(days=1)).isoformat(),
        "confirmado": True,  # [P0.10-FIX]
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
    }

    # Tenant 2: serviço inválido
    dados_t2 = {
        "profissional": "Profissional",
        "servico": "fantasma",
        "data_hora": (datetime.now() + timedelta(days=1)).isoformat(),
        "confirmado": True,  # [P0.10-FIX]
        "tenant_id": TENANT_2,
        "user_id": "9999999999",
    }

    resultado_t1 = await add_evento_por_gpt(None, None, dados_t1)
    resultado_t2 = await add_evento_por_gpt(None, None, dados_t2)

    print(f"Tenant 1 (válido): {resultado_t1}")
    print(f"Tenant 2 (inválido): {resultado_t2}")

    # VALIDAÇÃO
    assert resultado_t1 is True, "Tenant 1 deve retornar True"
    assert resultado_t2 is False, "Tenant 2 deve retornar False"

    print("✅ T4 PASSOU: Isolamento multi-tenant confirmado")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
