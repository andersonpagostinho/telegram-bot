#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0.3 — Teste de Mensagem WhatsApp Humanizada

Objetivo:
Validar que montar_mensagem_confirmacao_sucesso() produz mensagem humanizada.

Cenario:
- servico=corte
- profissional=Bruna
- data_hora=2026-10-05T09:00:00

Validacao:
Mensagem deve conter "Pronto" + "agendad" + profissional + servico
NAO deve ser apenas data/hora tecnica minimalista.
"""

import pytest
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.mensagens_agendamento import montar_mensagem_confirmacao_sucesso


def test_p03_montar_mensagem_confirmacao_sucesso_humanizada():
    """
    P0.3 — Validar que montar_mensagem_confirmacao_sucesso() produz mensagem humanizada.
    P0.7 — Validar conformidade com padrão oficial.
    """

    print("\n" + "="*80)
    print("[P0.3/P0.7 TESTE] montar_mensagem_confirmacao_sucesso()")
    print("="*80)

    servico = "corte"
    profissional = "Bruna"
    data_hora = "2026-10-05T09:00:00"

    print(f"\n[INPUT]")
    print(f"  servico: {servico}")
    print(f"  profissional: {profissional}")
    print(f"  data_hora: {data_hora}")

    # Chamar a funcao
    mensagem = montar_mensagem_confirmacao_sucesso(servico, profissional, data_hora)

    print(f"\n[MENSAGEM GERADA]")
    print(f"  {repr(mensagem)}")

    # P0.7: Validacao de padrão oficial
    print(f"\n[VALIDACAO P0.7 — PADRÃO OFICIAL]")
    print("-" * 80)

    # Padrão oficial esperado (de docs/roadmap/FEATURE_ENCAIXE_LISTA_ESPERA.md:94,415)
    # "Pronto! Seu horário de {servico} com {profissional} está confirmado para {quando} às {hora}."

    # Validar elementos obrigatórios do padrão
    tem_pronto_exclamacao = "Pronto!" in mensagem
    tem_seu_horario = "Seu horário de" in mensagem
    tem_profissional = profissional in mensagem
    tem_esta_confirmado = "está confirmado" in mensagem
    tem_servico = servico.lower() in mensagem.lower()

    print(f"  ✓ 'Pronto!' (com exclamação): {tem_pronto_exclamacao}")
    print(f"  ✓ 'Seu horário de': {tem_seu_horario}")
    print(f"  ✓ 'está confirmado': {tem_esta_confirmado}")
    print(f"  ✓ Profissional '{profissional}': {tem_profissional}")
    print(f"  ✓ Serviço '{servico}': {tem_servico}")

    # Validações críticas (P0.7)
    assert tem_pronto_exclamacao, f"Deve usar 'Pronto!' (com exclamação). Recebido: {repr(mensagem)}"
    assert tem_seu_horario, f"Deve usar 'Seu horário de'. Recebido: {repr(mensagem)}"
    assert tem_esta_confirmado, f"Deve usar 'está confirmado'. Recebido: {repr(mensagem)}"
    assert tem_profissional, f"Deve conter profissional '{profissional}': {repr(mensagem)}"
    assert tem_servico, f"Deve conter serviço '{servico}': {repr(mensagem)}"

    # P0.3: Validacao de humanizacao (genérica - compatibilidade)
    print(f"\n[VALIDACAO P0.3 — HUMANIZAÇÃO]")
    print("-" * 80)

    tem_pronto = "Pronto" in mensagem
    tem_confirmado = "confirmad" in mensagem.lower()

    print(f"  ✓ Contém 'Pronto': {tem_pronto}")
    print(f"  ✓ Contém 'confirmad': {tem_confirmado}")

    assert tem_pronto, f"Mensagem deve conter 'Pronto': {repr(mensagem)}"
    assert tem_confirmado, f"Mensagem deve conter 'confirmad': {repr(mensagem)}"

    print(f"\n[RESULTADO]")
    print(f"  ✅ Status: PASSOU")
    print(f"  ✅ Conformidade com padrão oficial (P0.7)")
    print(f"  ✅ Humanização validada (P0.3)")

    print(f"\n" + "="*80)
    print(f"[SUMMARY]")
    print(f"  Status: PASSOU")
    print(f"  Padrão: Oficial")
    print(f"  Mensagem: {repr(mensagem)}")
    print("="*80)
