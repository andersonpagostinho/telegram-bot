"""
Test Past-Time Blocking in event_service_async.salvar_evento()
Simples testes sem emojis para validacao de past-time blocking
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import pytz

# Setup path
script_dir = os.path.dirname(os.path.abspath(__file__))
projeto_dir = os.path.dirname(script_dir)
sys.path.insert(0, projeto_dir)
os.chdir(projeto_dir)

from services.event_service_async import salvar_evento
from services.firebase_service_async import deletar_dado_em_path

FUSO_BR = pytz.timezone("America/Sao_Paulo")
TEST_TENANT = "test_past_time_tenant"
TEST_USER = "test_past_time_user"


async def test_past_one_hour():
    """Teste: Uma hora no passado deve ser bloqueado"""
    print("\n[TEST] Evento uma hora no passado")

    try:
        agora = datetime.now(FUSO_BR)
        passado = agora - timedelta(hours=1)

        evento = {
            "confirmado": True,
            "data": passado.strftime("%Y-%m-%d"),
            "hora_inicio": passado.strftime("%H:%M"),
            "hora_fim": (passado + timedelta(minutes=60)).strftime("%H:%M"),
            "duracao": 60,
            "profissional": "Ana",
            "cliente_id": TEST_USER,
            "cliente_nome": "Test",
            "descricao": "Test"
        }

        resultado = await salvar_evento(TEST_USER, evento, TEST_TENANT)

        if resultado is False:
            print("[PASS] Evento foi rejeitado corretamente")
            return True
        else:
            print(f"[FAIL] Evento nao foi rejeitado (resultado={resultado})")
            return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


async def test_future_30min():
    """Teste: 30 minutos no futuro deve ser aceito"""
    print("\n[TEST] Evento 30 minutos no futuro")

    try:
        agora = datetime.now(FUSO_BR)
        futuro = agora + timedelta(minutes=30)

        evento = {
            "confirmado": True,
            "data": futuro.strftime("%Y-%m-%d"),
            "hora_inicio": futuro.strftime("%H:%M"),
            "hora_fim": (futuro + timedelta(minutes=60)).strftime("%H:%M"),
            "duracao": 60,
            "profissional": "Ana",
            "cliente_id": TEST_USER,
            "cliente_nome": "Test",
            "descricao": "Test"
        }

        resultado = await salvar_evento(TEST_USER, evento, TEST_TENANT)

        # Deve passar (True ou conflito de agenda, mas nao past-time)
        if resultado is True or (isinstance(resultado, str) and resultado.startswith("conflito")):
            print(f"[PASS] Evento futuro nao foi bloqueado por past-time (resultado={resultado})")

            if resultado is True:
                try:
                    event_id = f"{TEST_USER}_ana_{futuro.strftime('%Y-%m-%d')}_{futuro.strftime('%H:%M')}".replace(" ", "_").lower()
                    await deletar_dado_em_path(f"Clientes/{TEST_TENANT}/Eventos/{event_id}")
                except:
                    pass

            return True
        else:
            print(f"[FAIL] Evento futuro foi bloqueado (resultado={resultado})")
            return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


async def test_now():
    """Teste: Instante atual deve ser bloqueado"""
    print("\n[TEST] Evento no instante atual")

    try:
        agora = datetime.now(FUSO_BR)

        evento = {
            "confirmado": True,
            "data": agora.strftime("%Y-%m-%d"),
            "hora_inicio": agora.strftime("%H:%M"),
            "hora_fim": (agora + timedelta(minutes=60)).strftime("%H:%M"),
            "duracao": 60,
            "profissional": "Ana",
            "cliente_id": TEST_USER,
            "cliente_nome": "Test",
            "descricao": "Test"
        }

        resultado = await salvar_evento(TEST_USER, evento, TEST_TENANT)

        if resultado is False:
            print("[PASS] Evento no instante atual foi rejeitado")
            return True
        else:
            print(f"[FAIL] Evento nao foi rejeitado (resultado={resultado})")
            return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


async def run_tests():
    """Executar todos os testes"""
    print("\n" + "="*70)
    print("TESTES: Past-Time Blocking em salvar_evento()")
    print("="*70)

    tests = [
        ("T1: Passado 1h", test_past_one_hour),
        ("T2: Futuro 30min", test_future_30min),
        ("T3: Agora", test_now),
    ]

    resultados = []
    for nome, func in tests:
        try:
            resultado = await func()
            resultados.append((nome, resultado))
        except Exception as e:
            print(f"[FATAL] {nome}: {e}")
            resultados.append((nome, False))

    # Resumo
    print("\n" + "="*70)
    print("RESUMO")
    print("="*70)

    passed = sum(1 for _, r in resultados if r)
    total = len(resultados)

    for nome, resultado in resultados:
        status = "[PASS]" if resultado else "[FAIL]"
        print(f"{status} {nome}")

    print(f"\nTotal: {passed}/{total} TESTES PASSARAM")

    return passed == total


if __name__ == "__main__":
    resultado = asyncio.run(run_tests())
    sys.exit(0 if resultado else 1)
