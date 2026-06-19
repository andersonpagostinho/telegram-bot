#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RASTREIO P0 DIRETO — Testa funções de contexto diretamente

Chama carregar_contexto_temporario() e salvar_contexto_temporario()
SEM tenant_id para capturar [CTX_BLOQUEADO_SEM_TENANT]
"""

import os
import sys
import io
import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

# Fix encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Setup
os.environ["TZ"] = "America/Sao_Paulo"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BLOQUEIOS_CAPTURADOS = []

def interceptar_print():
    """Intercepta stdout para capturar [CTX_BLOQUEADO_SEM_TENANT]"""
    import builtins

    print_original = builtins.print

    def print_interceptado(*args, **kwargs):
        msg = ' '.join(str(arg) for arg in args)

        # Capturar bloqueios
        if "[CTX_BLOQUEADO_SEM_TENANT]" in msg or "[CTX_SAVE_BLOQUEADO_SEM_TENANT]" in msg:
            bloqueio = {
                "timestamp": datetime.now().isoformat(),
                "tipo": "CARREGAR" if "[CTX_BLOQUEADO_SEM_TENANT]" in msg else "SALVAR",
                "mensagem": msg
            }
            BLOQUEIOS_CAPTURADOS.append(bloqueio)

            # Exibir highlight
            print_original(f"\n{'🚨'*40}", flush=True)
            print_original(f"🚨 BLOQUEIO CAPTURADO!", flush=True)
            print_original(f"{'🚨'*40}\n", flush=True)

        # Imprimir normalmente
        print_original(*args, **kwargs)

    builtins.print = print_interceptado

async def testar_carregar_sem_tenant():
    """Testa carregar_contexto_temporario SEM tenant_id"""

    print("\n" + "=" * 80)
    print("TESTE 1: carregar_contexto_temporario(user_id=X, tenant_id=None)")
    print("=" * 80 + "\n")

    from utils.contexto_temporario import carregar_contexto_temporario

    # Mock Firebase para não precisar real
    with patch('utils.contexto_temporario.buscar_dado_em_path') as mock_buscar:
        mock_buscar.return_value = {"draft_agendamento": {"servico": "corte"}}

        print("[TESTE] Chamando carregar_contexto_temporario(user_id='7371670478', tenant_id=None)")
        print()

        resultado = await carregar_contexto_temporario(
            user_id="7371670478",
            tenant_id=None  # ← SEM TENANT
        )

        print(f"[TESTE] Resultado: {resultado}")
        print(f"[TESTE] Resultado == {{}}: {resultado == {}}")
        print()

async def testar_salvar_sem_tenant():
    """Testa salvar_contexto_temporario SEM tenant_id"""

    print("\n" + "=" * 80)
    print("TESTE 2: salvar_contexto_temporario(user_id=X, contexto=Y, tenant_id=None)")
    print("=" * 80 + "\n")

    from utils.contexto_temporario import salvar_contexto_temporario

    # Mock Firebase
    with patch('utils.contexto_temporario.buscar_dado_em_path') as mock_buscar, \
         patch('utils.contexto_temporario.atualizar_dado_em_path') as mock_salvar:

        mock_buscar.return_value = {}
        mock_salvar.return_value = True

        print("[TESTE] Chamando salvar_contexto_temporario(user_id='7371670478', contexto={...}, tenant_id=None)")
        print()

        resultado = await salvar_contexto_temporario(
            user_id="7371670478",
            contexto={"draft_agendamento": {"servico": "corte"}},
            tenant_id=None  # ← SEM TENANT
        )

        print(f"[TESTE] Resultado: {resultado}")
        print(f"[TESTE] Resultado == False: {resultado == False}")
        print()

async def testar_carregar_com_tenant():
    """Testa carregar_contexto_temporario COM tenant_id (deveria funcionar)"""

    print("\n" + "=" * 80)
    print("TESTE 3: carregar_contexto_temporario(user_id=X, tenant_id='7394370553')")
    print("=" * 80 + "\n")

    from utils.contexto_temporario import carregar_contexto_temporario

    # Mock Firebase
    with patch('utils.contexto_temporario.buscar_dado_em_path') as mock_buscar:
        # Simular contexto com guard válido
        mock_buscar.return_value = {
            "draft_agendamento": {"servico": "corte"},
            "_tenant_id_guard": "7394370553"
        }

        print("[TESTE] Chamando carregar_contexto_temporario(user_id='7371670478', tenant_id='7394370553')")
        print()

        resultado = await carregar_contexto_temporario(
            user_id="7371670478",
            tenant_id="7394370553"  # ← COM TENANT
        )

        print(f"[TESTE] Resultado: {resultado}")
        print(f"[TESTE] Contém draft_agendamento: {'draft_agendamento' in resultado}")
        print()

async def main():
    """Função principal"""

    print("\n" + "=" * 80)
    print("RASTREIO P0 DIRETO — Testes de Contexto Sem Tenant")
    print("=" * 80 + "\n")

    # Interceptar print() para capturar bloqueios
    interceptar_print()

    try:
        # Teste 1: Carregar SEM tenant
        await testar_carregar_sem_tenant()

        # Teste 2: Salvar SEM tenant
        await testar_salvar_sem_tenant()

        # Teste 3: Carregar COM tenant (deveria funcionar)
        await testar_carregar_com_tenant()

    except Exception as e:
        print(f"\n[ERRO] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    # Exibir resumo de bloqueios capturados
    print("\n" + "=" * 80)
    print("RESUMO DE BLOQUEIOS")
    print("=" * 80 + "\n")

    if not BLOQUEIOS_CAPTURADOS:
        print("❌ NENHUM BLOQUEIO CAPTURADO")
        print("\nIsso pode significar:")
        print("  1. Stack traces não estão sendo impressos (check prints)")
        print("  2. Os patches ainda não foram aplicados")
        print("  3. As funções não estão sendo chamadas")
        return 1

    print(f"✅ {len(BLOQUEIOS_CAPTURADOS)} BLOQUEIO(S) CAPTURADO(S)\n")

    for idx, bloqueio in enumerate(BLOQUEIOS_CAPTURADOS, 1):
        print(f"\nBloqueio #{idx}:")
        print(f"  Tipo: {bloqueio['tipo']}")
        print(f"  Timestamp: {bloqueio['timestamp']}")
        print(f"  Mensagem: {bloqueio['mensagem'][:100]}...")

    # Salvar resultado
    with open('rastreio_p0_direto.json', 'w', encoding='utf-8') as f:
        json.dump(BLOQUEIOS_CAPTURADOS, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Resultado salvo em: rastreio_p0_direto.json")

    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
