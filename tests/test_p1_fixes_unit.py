#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P1 FIX — Testes unitarios (sem dependencias de router/gpt)

Cobertura:
1. extrair_data_da_mensagem() - múltiplos padrões
2. enriquecer_contexto_consulta() - com data + intervalo
3. Construcao de contexto_consulta em bloco idle
"""

import sys
import os
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.multisservico_service import (
    extrair_data_da_mensagem,
    extrair_intervalo_horario,
    enriquecer_contexto_consulta
)


def test_extrair_data_amanha():
    """Extrai 'amanha'."""
    msg = "manicure amanha"
    data = extrair_data_da_mensagem(msg)
    esperado = (date.today() + timedelta(days=1)).isoformat()
    passou = data == esperado
    print(f"[UNIT-T1] 'amanha': {data} == {esperado} : {'PASSOU' if passou else 'FALHOU'}")
    return passou


def test_extrair_data_hoje():
    """Extrai 'hoje'."""
    msg = "manicure hoje"
    data = extrair_data_da_mensagem(msg)
    esperado = date.today().isoformat()
    passou = data == esperado
    print(f"[UNIT-T2] 'hoje': {data} == {esperado} : {'PASSOU' if passou else 'FALHOU'}")
    return passou


def test_extrair_data_segunda():
    """Extrai 'segunda' (proxima segunda)."""
    msg = "manicure segunda"
    data = extrair_data_da_mensagem(msg)
    passou = data is not None and isinstance(data, str)
    print(f"[UNIT-T3] 'segunda': {data} (tipo str) : {'PASSOU' if passou else 'FALHOU'}")
    return passou


def test_extrair_data_dia_especifico():
    """Extrai 'dia 25'."""
    msg = "manicure dia 25"
    data = extrair_data_da_mensagem(msg)
    passou = data is not None and isinstance(data, str)
    print(f"[UNIT-T4] 'dia 25': {data} (tipo str) : {'PASSOU' if passou else 'FALHOU'}")
    return passou


def test_extrair_intervalo_14_17():
    """Extrai intervalo 14-17."""
    msg = "manicure das 14 as 17"
    inicio, fim = extrair_intervalo_horario(msg)
    passou = inicio == 14 and fim == 17
    print(f"[UNIT-T5] 'das 14 as 17': {inicio}-{fim} == 14-17 : {'PASSOU' if passou else 'FALHOU'}")
    return passou


def test_enriquecer_com_intervalo_e_data():
    """enriquecer_contexto_consulta() adiciona intervalo + data."""
    msg = "manicure amanha das 14 as 17"
    contexto = enriquecer_contexto_consulta({}, msg)

    passou = (
        contexto.get("intervalo_inicio") == 14
        and contexto.get("intervalo_fim") == 17
        and contexto.get("data_hora") is not None
    )

    print(f"[UNIT-T6] Enriquecimento completo:")
    print(f"  - intervalo_inicio: {contexto.get('intervalo_inicio')} (esperado: 14)")
    print(f"  - intervalo_fim: {contexto.get('intervalo_fim')} (esperado: 17)")
    print(f"  - data_hora: {contexto.get('data_hora')} (esperado: nao-vazio)")
    print(f"  Status: {'PASSOU' if passou else 'FALHOU'}")

    return passou


def test_contexto_com_multiplos_servicos():
    """Simula construcao de contexto_consulta como em principal_router.py."""
    contexto_consulta = {}

    # Simular FASE 1: multiplos servicos (sem import do router)
    servicos_multiplos = ["manicure", "pedicure"]
    if len(servicos_multiplos) > 1:
        contexto_consulta["servicos_multiplos"] = servicos_multiplos

    # FASE 2: enriquecer com intervalo + data
    msg = "manicure pedicure com bruna amanha das 14 as 17"
    contexto_consulta = enriquecer_contexto_consulta(contexto_consulta, msg)

    # FASE 3: profissional (sem classificador)
    contexto_consulta["profissional_mencionada"] = "Bruna"

    passou = (
        contexto_consulta.get("servicos_multiplos") == ["manicure", "pedicure"]
        and contexto_consulta.get("intervalo_inicio") == 14
        and contexto_consulta.get("intervalo_fim") == 17
        and contexto_consulta.get("data_hora") is not None
        and contexto_consulta.get("profissional_mencionada") == "Bruna"
    )

    print(f"\n[UNIT-T7] Construcao de contexto_consulta:")
    print(f"  - servicos_multiplos: {contexto_consulta.get('servicos_multiplos')}")
    print(f"  - intervalo: {contexto_consulta.get('intervalo_inicio')}-{contexto_consulta.get('intervalo_fim')}")
    print(f"  - data_hora: {contexto_consulta.get('data_hora')}")
    print(f"  - profissional: {contexto_consulta.get('profissional_mencionada')}")
    print(f"  Status: {'PASSOU' if passou else 'FALHOU'}")

    return passou


def test_contexto_preserva_quando_vazio():
    """Contexto preserva valores mesmo quando alguns campos vazios."""
    contexto = enriquecer_contexto_consulta({}, "manicure hoje")

    # data_hora deve existir, intervalo pode estar vazio
    passou = (
        contexto.get("data_hora") is not None
        and contexto.get("intervalo_inicio") is None
        and contexto.get("intervalo_fim") is None
    )

    print(f"\n[UNIT-T8] Preservacao parcial:")
    print(f"  - data_hora: {contexto.get('data_hora')} (deve existir)")
    print(f"  - intervalo: {contexto.get('intervalo_inicio')} (pode ser None)")
    print(f"  Status: {'PASSOU' if passou else 'FALHOU'}")

    return passou


def main():
    print("\n" + "="*70)
    print("P1 FIX - TESTES UNITARIOS (sem dependencias router/gpt)")
    print("="*70)

    testes = [
        ("T1: extrair 'amanha'", test_extrair_data_amanha),
        ("T2: extrair 'hoje'", test_extrair_data_hoje),
        ("T3: extrair 'segunda'", test_extrair_data_segunda),
        ("T4: extrair 'dia 25'", test_extrair_data_dia_especifico),
        ("T5: extrair intervalo 14-17", test_extrair_intervalo_14_17),
        ("T6: enriquecimento completo", test_enriquecer_com_intervalo_e_data),
        ("T7: construcao contexto_consulta", test_contexto_com_multiplos_servicos),
        ("T8: preservacao parcial", test_contexto_preserva_quando_vazio),
    ]

    resultados = []
    for nome, teste_func in testes:
        try:
            resultado = teste_func()
            resultados.append((nome, resultado))
        except Exception as e:
            print(f"\n[ERROR] {nome}: {e}")
            import traceback
            traceback.print_exc()
            resultados.append((nome, False))

    # Resumo
    print("\n" + "="*70)
    print("RESUMO UNITARIOS")
    print("="*70)
    total = len(resultados)
    passou = sum(1 for _, r in resultados if r)

    for nome, resultado in resultados:
        status = "PASSOU" if resultado else "FALHOU"
        print(f"[{status}] {nome}")

    print(f"\nTotal: {passou}/{total} PASSOU")

    return passou == total


if __name__ == "__main__":
    resultado = main()
    sys.exit(0 if resultado else 1)
