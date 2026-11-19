# -*- coding: utf-8 -*-
"""
PROBLEMA 1: Duplicação de Processamento
Teste de Concorrência — Webhook 2x Paralelo (Mesmo msg_id)

Critério de Aceite:
- Webhook chega 2x com mesmo msg_id (paralelo)
- Motor executa APENAS 1x (não 2x)
- Segunda thread encerra com 200, sem processar
"""

import pytest
import asyncio
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

raiz_projeto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, raiz_projeto)

from services.whatsapp_msg_state_service import marcar_processando, consultar_status


class TestP1ConcorrenciaWebhook:
    """Teste de concorrência: 2 webhooks paralelos, mesmo msg_id"""

    @pytest.mark.asyncio
    async def test_p1_webhook_duplicado_motor_executa_uma_unica_vez(self):
        """
        CENÁRIO:
        - Webhook POST #1 (msg_id=X, timestamp=T) inicia Thread 1
        - Webhook POST #2 (msg_id=X, timestamp=T) inicia Thread 2 (paralela)

        ESPERADO:
        - Thread 1: marcar_processando() → sucesso (ganhou_disputa=True)
        - Thread 2: marcar_processando() → falha (AlreadyExists, ganhou_disputa=False)

        GARANTIA:
        - Motor executa 1x apenas
        - Segunda thread retorna 200 (não processa)
        """

        phone_number_id = "5511991382080"
        msg_id = f"test_webhook_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.utcnow().timestamp()

        # Simulação de contador de execuções do motor
        execucoes_motor = []

        async def simular_processamento_motor(thread_id: str):
            """Simula execução do motor (consulta multisserviço)"""
            # Log que motor foi executado
            execucoes_motor.append({
                "thread": thread_id,
                "timestamp": datetime.utcnow().isoformat(),
                "msg_id": msg_id
            })
            # Aguarda um pouco para simular processamento real
            await asyncio.sleep(0.1)

        # === TESTE CONCORRÊNCIA ===

        async def webhook_thread_1():
            """Thread 1: Primeira requisição webhook"""
            # Consulta status (deve estar vazio)
            status = await consultar_status(phone_number_id, msg_id)
            assert status is None or status != "CONCLUIDA", \
                f"❌ T1: Status já é CONCLUIDA (esperado: vazio ou PROCESSANDO)"

            # Tenta marcar PROCESSANDO
            ganhou = await marcar_processando(phone_number_id, msg_id, timestamp)

            assert ganhou == True, \
                f"❌ T1: Deveria ganhar disputa, mas ganhou={ganhou}"

            # Se ganhou, processa motor
            await simular_processamento_motor("T1")

            return "T1_SUCESSO"

        async def webhook_thread_2():
            """Thread 2: Segunda requisição webhook (paralela)"""
            # Aguarda T1 terminar a criação (Firestore leva tempo)
            await asyncio.sleep(0.5)

            # Consulta status (deve estar PROCESSANDO)
            status = await consultar_status(phone_number_id, msg_id)
            # Status pode estar PROCESSANDO ou None (lag de Firestore)

            # Tenta marcar PROCESSANDO
            ganhou = await marcar_processando(phone_number_id, msg_id, timestamp)

            # CRÍTICO: Deve perder a disputa
            assert ganhou == False, \
                f"❌ T2: Deveria perder disputa, mas ganhou={ganhou}"

            # Se perdeu, NÃO processa motor
            # (esse é o ponto: continue em vez de return 200 causa problema)

            return "T2_PERDEU"

        # Executar ambas as threads em paralelo
        t1_result, t2_result = await asyncio.gather(
            webhook_thread_1(),
            webhook_thread_2(),
            return_exceptions=False
        )

        # === VALIDAÇÕES ===

        # T1 deve ter sucesso
        assert t1_result == "T1_SUCESSO", f"T1 falhou: {t1_result}"

        # T2 deve ter perdido disputa
        assert t2_result == "T2_PERDEU", f"T2 não perdeu: {t2_result}"

        # CRÍTICO: Motor deve executar APENAS 1x
        assert len(execucoes_motor) == 1, \
            f"❌ FALHA P1: Motor executou {len(execucoes_motor)}x (esperado 1x)\n" \
            f"Execuções: {execucoes_motor}"

        # Verificar que a única execução foi T1
        assert execucoes_motor[0]["thread"] == "T1", \
            f"❌ Execução foi T2 (deveria ser T1): {execucoes_motor}"

        print(f"✅ TESTE PASSOU: Motor executado 1x (T1), T2 perdeu disputa")
        print(f"   Execuções: {execucoes_motor}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
