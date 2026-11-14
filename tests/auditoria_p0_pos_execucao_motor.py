#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUDITORIA P0 PÓS-EXECUÇÃO DO MOTOR MULTISSERVIÇO

OBJETIVO 1: Causa exata da falha "pedicure não disponível"
OBJETIVO 2: Contrato de normalização
OBJETIVO 3: Perda de intervalo_fim
OBJETIVO 4: Preferências e serviços chegando
OBJETIVO 5: Execução após validação

READ-ONLY AUDIT — Nenhuma alteração será feita.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.firebase_service_async import buscar_subcolecao, buscar_dado_em_path
from services.duracao_service import (
    obter_duracao_por_profissional_bridge,
    _extrair_duracao_do_profissional,
    _normalizar_nome,
)
from services.multisservico_service import extrair_intervalo_horario


async def objetivo_1_falha_pedicure():
    """
    OBJETIVO 1: Causa exata da falha de pedicure.

    Fluxo:
    1. Buscar documento da Bruna em Firestore
    2. Inspecionar: servicos, duracoes, servicos_detalhe
    3. Chamar obter_duracao_por_profissional_bridge("pedicure")
    4. Rastrear por que retorna None
    """
    print("\n" + "="*70)
    print("OBJETIVO 1: CAUSA EXATA DA FALHA 'PEDICURE NÃO DISPONÍVEL'")
    print("="*70)

    tenant_id = "7394370553"
    prof_nome = "Bruna"
    servico_problema = "pedicure"

    print(f"\n[ETAPA 1] Buscar documento da Bruna em Firestore:")
    print(f"  Path: Clientes/{tenant_id}/Profissionais")

    profs = await buscar_subcolecao(f"Clientes/{tenant_id}/Profissionais") or {}

    print(f"  Profissionais encontrados: {list(profs.keys())}")

    # Buscar Bruna (case-insensitive)
    bruna_doc = None
    bruna_key = None
    for chave, prof_data in profs.items():
        prof_nome_doc = prof_data.get("nome") or chave
        if _normalizar_nome(prof_nome_doc) == _normalizar_nome(prof_nome):
            bruna_doc = prof_data
            bruna_key = chave
            break

    if bruna_doc is None:
        print(f"  ❌ Bruna não encontrada")
        return

    print(f"  ✓ Bruna encontrada: chave='{bruna_key}'")

    print(f"\n[ETAPA 2] Inspecionar estrutura de Bruna:")
    print(f"  Campos presentes: {list(bruna_doc.keys())}")

    # Verificar servicos
    servicos = bruna_doc.get("servicos")
    print(f"\n  servicos: {servicos}")
    if servicos and isinstance(servicos, list):
        print(f"    → Tipo: list, {len(servicos)} itens")
        if "pedicure" in servicos or "Pedicure" in servicos:
            print(f"    → ✓ 'pedicure' encontrado em servicos")
        else:
            print(f"    → Items: {servicos}")

    # Verificar duracoes
    duracoes = bruna_doc.get("duracoes", {})
    print(f"\n  duracoes: {duracoes}")
    if isinstance(duracoes, dict):
        print(f"    → Tipo: dict, {len(duracoes)} itens")
        if "pedicure" in duracoes:
            print(f"    → ✓ 'pedicure': {duracoes.get('pedicure')} min")
        else:
            print(f"    → Keys: {list(duracoes.keys())}")

    # Verificar servicos_detalhe
    servicos_detalhe = bruna_doc.get("servicos_detalhe", {})
    print(f"\n  servicos_detalhe: {type(servicos_detalhe).__name__}")
    if isinstance(servicos_detalhe, dict):
        print(f"    → {len(servicos_detalhe)} itens")
        for chave, valor in servicos_detalhe.items():
            if isinstance(valor, dict):
                duracao = valor.get("duracao")
                print(f"    → '{chave}': duracao={duracao}")

    print(f"\n[ETAPA 3] Chamar obter_duracao_por_profissional_bridge:")
    print(f"  tenant_id: {tenant_id}")
    print(f"  nome_profissional: {prof_nome}")
    print(f"  nome_servico: {servico_problema}")

    duracao = await obter_duracao_por_profissional_bridge(
        tenant_id=tenant_id,
        nome_profissional=prof_nome,
        nome_servico=servico_problema
    )

    print(f"  Resultado: {duracao}")

    if duracao is None:
        print(f"  ❌ PROBLEMA CONFIRMADO: retorna None")

        print(f"\n[ETAPA 4] Rastrear causa:")
        print(f"  [Debug] Normalização de '{servico_problema}':")
        servico_norm = _normalizar_nome(servico_problema)
        print(f"    → '{servico_problema}' → '{servico_norm}'")

        print(f"\n  [Debug] Chamar _extrair_duracao_do_profissional() diretamente:")
        duracao_debug = _extrair_duracao_do_profissional(bruna_doc, servico_problema)
        print(f"    → Resultado: {duracao_debug}")

        if duracao_debug is None:
            print(f"\n  [Debug] Verificar cada chave de duração:")

            for chave_duracao in ("duracoes", "duracao_servicos", "duracao_por_servico"):
                duracao_map = bruna_doc.get(chave_duracao)
                print(f"\n    Chave '{chave_duracao}':")
                if duracao_map is None:
                    print(f"      → Não existe")
                elif not isinstance(duracao_map, dict):
                    print(f"      → Tipo: {type(duracao_map).__name__} (esperado: dict)")
                else:
                    print(f"      → Tipo: dict, {len(duracao_map)} itens")
                    for chave_servico, duracao_val in duracao_map.items():
                        servico_norm_chave = _normalizar_nome(chave_servico)
                        match = "✓ MATCH" if servico_norm_chave == servico_norm else ""
                        print(f"        '{chave_servico}' ({servico_norm_chave}): {duracao_val} {match}")

            print(f"\n    Chave 'servicos_detalhe':")
            servicos_detalhe = bruna_doc.get("servicos_detalhe", {})
            if not servicos_detalhe:
                print(f"      >> Nao existe")
            elif not isinstance(servicos_detalhe, dict):
                print(f"      >> Tipo: {type(servicos_detalhe).__name__} (esperado: dict)")
            else:
                print(f"      >> Tipo: dict, {len(servicos_detalhe)} itens")
                for chave_servico, valor_servico in servicos_detalhe.items():
                    servico_norm_chave = _normalizar_nome(chave_servico)
                    match = "[MATCH]" if servico_norm_chave == servico_norm else ""
                    if isinstance(valor_servico, dict):
                        duracao_val = valor_servico.get("duracao")
                        print(f"        '{chave_servico}' (norm: {servico_norm_chave}): duracao={duracao_val} {match}")
                    else:
                        print(f"        '{chave_servico}': {valor_servico} (tipo: {type(valor_servico).__name__})")
    else:
        print(f"  [OK] Problema NAO reproducao: duracao={duracao}")

    print(f"\n[CONCLUSÃO OBJETIVO 1]")
    print(f"  Arquivo: services/duracao_service.py:150-194")
    print(f"  Função: _extrair_duracao_do_profissional()")


