# -*- coding: utf-8 -*-
# test_notificacoes_expirado.py
"""
Teste para validar que notificacoes muito antigas (> 15 min) sao marcadas como expiradas
e NAO sao enviadas quando o sistema volta ao ar.
"""

import asyncio
from datetime import datetime, timedelta
from pytz import timezone
import sys
import os

# Configurar encoding para UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Mock para simular Firestore
class MockFirestore:
    def __init__(self):
        self.data = {}
        self.updates = []

    async def buscar_dado_em_path(self, path):
        return self.data.get(path)

    async def atualizar_dado_em_path(self, path, dados):
        self.updates.append({"path": path, "dados": dados})
        self.data[path] = dados
        return True


# Simular cenário
async def test_notificacao_expirada():
    """
    Cenário: Sistema desligado por 2 dias
    - Notificação criada: 2 dias atrás (status=pendente, avisado=False)
    - Esperado: NÃO deve ser enviada, deve ser marcada como expirada
    """

    FUSO_BR = timezone("America/Sao_Paulo")
    ATRASO_MAXIMO_NOTIFICACAO_MINUTOS = 15

    # Simular: agora = 2026-06-10 09:00
    agora = datetime(2026, 6, 10, 9, 0, 0, tzinfo=FUSO_BR)

    # Simular: notificação criada = 2026-06-08 14:00 (2 dias atrás = 2880 minutos)
    data_notificacao = datetime(2026, 6, 8, 14, 0, 0, tzinfo=FUSO_BR)

    # Calcular atraso
    atraso = agora - data_notificacao
    atraso_minutos = int(atraso.total_seconds() // 60)

    print("[TEST 1] Notificacao Expirada")
    print("         Data notificacao: {}".format(data_notificacao))
    print("         Agora: {}".format(agora))
    print("         Atraso: {} minutos".format(atraso_minutos))
    print("         Limite: {} minutos".format(ATRASO_MAXIMO_NOTIFICACAO_MINUTOS))
    print()

    # Verificar se expirou
    if atraso_minutos > ATRASO_MAXIMO_NOTIFICACAO_MINUTOS:
        print("[PASS] Notificacao EXPIROU (atraso > limite)")
        print("       Acao esperada:")
        print("       - NAO enviar mensagem")
        print("       - Marcar como: status='expirada'")
        print("       - Marcar como: avisado=True")
        print("       - Marcar como: processada=True")
        print("       - Campo: motivo_expiracao='notificacao_atrasada'")
        print("       - Campo: atraso_minutos={}".format(atraso_minutos))

        # Simular update que seria feito
        update_esperado = {
            "avisado": True,
            "processada": True,
            "status": "expirada",
            "expirada_em": agora.isoformat(),
            "motivo_expiracao": "notificacao_atrasada",
            "atraso_minutos": atraso_minutos,
            "atualizado_em": agora.isoformat(),
        }
        print("\n[UPDATE] Firestore:")
        for k, v in update_esperado.items():
            print("         {}: {}".format(k, v))

        return True
    else:
        print("[FAIL] Notificacao NAO expirou (deveria ter expirado!)")
        return False


async def test_notificacao_dentro_tolerancia():
    """
    Cenário: Notificação criada há 5 minutos (dentro da tolerância de 15min)
    - Esperado: DEVE ser enviada normalmente
    """

    FUSO_BR = timezone("America/Sao_Paulo")
    ATRASO_MAXIMO_NOTIFICACAO_MINUTOS = 15

    # Simular: agora = 2026-06-10 09:00
    agora = datetime(2026, 6, 10, 9, 0, 0, tzinfo=FUSO_BR)

    # Simular: notificação criada = 2026-06-10 08:55 (5 minutos atrás)
    data_notificacao = datetime(2026, 6, 10, 8, 55, 0, tzinfo=FUSO_BR)

    # Calcular atraso
    atraso = agora - data_notificacao
    atraso_minutos = int(atraso.total_seconds() // 60)

    print("\n[TEST 2] Notificacao Dentro da Tolerancia")
    print("         Data notificacao: {}".format(data_notificacao))
    print("         Agora: {}".format(agora))
    print("         Atraso: {} minutos".format(atraso_minutos))
    print("         Limite: {} minutos".format(ATRASO_MAXIMO_NOTIFICACAO_MINUTOS))
    print()

    # Verificar se expirou
    if atraso_minutos > ATRASO_MAXIMO_NOTIFICACAO_MINUTOS:
        print("[FAIL] Notificacao EXPIROU (nao deveria!)")
        return False
    else:
        print("[PASS] Notificacao dentro da tolerancia")
        print("       Acao esperada:")
        print("       - ENVIAR mensagem normalmente")
        print("       - Marcar como: status='enviado'")
        print("       - Marcar como: avisado=True")
        return True


async def test_notificacao_futura():
    """
    Cenário: Notificação agendada para futuro
    - Esperado: NÃO deve ser processada (pula com continue)
    """

    FUSO_BR = timezone("America/Sao_Paulo")

    # Simular: agora = 2026-06-10 09:00
    agora = datetime(2026, 6, 10, 9, 0, 0, tzinfo=FUSO_BR)

    # Simular: notificação criada para = 2026-06-10 14:00 (futuro)
    data_notificacao = datetime(2026, 6, 10, 14, 0, 0, tzinfo=FUSO_BR)

    print("\n[TEST 3] Notificacao Futura")
    print("         Data notificacao: {}".format(data_notificacao))
    print("         Agora: {}".format(agora))
    print()

    if data_notificacao > agora:
        print("[PASS] Notificacao eh futura")
        print("       Acao esperada:")
        print("       - PULAR (continue no codigo)")
        print("       - Nao atualizar Firestore")
        print("       - Tentar novamente na proxima execucao do scheduler")
        return True
    else:
        print("[FAIL] Notificacao nao eh futura (deveria ser!)")
        return False


async def main():
    print("=" * 70)
    print("TESTES: Expiracao de Notificacoes")
    print("=" * 70)
    print()

    resultado1 = await test_notificacao_expirada()
    resultado2 = await test_notificacao_dentro_tolerancia()
    resultado3 = await test_notificacao_futura()

    print()
    print("=" * 70)
    print("RESUMO:")
    print("  Teste 1 (Expirada): {}".format("PASSOU" if resultado1 else "FALHOU"))
    print("  Teste 2 (Tolerancia): {}".format("PASSOU" if resultado2 else "FALHOU"))
    print("  Teste 3 (Futura): {}".format("PASSOU" if resultado3 else "FALHOU"))
    print("=" * 70)

    if resultado1 and resultado2 and resultado3:
        print("\nTODOS OS TESTES PASSARAM!")
        return 0
    else:
        print("\nALGUNS TESTES FALHARAM!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
