#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUDITORIA READ-ONLY — REGRESSAO EM PRODUCAO 2026-11-12 22:12:12

BLOQUEADOR 1: intervalo_fim = 14 (deveria ser 17)
BLOQUEADOR 2: pedicure retorna None

Objetivo: Rastrear a ORIGEM EXATA do valor 14 em intervalo_fim
e por que pedicure nao e encontrada apesar de existir no Firestore.

READ-ONLY: Nenhuma alteracao sera realizada.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.multisservico_service import extrair_intervalo_horario, enriquecer_contexto_consulta
from services.duracao_service import obter_duracao_por_profissional_bridge, _normalizar_nome, _extrair_duracao_do_profissional
from services.firebase_service_async import buscar_subcolecao
import asyncio


def bloqueador_1_intervalo_fim():
    """BLOQUEADOR 1: Rastrear origem do intervalo_fim=14"""

    print("\n" + "="*70)
    print("BLOQUEADOR 1: intervalo_fim = 14 (REGRESSAO)")
    print("="*70)

    # Mensagem real
    msg = (
        "Gostaria de agendar manicure e pedicure para sexta-feira, dia 13/11/2026, "
        "a partir das 14h, mas preciso terminar os dois servicos ate, no maximo, 17h."
    )

    print(f"\nMENSAGEM REAL:")
    print(f"  '{msg[:80]}...'")

    # ETAPA 1: Testar extrair_intervalo_horario() atual
    print(f"\nETAPA 1: Testar extrair_intervalo_horario()")
    inicio, fim = extrair_intervalo_horario(msg)
    print(f"  Resultado: inicio={inicio}, fim={fim}")

    if fim == 17:
        print(f"  [OK] intervalo_fim=17 correto em extrair_intervalo_horario()")
    elif fim == 14:
        print(f"  [ERRO] intervalo_fim=14 — FALHA EM EXTRACAO")
        print(f"  [DEBUG] Analisando regex...")

        # Verificar regex atual
        import re
        msg_lower = msg.lower()

        # PADRAO 1: "das X as Y" continuado
        match_p1 = re.search(
            r"(?:das?|de)?\s*(\d{1,2})(?::00|h)?\s*(?:as?|as?)\s*(\d{1,2})(?::00|h)?",
            msg_lower
        )
        print(f"    PADRAO 1 (das X as Y): {match_p1}")

        # PADRAO 2: "a partir de" + "ate" separado
        match_inicio = re.search(r"a partir d(?:e|as?)\s*(\d{1,2})(?::00|h)?", msg_lower)
        match_fim = re.search(r"(?:ate|ate)[^0-9]*?(\d{1,2})(?::00|h)?", msg_lower)
        print(f"    PADRAO 2 (a partir de + ate):")
        print(f"      inicio={match_inicio.group(1) if match_inicio else None}")
        print(f"      fim={match_fim.group(1) if match_fim else None}")

        if match_inicio and not match_fim:
            print(f"\n  [HIPOTESE] Regex 'ate' quebrada (nao encontra 17)")
        elif match_inicio and match_fim:
            print(f"\n  [HIPOTESE] Possivel fallback copying inicio para fim?")
    else:
        print(f"  [ERRO] intervalo_fim=None — NAO EXTRAIDO")

    # ETAPA 2: Testar enriquecer_contexto_consulta()
    print(f"\nETAPA 2: Testar enriquecer_contexto_consulta()")
    contexto = {}
    contexto = enriquecer_contexto_consulta(contexto, msg)
    print(f"  intervalo_inicio: {contexto.get('intervalo_inicio')}")
    print(f"  intervalo_fim: {contexto.get('intervalo_fim')}")

    if contexto.get('intervalo_fim') == 14:
        print(f"  [ERRO] Problema propagado de extrair_intervalo_horario()")

    # ETAPA 3: Verificar se ha fallback que copia inicio para fim
    print(f"\nETAPA 3: Procurar fallback que copia inicio para fim")
    import subprocess

    # Grep para fallback patterns
    try:
        # Procurar por linhas que atribuem intervalo_fim = intervalo_inicio
        result = subprocess.run(
            ["grep", "-rn", "intervalo_fim.*intervalo_inicio",
             "services/", "router/"],
            capture_output=True, text=True, cwd="C:\\dev\\neoeve"
        )

        if result.stdout:
            print(f"  ENCONTRADO:")
            for linha in result.stdout.strip().split("\n"):
                print(f"    {linha}")
        else:
            print(f"  Nao encontrado fallback direto")
    except Exception as e:
        print(f"  Erro ao procurar: {e}")

    print(f"\nCONCLUSAO BLOQUEADOR 1:")
    print(f"  Status: INVESTIGANDO")
    print(f"  Possivel origem: regex em extrair_intervalo_horario() ou fallback desconhecido")