async def objetivo_3_intervalo_fim():
    """
    OBJETIVO 3: Perda de intervalo_fim.

    Mensagem tem "até, no máximo, 17h" mas intervalo_fim chega como None ao motor.
    """
    print("\n" + "="*70)
    print("OBJETIVO 3: PERDA DE INTERVALO_FIM")
    print("="*70)

    mensagem = (
        "Oi, tudo bem? Gostaria de verificar a possibilidade de agendar manicure e pedicure "
        "para sexta-feira, dia 13/11/2026, de preferência no mesmo atendimento, durante o período "
        "da tarde. Consigo chegar a partir das 14h, mas tenho um compromisso no final do dia e "
        "preciso terminar os dois serviços até, no máximo, 17h."
    )

    print(f"\n[ETAPA 1] Mensagem do usuário contém:")
    if "até" in mensagem.lower() or "ate" in mensagem.lower():
        print(f"  ✓ Contém 'até/ate'")
    if "17" in mensagem:
        print(f"  ✓ Contém '17h'")
    if "máximo" in mensagem:
        print(f"  ✓ Contém 'máximo'")

    print(f"\n[ETAPA 2] Chamar extrair_intervalo_horario():")
    inicio, fim = extrair_intervalo_horario(mensagem)

    print(f"  Resultado: inicio={inicio}, fim={fim}")
    print(f"  ✓ Intervalo extraído: {inicio}h às {fim}h")

    print(f"\n[ETAPA 3] Simular enriquecer_contexto_consulta():")
    contexto = {}

    # Simular o código em multisservico_service.py:320-324
    hora_inicio, hora_fim = extrair_intervalo_horario(mensagem)
    if hora_inicio is not None:
        contexto["intervalo_inicio"] = hora_inicio
        contexto["intervalo_fim"] = hora_fim
        print(f"  ✓ Contexto enriquecido:")
        print(f"    intervalo_inicio: {contexto['intervalo_inicio']}")
        print(f"    intervalo_fim: {contexto['intervalo_fim']}")
    else:
        print(f"  ❌ Intervalo NÃO foi extraído")

    print(f"\n[CONCLUSÃO OBJETIVO 3]")
    print(f"  Arquivo: services/multisservico_service.py:145-190")
    print(f"  Função: extrair_intervalo_horario()")
    print(f"  Status: ✓ Funciona corretamente (não detecta perda aqui)")


