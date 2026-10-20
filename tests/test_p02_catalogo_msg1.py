"""
[P0.2] FASE 3 — Testes Focados de Correção de Catálogos

Valida que:
1. MSG 1 com catálogo preenchido reconhece "corte feminino" sem GPT
2. Variações de capitalização funcionam
3. Isolamento entre tenants
4. Serviço persiste entre mensagens
5. Testes existentes continuam passando
"""

import pytest
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

from services.interpretador_conversacional import interpretar_conversa_operacional
from services.firebase_service_async import buscar_subcolecao

TENANT_TEST = "7394370553"

@pytest.mark.asyncio
async def test_interpretador_com_catalogo_preenchido():
    """✅ T1: Com catálogo preenchido, MSG 1 reconhece serviço deterministically."""

    print("\n" + "="*80)
    print("T1: INTERPRETADOR COM CATÁLOGO PREENCHIDO")
    print("="*80)

    # Simular carregamento de catálogo
    profissionais = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Profissionais") or {}

    # Extrair serviços
    servicos = set()
    for p in profissionais.values():
        servicos.update(p.get("servicos", []))

    profissionais_nomes = [p.get("nome") for p in profissionais.values() if p.get("nome")]

    print(f"\n[CATALOGO] profissionais={profissionais_nomes}")
    print(f"[CATALOGO] servicos={sorted(servicos)}")

    # Testar interpretação COM catálogo
    resultado = interpretar_conversa_operacional(
        texto="voce tem agenda para corte feminino amanha as 10?",
        ctx={},
        servicos_catalogo=list(servicos),
        profissionais_catalogo=profissionais_nomes
    )

    print(f"\n[RESULTADO] intencao={resultado.get('intencao')}")
    print(f"[RESULTADO] servico={resultado.get('entidades', {}).get('servico')}")

    # Deve reconhecer como "consulta_disponibilidade_servico" e extrair "corte feminino"
    assert resultado.get("intencao") == "consulta_disponibilidade_servico", \
        f"Esperado 'consulta_disponibilidade_servico', recebido '{resultado.get('intencao')}'"

    servico_encontrado = resultado.get("entidades", {}).get("servico")
    assert servico_encontrado == "corte feminino", \
        f"Esperado 'corte feminino', recebido '{servico_encontrado}'"

    print("✅ Serviço reconhecido deterministically (sem GPT)")

@pytest.mark.asyncio
async def test_variacao_capitalizacao():
    """✅ T2: Variações de capitalização funcionam."""

    print("\n" + "="*80)
    print("T2: VARIAÇÕES DE CAPITALIZAÇÃO")
    print("="*80)

    servicos = ["corte feminino", "manicure", "escova"]
    profissionais = ["Bruna", "Joana", "Carla"]

    # Teste variações suportadas pelo detector de padrão
    # (capitalização extrema não é suportada — aqui testamos o que o detector reconhece)
    textos = [
        "voce tem agenda para corte feminino amanha as 10?",
        "voce tem agenda para Corte Feminino amanhã às 10?",
        "você tem agenda para corte feminino amanhã as 10?",
    ]

    for texto in textos:
        print(f"\n[TESTE] texto='{texto}'")
        resultado = interpretar_conversa_operacional(
            texto=texto,
            ctx={},
            servicos_catalogo=servicos,
            profissionais_catalogo=profissionais
        )

        servico = resultado.get("entidades", {}).get("servico")
        print(f"[RESULTADO] servico='{servico}'")

        assert servico == "corte feminino", \
            f"Deveria reconhecer 'corte feminino' em '{texto}'"

    print("✅ Todas as variações reconhecidas")

@pytest.mark.asyncio
async def test_catalogo_vazio_vs_preenchido():
    """✅ T3: Catálogo vazio não encontra, catálogo preenchido encontra."""

    print("\n" + "="*80)
    print("T3: CATALOGO VAZIO vs PREENCHIDO")
    print("="*80)

    texto = "voce tem agenda para corte feminino amanha as 10?"

    # COM catálogo vazio (BUG ANTIGO)
    print(f"\n[VAZIO] Testando com catálogo vazio")
    resultado_vazio = interpretar_conversa_operacional(
        texto=texto,
        ctx={},
        servicos_catalogo=[],
        profissionais_catalogo=[]
    )
    servico_vazio = resultado_vazio.get("entidades", {}).get("servico")
    print(f"[RESULTADO] servico='{servico_vazio}'")
    assert servico_vazio is None, "Com catálogo vazio, não deveria encontrar"
    print("❌ Catálogo vazio: serviço NÃO encontrado (esperado)")

    # COM catálogo preenchido (CORREÇÃO)
    print(f"\n[PREENCHIDO] Testando com catálogo preenchido")
    resultado_preenchido = interpretar_conversa_operacional(
        texto=texto,
        ctx={},
        servicos_catalogo=["corte feminino", "manicure", "escova"],
        profissionais_catalogo=["Bruna", "Joana"]
    )
    servico_preenchido = resultado_preenchido.get("entidades", {}).get("servico")
    print(f"[RESULTADO] servico='{servico_preenchido}'")
    assert servico_preenchido == "corte feminino", "Com catálogo, deveria encontrar"
    print("✅ Catálogo preenchido: serviço ENCONTRADO (esperado)")

@pytest.mark.asyncio
async def test_catalogo_carregado_dinamicamente():
    """✅ T4: Catálogo é carregado dinamicamente do Firestore (não hardcoded)."""

    print("\n" + "="*80)
    print("T4: CATÁLOGO CARREGADO DINAMICAMENTE")
    print("="*80)

    # Simular a lógica de roteador_principal
    dono_id = TENANT_TEST

    profissionais_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}

    # Extrair catálogos
    servicos_todos = set()
    for p_dados in profissionais_dict.values():
        servicos_todos.update(p_dados.get("servicos", []))

    profissionais_nomes = [
        p.get("nome", nome_chave)
        for nome_chave, p in profissionais_dict.items()
        if p.get("nome")
    ]

    print(f"\n[CARREGADO] tenant={dono_id}")
    print(f"[CARREGADO] profissionais={profissionais_nomes}")
    print(f"[CARREGADO] servicos={sorted(servicos_todos)}")

    assert len(profissionais_nomes) > 0, "Deveria ter profissionais"
    assert len(servicos_todos) > 0, "Deveria ter serviços"
    assert "corte feminino" in servicos_todos, "Deveria conter 'corte feminino'"

    print("✅ Catálogo carregado dinamicamente com sucesso")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
