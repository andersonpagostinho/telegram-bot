#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0.2 — Reprodução Controlada com Firestore Real

Objetivo:
Reproduzir cenário P0.2 com Firestore REAL:
- tenant_id=7394370553
- actor_id=whatsapp:5511991382080
- profissional=Bruna
- serviço=corte
- data=2026-10-05
- horário=09:00
- duração=30
- confirmado=True
- agenda SEM configuração (aberto=False, fallback)

Infraestrutura:
- Firestore REAL (não mock)
- principal_router() ou add_evento_por_gpt() direto
- Firebase credentials via FIREBASE_CREDENTIALS_B64

Objetivo de Captura:
Sequência de logs [P01_TRACE] para determinar:
A) Se validação de expediente bloqueia corretamente
B) Se existe bypass de expediente
C) Se linha 1212 retorna True em falha de salvamento
"""

import pytest
import json
import asyncio
import sys
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
import pytz

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Verificar Firestore real
try:
    from services.firebase_service_async import get_async_client, buscar_dado_em_path, salvar_dado_em_path
    print(f"[OK] Firebase importado: get_async_client")
except Exception as e:
    print(f"[ERRO] Falha ao importar Firebase: {e}")
    raise

from handlers.event_handler import add_evento_por_gpt
from services.gpt_executor import executar_acao_gpt

pytestmark = pytest.mark.asyncio


# ============================================================================
# MOCKS DE TELEGRAM (Adaptar para WhatsApp de necessário)
# ============================================================================

class MockMessage:
    def __init__(self, chat_id, user_id, text=""):
        self.from_user = MagicMock()
        self.from_user.id = user_id
        self.chat = MagicMock()
        self.chat.id = chat_id
        self.text = text
        self.message_id = 1
        self.date = datetime.now(pytz.UTC)
        self.reply_text = AsyncMock(return_value={"ok": True})


class MockUser:
    def __init__(self, user_id):
        self.id = user_id


class MockChat:
    def __init__(self, chat_id):
        self.id = chat_id


class MockUpdate:
    """Mock para Update (Telegram/WhatsApp adapter)"""
    def __init__(self, user_id: str, chat_id: str = "", text: str = ""):
        self.message = MockMessage(chat_id, user_id, text)
        self.effective_user = self.message.from_user
        self.effective_chat = self.message.chat


class MockContext:
    """Mock para context (Telegram/WhatsApp adapter)"""
    def __init__(self):
        self.bot = AsyncMock()
        self.bot.send_message = AsyncMock(return_value={"ok": True})
        self.user_data = {}
        self.chat_data = {}
        self.bot_data = {}


# ============================================================================
# TESTE P0.2 REPRODUÇÃO
# ============================================================================

async def test_p02_reproducao_agenda_fechada_confirmado_true():
    """
    P0.2 — Reprodução controlada com Firestore real.

    Cenário:
    - tenant_id=7394370553
    - actor_id=whatsapp:5511991382080
    - profissional=Bruna
    - serviço=corte
    - data=2026-10-05 09:00
    - duração=30 min
    - confirmado=True
    - agenda sem configuração (aberto=False)

    Objetivo:
    Capturar sequência de [P01_TRACE] para diagnosticar:
    A) Bloqueio de expediente
    B) Bypass de expediente
    C) Retorno True em falha de salvamento
    """

    print("\n" + "="*80)
    print("[P0.2 REPRODUÇÃO] Agenda Fechada + Confirmado=True + Firestore Real")
    print("="*80)

    tenant_id = "7394370553"
    actor_id = "whatsapp:5511991382080"
    canal = "whatsapp"

    print(f"\n[SETUP]")
    print(f"  tenant_id: {tenant_id}")
    print(f"  actor_id: {actor_id}")
    print(f"  canal: {canal}")
    print(f"  Firestore: REAL")

    # Verificar que Firestore é real
    try:
        db = get_async_client()
        print(f"  [OK] Firestore real conectado: {type(db)}")
    except Exception as e:
        print(f"  [ERRO] Falha ao conectar Firestore: {e}")
        raise

    # ========================================================================
    # PREPARAR DADOS DO EVENTO
    # ========================================================================

    print(f"\n[DADOS DO EVENTO]")
    evento_dados = {
        "profissional": "Bruna",
        "servico": "corte",
        "data_hora": "2026-10-05T09:00:00",
        "duracao": 30,
        "cliente_nome": "Teste P0.2",
        "descricao": "corte",
        "confirmado": True,  # ← CRÍTICO
        "tenant_id": tenant_id,
        "user_id": actor_id,
    }

    print(f"  profissional: {evento_dados['profissional']}")
    print(f"  serviço: {evento_dados['servico']}")
    print(f"  data_hora: {evento_dados['data_hora']}")
    print(f"  duração: {evento_dados['duracao']}")
    print(f"  confirmado: {evento_dados['confirmado']}")

    # ========================================================================
    # VERIFICAR ESTADO FIRESTORE ANTES
    # ========================================================================

    print(f"\n[VERIFICAÇÃO PRÉ-TESTE — Firestore Real]")

    # Verificar configuração de agenda
    try:
        config_path = f"Clientes/{tenant_id}/configuracao/agenda_funcionamento"
        config = await buscar_dado_em_path(config_path)
        if config:
            print(f"  [OK] Config agenda encontrada: {config.get('agenda_padrao', {})}")
        else:
            print(f"  [WARN] Config agenda NAO encontrada (fallback aberto=False esperado)")
    except Exception as e:
        print(f"  [WARN] Erro ao buscar config: {e}")

    # ========================================================================
    # EXECUTAR add_evento_por_gpt() DIRETO
    # ========================================================================

    print(f"\n[EXECUÇÃO] add_evento_por_gpt() com Firestore Real")
    print("-" * 80)

    # Usar update=None para simular WhatsApp (não Telegram)
    update = None  # WhatsApp não usa Telegram Update
    context = MockContext()

    try:
        resultado = await add_evento_por_gpt(update, context, evento_dados)

        print(f"\n[RESULTADO FINAL]")
        print(f"  add_evento_por_gpt() retornou: {resultado}")
        print(f"  Tipo: {type(resultado)}")

    except Exception as e:
        print(f"\n[ERRO NA EXECUÇÃO]")
        print(f"  Exceção: {e}")
        import traceback
        traceback.print_exc()
        raise

    # ========================================================================
    # VERIFICAR ESTADO FIRESTORE DEPOIS
    # ========================================================================

    print(f"\n[VERIFICAÇÃO PÓS-TESTE — Firestore Real]")
    print("-" * 80)

    # Procurar evento criado
    try:
        eventos_path = f"Clientes/{tenant_id}/Eventos"
        eventos_ref = get_async_client().collection("Clientes").document(tenant_id).collection("Eventos")

        # Buscar eventos do dia 2026-10-05
        query = eventos_ref.where("data", "==", "2026-10-05")
        docs = query.stream()

        eventos_encontrados = []
        for doc in docs:
            data = doc.to_dict()
            if (data.get("hora_inicio") == "09:00" and
                data.get("profissional") == "Bruna" and
                data.get("duracao") == 30):
                eventos_encontrados.append((doc.id, data))

        if eventos_encontrados:
            print(f"  [OK] EVENTO ENCONTRADO no Firestore real!")
            for evento_id, evento_data in eventos_encontrados:
                print(f"\n  ID: {evento_id}")
                print(f"  Profissional: {evento_data.get('profissional')}")
                print(f"  Data: {evento_data.get('data')}")
                print(f"  Hora: {evento_data.get('hora_inicio')}")
                print(f"  Duracao: {evento_data.get('duracao')}")
                print(f"  Status: {evento_data.get('status')}")
                print(f"  Campos: {list(evento_data.keys())}")
        else:
            print(f"  [ERRO] NENHUM EVENTO ENCONTRADO no Firestore real")
            print(f"     Esperado: data=2026-10-05, hora=09:00, profissional=Bruna")

    except Exception as e:
        print(f"  [WARN] Erro ao buscar eventos: {e}")

    # ========================================================================
    # RESULTADO DIAGNÓSTICO
    # ========================================================================

    print(f"\n" + "="*80)
    print(f"[DIAGNÓSTICO P0.2]")
    print(f"="*80)

    if resultado is True and eventos_encontrados:
        print(f"  [ALERT] BUG CONFIRMADO (Retorno True + Evento Criado)")
        print(f"     - Validacao de expediente nao bloqueou")
        print(f"     - Evento foi criado apesar de agenda fechada")
    elif resultado is True and not eventos_encontrados:
        print(f"  [ALERT] BUG PARCIAL CONFIRMADO (Retorno True, Sem Evento)")
        print(f"     - Linha 1212 retorna True quando salvar_evento() falha")
        print(f"     - Evento NAO foi criado (correto)")
        print(f"     - Mas retorno e True (incorreto)")
    elif resultado is False:
        print(f"  [OK] VALIDACAO FUNCIONOU CORRETAMENTE")
        print(f"     - Expediente foi bloqueado")
        print(f"     - Retornou False (esperado)")

    print(f"\n[LOGS CAPTURADOS — PROCURAR POR [P01_TRACE]]")
    print(f"  Ver stdout acima para sequência de [P01_TRACE]_*")

    # ========================================================================
    # SUMMARY
    # ========================================================================

    print(f"\n" + "="*80)
    print(f"[SUMMARY]")
    print(f"  Resultado: {resultado}")
    print(f"  Evento criado: {bool(eventos_encontrados)}")
    print(f"  Firestore: REAL")
    print(f"  Status: {'BUG REPRODUZIDO' if resultado is True else 'VALIDAÇÃO FUNCIONOU'}")
    print(f"="*80)


# ============================================================================
# MAIN — Executar teste
# ============================================================================

if __name__ == "__main__":
    print("\n[EXECUÇÃO DIRETA] test_p02_reproducao_firebase_real.py")
    print(f"Usando Firebase/Firestore REAL\n")

    try:
        asyncio.run(test_p02_reproducao_agenda_fechada_confirmado_true())
    except Exception as e:
        print(f"\n❌ Falha na execução: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
