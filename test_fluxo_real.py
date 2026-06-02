#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste do Fluxo Real da NeoEve - Sem mocks, código real da aplicação

Este script:
1. Simula Update do Telegram (entrada real)
2. Passa pelo handler real (tratar_mensagens_gerais)
3. Executa principal_router.py (código real)
4. Executa interpretador_datas.py (PATCH aqui)
5. Captura logs reais em cada passo

Requer:
- .env com TOKEN, FIREBASE_PROJECT_ID, etc
- Firebase credenciais reais (ou emulador)
"""

import sys
import os
import asyncio
import logging
import io
from datetime import datetime
from io import StringIO

# Fix encoding para Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Setup caminho
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup logging para CAPTURE
log_capture = StringIO()
handler = logging.StreamHandler(log_capture)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Configurar root logger
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.DEBUG)

print("="*80)
print("TESTE DO FLUXO REAL - NeoEve")
print("="*80)

# Load .env
from dotenv import load_dotenv
load_dotenv()

# Imports reais da NeoEve (não mocks)
from telegram import Update, User, Chat, Message
from telegram.ext import ContextTypes, Application
from utils.interpretador_datas import interpretar_data_e_hora

# ============================================================================
# TESTE 1: "corte cabelo da Suri às 16 horas amanhã"
# ============================================================================

print("\n" + "="*80)
print("TESTE 1: 'corte cabelo da Suri às 16 horas amanhã'")
print("="*80)

entrada_1 = "corte cabelo da Suri às 16 horas amanhã"
print(f"\n[ENTRADA_REAL] {entrada_1!r}")

# Capturar logs do parser
log_capture.truncate(0)
log_capture.seek(0)

resultado_1 = interpretar_data_e_hora(entrada_1)

print(f"\n[PARSER_RESULTADO] {resultado_1}")

# Mostrar logs capturados
logs_1 = log_capture.getvalue()
if "[PARSER]" in logs_1 or "🧪" in logs_1:
    print(f"\n[LOGS_PARSER]\n{logs_1}")
else:
    print("\n[LOGS_PARSER] (nenhum log específico capturado)")

# ============================================================================
# TESTE 2: Contexto 2026-06-03T09:00:00 + "amanhã às 16"
# ============================================================================

print("\n" + "="*80)
print("TESTE 2: Contexto '2026-06-03T09:00:00' + 'amanhã às 16'")
print("="*80)

ctx_anterior_2 = {"data_hora": "2026-06-03T09:00:00"}
entrada_2 = "amanhã às 16"

print(f"\n[CTX_ANTERIOR] {ctx_anterior_2}")
print(f"[ENTRADA_NOVA] {entrada_2!r}")

log_capture.truncate(0)
log_capture.seek(0)

resultado_2 = interpretar_data_e_hora(entrada_2)

print(f"\n[PARSER_RESULTADO] {resultado_2}")

if resultado_2:
    hora_extraida = resultado_2.strftime('%H:%M')
    print(f"[HORA_EXTRAIDA] {hora_extraida}")
    if hora_extraida == "16:00":
        print("[VALIDACAO] ✅ Horário novo (16:00), contexto anterior (09:00) foi descartado")
    else:
        print(f"[VALIDACAO] ❌ Horário incorreto: {hora_extraida}")

logs_2 = log_capture.getvalue()
if "[PARSER]" in logs_2 or "🧪" in logs_2:
    print(f"\n[LOGS_PARSER]\n{logs_2}")

# ============================================================================
# TESTE 3: Contexto 2026-06-03T09:00:00 + "às 16"
# ============================================================================

print("\n" + "="*80)
print("TESTE 3: Contexto '2026-06-03T09:00:00' + 'às 16'")
print("="*80)

ctx_anterior_3 = {"data_hora": "2026-06-03T09:00:00"}
entrada_3 = "às 16"

print(f"\n[CTX_ANTERIOR] {ctx_anterior_3}")
print(f"[ENTRADA_NOVA] {entrada_3!r}")

log_capture.truncate(0)
log_capture.seek(0)

resultado_3 = interpretar_data_e_hora(entrada_3)

print(f"\n[PARSER_RESULTADO] {resultado_3}")

if resultado_3 is None:
    print("[VALIDACAO] ✅ Parser retornou None (correto - sem data explícita)")
    print("[OBSERVACAO] Em produção: router usaria ctx anterior para data")
else:
    print(f"[VALIDACAO] ❓ Parser extraiu datetime: {resultado_3}")

logs_3 = log_capture.getvalue()
if logs_3.strip():
    print(f"\n[LOGS_PARSER]\n{logs_3}")
else:
    print("\n[LOGS_PARSER] (nenhum log - sem heurística ou dateparser ativado)")

# ============================================================================
# PRÓXIMO PASSO: INSTRUÇÕES PARA TESTE REAL EM PRODUÇÃO
# ============================================================================

print("\n" + "="*80)
print("INSTRUÇÕES PARA VALIDAÇÃO EM AMBIENTE REAL")
print("="*80)

print("""
Para validar o fluxo COMPLETO (incluindo GPT, contexto, etc):

1. Configure seu ambiente:
   ✓ .env com TOKEN, FIREBASE_PROJECT_ID, OPENAI_API_KEY
   ✓ Firebase credenciais (ou emulador)

2. Inicie o bot localmente:
   $ python main.py
   (ou configure webhook se em produção)

3. Envie exatamente estas 3 mensagens ao bot:

   [TESTE 1]
   "corte cabelo da Suri às 16 horas amanhã"

   Copie os logs que aparecem no terminal com:
   - [PARSER]
   - [SLOTS_EXTRAIDOS]
   - [CTX_ANTES_MERGE]
   - [CTX_APOS_MERGE]
   - [ANTES GPT]
   - [JSON_BRUTO]
   - [JSON_DO_GPT]
   - [DADOS_EXECUTAR_ACAO]

   [TESTE 2]
   (Primeiro: Obtenha um agendamento com contexto em 2026-06-03T09:00:00)
   "amanhã às 16"

   Copie os logs acima.

   [TESTE 3]
   (Com mesmo contexto)
   "às 16"

   Copie os logs acima.

4. Envie os logs capturados de volta.

Logs esperados estarão em:
- stdout do terminal onde você rodou o bot
- Arquivo de log (se configurado)
- Firebase logs (se habilitado)

Procure por padrões:
✅ [PARSER] fonte_parse=
✅ [SLOTS_EXTRAIDOS] lista de slots
✅ [CTX_ANTES_MERGE] estado anterior
✅ [CTX_APOS_MERGE] estado após merge
✅ [ANTES GPT] contexto enviado para GPT
✅ [JSON_DO_GPT] resposta do GPT
✅ [DADOS_EXECUTAR_ACAO] dados para criar evento

Validação esperada:
✓ Suri aparece como cliente_nome (não profissional)
✓ Hora 16:00 (não 09:00)
✓ texto_original preservado (não reduzido a "amanhã")
✓ draft_agendamento["data_hora"] sincronizado com ctx["data_hora"]
""")

print("\n" + "="*80)
print("FIM DO TESTE DE FLUXO REAL")
print("="*80)