async def bloqueador_2_pedicure_none():
    """BLOQUEADOR 2: Rastrear por que pedicure retorna None"""

    print("\n" + "="*70)
    print("BLOQUEADOR 2: pedicure retorna None (BLOQUEADO)")
    print("="*70)

    tenant_id = "7394370553"
    prof_nome = "Bruna"
    servico = "pedicure"

    # ETAPA 1: Verificar Firestore
    print(f"\nETAPA 1: Verificar documento em Firestore")
    profs = await buscar_subcolecao(f"Clientes/{tenant_id}/Profissionais") or {}

    bruna_doc = None
    for chave, prof_data in profs.items():
        prof_nome_doc = prof_data.get("nome") or chave
        if _normalizar_nome(prof_nome_doc) == _normalizar_nome(prof_nome):
            bruna_doc = prof_data
            print(f"  CHAVE FIRESTORE: {chave}")
            break

    if not bruna_doc:
        print(f"  [ERRO] Bruna nao encontrada em Firestore")
        return

    # Verificar campos
    duracoes = bruna_doc.get("duracoes", {})
    sd = bruna_doc.get("servicos_detalhe", {})

    print(f"\n  duracoes['pedicure']: {duracoes.get('pedicure')}")
    print(f"  servicos_detalhe keys: {list(sd.keys())}")
    for chave in sd.keys():
        if _normalizar_nome(chave) == _normalizar_nome(servico):
            print(f"    ENCONTRADO: '{chave}' -> duracao={sd[chave].get('duracao')}")

    # ETAPA 2: Chamar bridge
    print(f"\nETAPA 2: Chamar obter_duracao_por_profissional_bridge()")
    print(f"  tenant_id='{tenant_id}'")
    print(f"  nome_profissional='{prof_nome}'")
    print(f"  nome_servico='{servico}'")

    duracao = await obter_duracao_por_profissional_bridge(
        tenant_id=tenant_id,
        nome_profissional=prof_nome,
        nome_servico=servico
    )

    print(f"  Resultado: {duracao}")

    if duracao is None:
        print(f"\n  [ERRO] Retornou None apesar de existir no Firestore")

        # ETAPA 3: Debug _extrair_duracao_do_profissional()
        print(f"\nETAPA 3: Testar _extrair_duracao_do_profissional() diretamente")
        duracao_debug = _extrair_duracao_do_profissional(bruna_doc, servico)
        print(f"  Resultado: {duracao_debug}")

        if duracao_debug is None:
            print(f"\n  [DEBUG] Rastrear por campo:")

            # Verificar cada chave de duracao
            for chave_duracao in ("duracoes", "duracao_servicos", "duracao_por_servico"):
                duracao_map = bruna_doc.get(chave_duracao)
                print(f"\n    Chave '{chave_duracao}':")
                if duracao_map is None:
                    print(f"      NAO EXISTE")
                elif not isinstance(duracao_map, dict):
                    print(f"      TIPO ERRADO: {type(duracao_map).__name__}")
                else:
                    servico_norm = _normalizar_nome(servico)
                    for chave_servico, duracao_val in duracao_map.items():
                        chave_norm = _normalizar_nome(chave_servico)
                        match = "[MATCH]" if chave_norm == servico_norm else ""
                        print(f"      '{chave_servico}' ({chave_norm}): {duracao_val} {match}")

            # Verificar servicos_detalhe
            print(f"\n    Chave 'servicos_detalhe':")
            servico_norm = _normalizar_nome(servico)
            for chave_servico, valor in sd.items():
                chave_norm = _normalizar_nome(chave_servico)
                match = "[MATCH]" if chave_norm == servico_norm else ""
                if isinstance(valor, dict):
                    dur = valor.get("duracao")
                    print(f"      '{chave_servico}' ({chave_norm}): duracao={dur} {match}")
    else:
        print(f"\n  [OK] Pedicure encontrada com duracao={duracao}")

    # ETAPA 4: Comparar com manicure
    print(f"\nETAPA 4: Comparar com manicure")
    duracao_manicure = await obter_duracao_por_profissional_bridge(
        tenant_id=tenant_id,
        nome_profissional=prof_nome,
        nome_servico="manicure"
    )
    print(f"  manicure: {duracao_manicure}")
    print(f"  pedicure: {duracao}")

    if duracao_manicure is not None and duracao is None:
        print(f"\n  [ERRO] Tratamento DIVERGENTE entre servicos")
        print(f"  manicure funciona, pedicure nao")

    print(f"\nCONCLUSAO BLOQUEADOR 2:")
    print(f"  Status: INVESTIGANDO")
    print(f"  Possivel origem: normalizacao ou lookup divergente")


async def main():
    print("\n" + "="*70)
    print("AUDITORIA READ-ONLY — 2 BLOQUEADORES")
    print("2026-11-12 LOG PRODUCAO")
    print("="*70)

    bloqueador_1_intervalo_fim()
    await bloqueador_2_pedicure_none()

    print("\n" + "="*70)
    print("AUDITORIA CONCLUIDA")
    print("="*70)
    print("\nAguardando analise e autorizacao para proxima etapa")


if __name__ == "__main__":
    asyncio.run(main())
