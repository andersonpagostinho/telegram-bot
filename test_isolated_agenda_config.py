#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LOTE 6C: Validação isolada da configuração de agenda.

Objetivo: Provar que obter_janela_funcionamento() lê corretamente
a configuração de agenda criada no setup.

Fluxo:
1. Criar tenant_id novo
2. Salvar documento de configuração com agenda_padrao (chaves numéricas)
3. Chamar obter_janela_funcionamento() diretamente
4. Validar que aberto=True para terça 14:00
"""

import asyncio
import uuid
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

async def test_agenda_config():
    """Teste isolado de configuração de agenda."""

    from services.firebase_service_async import salvar_dado_em_path
    from services.agenda_service import obter_janela_funcionamento

    # ===== SETUP =====
    tenant_id = f"teste_isolado_{uuid.uuid4().hex[:8]}"
    data_cenario_06 = "2026-06-23T14:00:00"  # Terça às 14:00

    print(f"\n{'='*70}")
    print(f"LOTE 6C: VALIDAÇÃO ISOLADA CONFIG AGENDA")
    print(f"{'='*70}")
    print(f"tenant_id: {tenant_id}")
    print(f"data: {data_cenario_06}")
    print(f"{'='*70}\n")

    # ===== CRIAR CONFIGURAÇÃO =====
    print("[1] Salvando configuração de agenda...")

    agenda_salao = {
        "agenda_padrao": {
            "0": {"aberto": True, "inicio": "08:00", "fim": "18:00"},  # segunda
            "1": {"aberto": True, "inicio": "08:00", "fim": "18:00"},  # terça
            "2": {"aberto": True, "inicio": "08:00", "fim": "18:00"},  # quarta
            "3": {"aberto": True, "inicio": "08:00", "fim": "18:00"},  # quinta
            "4": {"aberto": True, "inicio": "08:00", "fim": "18:00"},  # sexta
            "5": {"aberto": True, "inicio": "08:00", "fim": "18:00"},  # sábado
            "6": {"aberto": False},  # domingo
        }
    }

    try:
        # Salvar em ambos paths (maiúscula e minúscula)
        path_maiuscula = f"Clientes/{tenant_id}/Configuracao/agenda_funcionamento"
        path_minuscula = f"Clientes/{tenant_id}/configuracao/agenda_funcionamento"

        await salvar_dado_em_path(path_maiuscula, agenda_salao)
        print(f"   [OK] Salvo em: {path_maiuscula}")

        await salvar_dado_em_path(path_minuscula, agenda_salao)
        print(f"   [OK] Salvo em: {path_minuscula}")
    except Exception as e:
        print(f"   [ERRO] ao salvar: {e}")
        return False

    # ===== CHAMAR obter_janela_funcionamento =====
    print("\n[2] Chamando obter_janela_funcionamento()...")

    try:
        janela = await obter_janela_funcionamento(
            user_id=tenant_id,
            data_str=data_cenario_06,
            profissional=None
        )

        print(f"   Resultado: {janela}")

    except Exception as e:
        print(f"   [ERRO] ao chamar: {e}")
        import traceback
        traceback.print_exc()
        return False

    # ===== VALIDAÇÃO =====
    print("\n[3] Validando resultado...")

    aberto = janela.get("aberto", False)
    inicio = janela.get("inicio")
    fim = janela.get("fim")

    print(f"   aberto: {aberto} (esperado: True)")
    print(f"   inicio: {inicio} (esperado: 08:00)")
    print(f"   fim: {fim} (esperado: 18:00)")

    # ===== RESULTADO =====
    print(f"\n{'='*70}")

    if aberto and inicio == "08:00" and fim == "18:00":
        print("[PASS] VALIDAÇÃO PASSOU")
        print("   Configuracao de agenda foi lida corretamente!")
        print(f"{'='*70}\n")
        return True
    else:
        print("[FAIL] VALIDACAO FALHOU")
        print(f"   aberto={aberto} (esperado True)")
        print(f"{' '*70}\n")
        return False

if __name__ == "__main__":
    resultado = asyncio.run(test_agenda_config())
    sys.exit(0 if resultado else 1)
