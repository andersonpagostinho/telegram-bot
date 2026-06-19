#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RASTREIO P0 REAL — Capturar Stack Traces de Contexto Sem Tenant

Simula mensagem real e captura TODOS os [CTX_BLOQUEADO_SEM_TENANT]
e [CTX_SAVE_BLOQUEADO_SEM_TENANT] que aparecerem.

Executa: "Quero corte com Bruna amanhã às 10"
"""

import os
import sys
import io
import asyncio
import logging
import json
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

# Fix encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Setup
os.environ["TZ"] = "America/Sao_Paulo"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Logging com captura de stack traces
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('rastreio_p0_real.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Variáveis para capturar bloqueios
BLOQUEIOS_CAPTURADOS = []

class CapturadorBloqueios:
    """Intercepta print() para capturar bloqueios de contexto"""

    def __init__(self, stdout_original):
        self.stdout_original = stdout_original
        self.buffer = []
        self.bloqueio_atual = None

    def write(self, msg):
        self.buffer.append(msg)
        self.stdout_original.write(msg)

        # Detectar bloqueios
        if "[CTX_BLOQUEADO_SEM_TENANT]" in msg or "[CTX_SAVE_BLOQUEADO_SEM_TENANT]" in msg:
            self.capturar_bloqueio(msg)

    def capturar_bloqueio(self, msg):
        """Extrair e registrar bloqueio"""
        if "[CTX_BLOQUEADO_SEM_TENANT]" in msg:
            tipo = "CARREGAR"
            marcador = "[CTX_BLOQUEADO_SEM_TENANT]"
        else:
            tipo = "SALVAR"
            marcador = "[CTX_SAVE_BLOQUEADO_SEM_TENANT]"

        bloqueio = {
            "timestamp": datetime.now().isoformat(),
            "tipo": tipo,
            "marcador": marcador,
            "mensagem_completa": msg,
            "stack_trace": self.extrair_stack_trace(msg)
        }
        BLOQUEIOS_CAPTURADOS.append(bloqueio)

        logger.warning(f"🚨 BLOQUEIO CAPTURADO: {tipo} | {marcador}")

    def extrair_stack_trace(self, msg):
        """Extrair stack trace do bloco de mensagem"""
        linhas = msg.split('\n')
        stack_lines = []
        em_stack = False

        for linha in linhas:
            if "STACK TRACE COMPLETO:" in linha:
                em_stack = True
                continue
            if em_stack:
                stack_lines.append(linha)

        return '\n'.join(stack_lines)

    def flush(self):
        self.stdout_original.flush()

async def executar_rastreio():
    """Executa o fluxo de rastreio"""

    print("\n" + "=" * 80)
    print("RASTREIO P0 REAL — Capturando Stack Traces")
    print("=" * 80 + "\n")

    # Dados da simulação
    user_id = "7371670478"
    dono_id = "7394370553"
    chat_id = user_id
    mensagem = "Quero corte com Bruna amanhã às 10"

    print(f"[SETUP] User ID: {user_id}")
    print(f"[SETUP] Dono ID: {dono_id}")
    print(f"[SETUP] Chat ID: {chat_id}")
    print(f"[SETUP] Mensagem: {mensagem}")
    print()

    # Interceptar stdout para capturar bloqueios
    capturador = CapturadorBloqueios(sys.stdout)
    sys.stdout = capturador

    try:
        print("-" * 80)
        print("[SIMULACAO] Iniciando fluxo de agendamento...")
        print("-" * 80)
        print()

        # Importar após setup
        from router.principal_router import roteador_principal
        from services.firebase_service_async import obter_id_dono

        # Montar contexto de simulação
        ctx = {
            "user_id": user_id,
            "dono_id": dono_id,
            "historico_texto": [mensagem],
            "modo_conversa": "mensagem_texto",
            "estado_fluxo": "idle"
        }

        print(f"[FLUXO] Context inicial: {json.dumps(ctx, indent=2)}")
        print()

        # Mock do Update do Telegram
        mock_update = MagicMock()
        mock_update.effective_user.id = int(user_id)
        mock_update.message.text = mensagem
        mock_update.message.from_user.id = int(user_id)
        mock_update.effective_chat.id = int(chat_id)

        # Mock do Context do Telegram
        mock_context = MagicMock()
        mock_context.user_data = {}
        mock_context.chat_data = {}

        print("[FLUXO] Chamando roteador_principal()...")
        print()

        # Executar o roteador (vai disparar os bloqueios se existirem)
        try:
            resultado = await roteador_principal(
                user_id=user_id,
                dono_id=dono_id,
                mensagem=mensagem,
                contexto=ctx
            )
            print(f"\n[FLUXO] Resultado: {json.dumps(resultado, indent=2)}\n")
        except Exception as e:
            print(f"\n[ERRO] Exceção no roteador: {type(e).__name__}: {e}\n")
            import traceback
            traceback.print_exc()

        print("[SIMULACAO] Fluxo concluído")
        print()

    except ImportError as e:
        print(f"[ERRO IMPORT] {e}")
        print("[INFO] Aguardando configuração de variáveis de ambiente...")
    except Exception as e:
        print(f"[ERRO GERAL] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Restaurar stdout
        sys.stdout = capturador.stdout_original

async def main():
    """Função principal"""

    try:
        await executar_rastreio()
    except KeyboardInterrupt:
        print("\n[PARADO] Rastreio interrompido pelo usuário")
        return 1
    except Exception as e:
        print(f"\n[ERRO FATAL] {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Restaurar stdout e exibir resultados
    print("\n" + "=" * 80)
    print("RESULTADO DO RASTREIO")
    print("=" * 80 + "\n")

    if not BLOQUEIOS_CAPTURADOS:
        print("✅ NENHUM BLOQUEIO CAPTURADO")
        print("\nIsso significa:")
        print("  • Todos os contextos estão sendo passados com tenant_id")
        print("  • Ou o fluxo não disparou chamadas a contexto")
        print("\nPróximas ações:")
        print("  1. Verificar se o fluxo realmente chegou aos handlers")
        print("  2. Verificar logs para [LOAD CTX], [SAVE CTX]")
        print("  3. Se houver [LOAD CTX LEGADO], patch já está funcionando")
        return 0

    print(f"🚨 {len(BLOQUEIOS_CAPTURADOS)} BLOQUEIO(S) CAPTURADO(S)\n")

    for idx, bloqueio in enumerate(BLOQUEIOS_CAPTURADOS, 1):
        print(f"\n{'='*80}")
        print(f"BLOQUEIO #{idx}")
        print(f"{'='*80}")
        print(f"Tipo: {bloqueio['tipo']}")
        print(f"Marcador: {bloqueio['marcador']}")
        print(f"Timestamp: {bloqueio['timestamp']}")
        print(f"\nStack Trace:\n{bloqueio['stack_trace']}")
        print(f"{'='*80}\n")

    # Salvar para análise
    output_file = "rastreio_p0_real_resultado.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(BLOQUEIOS_CAPTURADOS, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Resultados salvos em: {output_file}")

    return 0 if len(BLOQUEIOS_CAPTURADOS) == 0 else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
