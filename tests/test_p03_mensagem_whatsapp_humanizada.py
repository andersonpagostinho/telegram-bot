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
    """

    print("\n" + "="*80)
    print("[P0.3 TESTE] montar_mensagem_confirmacao_sucesso()")
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

    # Validacao
    print(f"\n[VALIDACAO]")
    print("-" * 80)

    # Indicadores de humanizacao
    tem_pronto = "Pronto" in mensagem
    tem_agendada = "agendad" in mensagem.lower()
    tem_ficou = "ficou" in mensagem.lower()
    tem_profissional = profissional in mensagem
    tem_servico = servico.lower() in mensagem.lower()

    print(f"  'Pronto': {tem_pronto}")
    print(f"  'agendad': {tem_agendada}")
    print(f"  'ficou': {tem_ficou}")
    print(f"  Profissional ({profissional}): {tem_profissional}")
    print(f"  Servico ({servico}): {tem_servico}")

    # Validacao critica
    assert tem_pronto, f"Mensagem nao contem 'Pronto': {repr(mensagem)}"
    assert tem_agendada or tem_ficou, f"Mensagem nao contem 'agendad' ou 'ficou': {repr(mensagem)}"
    assert tem_profissional, f"Mensagem nao contem profissional ({profissional}): {repr(mensagem)}"
    assert tem_servico, f"Mensagem nao contem servico ({servico}): {repr(mensagem)}"

    print(f"\n[RESULTADO]")
    print(f"  Status: PASSOU")
    print(f"  Mensagem eh humanizada")
    print(f"  Contem: 'Pronto', 'agendada', profissional e servico")

    print(f"\n" + "="*80)
    print(f"[SUMMARY]")
    print(f"  Status: PASSOU")
    print(f"  Mensagem: {repr(mensagem)}")
    print("="*80)
