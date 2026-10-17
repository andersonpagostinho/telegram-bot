#!/usr/bin/env python3
"""
Monitor de Consumo Firestore - Verifica quota e status

Uso:
    python monitor_firebase_quota.py
"""

import asyncio
from datetime import datetime, timedelta
from services.firebase_service_async import get_async_client

async def check_quota_status():
    """Tenta operacao simples para verificar se quota foi liberada"""

    print("\n" + "="*70)
    print("MONITOR DE QUOTA FIRESTORE")
    print("="*70)
    print(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    client = get_async_client()

    print("[1] Testando leitura simples...")
    try:
        ref = client.document("_test_quota/status")
        doc = await ref.get()
        print("    [OK] QUOTA LIBERADA! (read funcionou)")
        return "LIBERADA"
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Quota" in error_msg:
            print(f"    [ESGOTADA] Quota ainda esgotada (429)")
            return "ESGOTADA"
        else:
            print(f"    [ERRO] Erro: {error_msg[:80]}")
            return "DESCONHECIDO"

async def estimate_reset_time():
    """Estima quando a quota volta"""
    print("\n[2] Estimativa de reset...")

    reset_time = datetime.now() + timedelta(hours=24)
    print(f"    Reset estimado: {reset_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"    Tempo restante: aprox 24h")

    return reset_time

async def show_recommendations(status):
    """Recomendacoes baseadas no status"""
    print("\n[3] Recomendacoes...")

    if status == "LIBERADA":
        print("    [ACAO] QUOTA LIBERADA!")
        print("    Proximos passos:")
        print("    1. Limpar dados residuais via Console Firebase")
        print("    2. Re-executar testes com Firestore real")
        print("    3. Fazer deploy")
    else:
        print("    [ESPERA] QUOTA AINDA ESGOTADA")
        print("    Alternativas:")
        print("    1. Usar MOCKS para testes (zero quota)")
        print("    2. Usar Firestore EMULATOR (zero quota)")
        print("    3. Aguardar aprox 24h para reset automatico")

async def main():
    status = await check_quota_status()
    reset_time = await estimate_reset_time()
    await show_recommendations(status)

    print("\n" + "="*70)
    print(f"Status: {status}")
    print("="*70 + "\n")

    return 0 if status == "LIBERADA" else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