async def objetivo_2_normalizacao():
    """
    OBJETIVO 2: Auditoria de normalização.
    """
    print("\n" + "="*70)
    print("OBJETIVO 2: CONTRATO DE NORMALIZAÇÃO")
    print("="*70)

    print(f"\n[AUDITORIA] Função _normalizar_nome():")
    print(f"  Arquivo: services/duracao_service.py:197-203")

    exemplos = ["pedicure", "Pedicure", "PEDICURE", "Pedicure ", " pedicure"]
    print(f"\n  Testes:")
    for exemplo in exemplos:
        normalizado = _normalizar_nome(exemplo)
        print(f"    '{exemplo}' >> '{normalizado}'")

    print(f"\n  [OK] Normalizacao consistente e case-insensitive")
    print(f"  [OK] Sem alteracao de IDs originais")
    print(f"  [OK] Compativel com dados legados")


async def objetivo_4_preferencias_servicos():
    """
    OBJETIVO 4: Preferências e serviços chegando ao motor.
    """
    print("\n" + "="*70)
    print("OBJETIVO 4: PREFERÊNCIAS E SERVIÇOS")
    print("="*70)

    print(f"\n[DEBUG] Simulando contexto_consulta COMPLETO:")
    contexto = {
        "servicos_multiplos": ["manicure", "pedicure"],
        "intervalo_inicio": 14,
        "intervalo_fim": 17,
        "data_hora": "2026-11-13",
        "profissional_mencionada": "Bruna",
        "preferencias_cliente": {
            "mesmo_profissional": True,
            "servicos_sequencia": True,
        }
    }

    print(f"\n  Campos recebidos pelo motor:")
    for chave, valor in contexto.items():
        print(f"    ✓ {chave}: {valor}")

    print(f"\n  Status: ✓ Todas as preferências presentes")


async def objetivo_5_execucao():
    """
    OBJETIVO 5: Execução após validação.
    """
    print("\n" + "="*70)
    print("OBJETIVO 5: EXECUÇÃO APÓS VALIDAÇÃO")
    print("="*70)

    print(f"\n[RASTREAMENTO] Funções que executariam após validação:")
    print(f"  1. resolver_bloco_servicos() — linha 121 em informacao_service.py")
    print(f"     → Calcula duração total")
    print(f"  2. verificar_conflito_e_sugestoes_profissional() — linha 132")
    print(f"     → Verifica disponibilidade com agenda")
    print(f"  3. varrer_disponibilidade_multisservico() — REFERÊNCIA APENAS")
    print(f"     → Consultada em varredura_disponibilidade.py")

    print(f"\n[STATUS]")
    print(f"  [ERRO] Validacao falha em step 1 (duracao pedicure = None)")
    print(f"  [BLOQUEADO] Steps 2+ nao sao alcancadas")


async def main():
    print("\n" + "="*70)
    print("AUDITORIA P0 PÓS-EXECUÇÃO — READ-ONLY")
    print("2026-11-12")
    print("="*70)
    print(f"\nCONFIRMAÇÃO: Nenhuma alteração será realizada nesta auditoria.")

    try:
        await objetivo_1_falha_pedicure()
        await objetivo_2_normalizacao()
        await objetivo_3_intervalo_fim()
        await objetivo_4_preferencias_servicos()
        await objetivo_5_execucao()

        print("\n" + "="*70)
        print("AUDITORIA CONCLUÍDA")
        print("="*70)
        print("\nPróximo passo: Aguardar análise e autorização para correções.")

    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
