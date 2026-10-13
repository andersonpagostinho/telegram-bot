#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUDITORIA READ-ONLY: Cadeia de evento_id para evento de Bruna

Objetivo: Rastrear onde o evento_id diverge entre:
1. ID REAL no Firestore
2. ID armazenado na sessão
3. ID recuperado pelo handler
4. ID passado a cancelar_evento()

Tenant: 7394370553
Usuario: whatsapp:5511991382080
Data: 2026-10-12
Hora: 10:00

NÃO FAZ NENHUMA ALTERAÇÃO. Apenas lê dados.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, date

# Firebase
from firebase_admin import initialize_app, credentials, firestore

# Setup
project_root = Path(__file__).parent
creds_path = project_root / "firebase_credentials.json"
cred = credentials.Certificate(str(creds_path))
app = initialize_app(cred)
db = firestore.client()

print("=" * 80)
print("AUDITORIA READ-ONLY: Cadeia evento_id Bruna 2026-10-12 10:00")
print("=" * 80)

# Parâmetros da auditoria
TENANT_ID = "7394370553"
ACTOR_ID = "whatsapp:5511991382080"
DATA_EVENTO = "2026-10-12"
HORA_EVENTO = "10:00"
PROFISSIONAL = "bruna"  # lowercase para busca

print(f"\n[PARAM] Tenant: {TENANT_ID}")
print(f"[PARAM] Actor: {ACTOR_ID}")
print(f"[PARAM] Data: {DATA_EVENTO}")
print(f"[PARAM] Hora: {HORA_EVENTO}")
print(f"[PARAM] Profissional: {PROFISSIONAL}")

# ============================================================================
# PASSO 1: BUSCAR EVENTO REAL NO FIRESTORE
# ============================================================================
print(f"\n{'='*80}")
print(f"[PASSO-01] Procurar evento de Bruna em Firestore")
print(f"{'='*80}")

events_ref = db.collection("Clientes").document(TENANT_ID).collection("Eventos")
docs = events_ref.stream()

print(f"\n[SEARCH] Procurando em: Clientes/{TENANT_ID}/Eventos/")
print(f"[SEARCH] Critério: data={DATA_EVENTO}, hora={HORA_EVENTO}")

candidates = []
for doc in docs:
    data = doc.to_dict() or {}
    doc_id = doc.id

    ev_data = data.get("data", "")
    ev_hora = data.get("hora_inicio", "")
    ev_prof = data.get("profissional", "").lower()
    ev_cliente = data.get("cliente_id", "")
    ev_status = data.get("status", "")
    ev_created = data.get("created_at", "")

    # Critério de busca
    if (ev_data == DATA_EVENTO and
        ev_hora.startswith(HORA_EVENTO) and
        PROFISSIONAL in ev_prof):

        candidates.append({
            "document_id": doc_id,
            "data": data,
            "path": f"Clientes/{TENANT_ID}/Eventos/{doc_id}"
        })

        print(f"\n[CANDIDATO ENCONTRADO]")
        print(f"  document_id: {doc_id}")
        print(f"  data: {ev_data}")
        print(f"  hora_inicio: {ev_hora}")
        print(f"  profissional: {data.get('profissional')}")
        print(f"  cliente_id: {ev_cliente}")
        print(f"  status: {ev_status}")
        print(f"  created_at: {ev_created}")
        print(f"  path_completo: {candidates[-1]['path']}")

if not candidates:
    print(f"\n[ERRO] Nenhum evento encontrado com critério: data={DATA_EVENTO}, hora={HORA_EVENTO}, prof={PROFISSIONAL}")
    print(f"[DICA] Verificar se evento existe em Firestore")
    sys.exit(1)

if len(candidates) > 1:
    print(f"\n[AVISO] {len(candidates)} candidatos encontrados. Usando primeiro.")

evento_real = candidates[0]
documento_id_real = evento_real["document_id"]
caminho_completo = evento_real["path"]
dados_evento = evento_real["data"]

print(f"\n[RESULTADO] Evento selecionado para auditoria:")
print(f"  document_id REAL: {documento_id_real}")
print(f"  path COMPLETO: {caminho_completo}")
print(f"  dados completos: {json.dumps(dados_evento, indent=2, ensure_ascii=False)}")

# ============================================================================
# PASSO 2: BUSCAR SESSÃO DO USUÁRIO
# ============================================================================
print(f"\n{'='*80}")
print(f"[PASSO-02] Procurar sessão do usuário")
print(f"{'='*80}")

session_path = f"Clientes/{TENANT_ID}/Sessoes/{ACTOR_ID}"
print(f"\n[SEARCH] Path: {session_path}")

session_doc = db.collection("Clientes").document(TENANT_ID).collection("Sessoes").document(ACTOR_ID).get()

if not session_doc.exists:
    print(f"[AVISO] Sessão não encontrada em: {session_path}")
    print(f"[FALLBACK] Procurando em path legado (sem prefixo whatsapp:)...")

    actor_id_sem_prefixo = ACTOR_ID.split(":")[-1]  # "5511991382080"
    session_path_legado = f"Clientes/{TENANT_ID}/Sessoes/{actor_id_sem_prefixo}"
    print(f"[SEARCH] Path legado: {session_path_legado}")

    session_doc = db.collection("Clientes").document(TENANT_ID).collection("Sessoes").document(actor_id_sem_prefixo).get()

    if not session_doc.exists:
        print(f"[ERRO] Sessão não encontrada em nenhum path")
        sys.exit(1)
    else:
        print(f"[OK] Sessão encontrada em path legado")
        session_path = session_path_legado
else:
    print(f"[OK] Sessão encontrada")

session_data = session_doc.to_dict() or {}

print(f"\n[SESSÃO] Dados carregados:")
print(f"  path: {session_path}")
print(f"  estado_fluxo: {session_data.get('estado_fluxo', 'N/A')}")
print(f"  cancelamento_pendente: {session_data.get('cancelamento_pendente', {})}")

# Procurar evento_id na sessão
evento_id_na_sessao = None
cancelamento_pendente = session_data.get("cancelamento_pendente", {})

if isinstance(cancelamento_pendente, dict):
    evento_id_na_sessao = cancelamento_pendente.get("evento_id")
    resumo_evento = cancelamento_pendente.get("resumo_evento", {})

    print(f"\n[EVENTO_ID_SESSÃO] Encontrado na sessão:")
    print(f"  evento_id: {evento_id_na_sessao}")
    print(f"  resumo_evento: {json.dumps(resumo_evento, indent=2, ensure_ascii=False)}")

if not evento_id_na_sessao:
    print(f"\n[AVISO] evento_id NÃO encontrado em cancelamento_pendente")
    print(f"  Conteúdo completo: {json.dumps(cancelamento_pendente, indent=2, ensure_ascii=False)}")

# ============================================================================
# PASSO 3: COMPARAR IDs
# ============================================================================
print(f"\n{'='*80}")
print(f"[PASSO-03] Comparar IDs lado a lado")
print(f"{'='*80}")

print(f"\n[COMPARAÇÃO]")
print(f"  ID REAL NO FIRESTORE         : {documento_id_real}")
print(f"  ID ARMAZENADO NA SESSÃO      : {evento_id_na_sessao}")
print(f"  CORRESPONDEM?                : {documento_id_real == evento_id_na_sessao}")

if documento_id_real != evento_id_na_sessao:
    print(f"\n[DIVERGÊNCIA DETECTADA!]")
    print(f"  documento_id_real: {documento_id_real}")
    print(f"  evento_id_sessao: {evento_id_na_sessao}")
    print(f"  Diferença: O ID armazenado NÃO corresponde ao ID real")
else:
    print(f"\n[OK] IDs correspondem")

# ============================================================================
# PASSO 4: ANALISAR COMO EVENTO_ID FOI GERADO
# ============================================================================
print(f"\n{'='*80}")
print(f"[PASSO-04] Analisar estrutura do evento_id")
print(f"{'='*80}")

print(f"\n[ANÁLISE] documento_id_real: {documento_id_real}")

# Verificar se parece ser um UUID ou ID montado
if "_" in documento_id_real:
    partes = documento_id_real.split("_")
    print(f"  Contém '_': sim, partes: {partes}")
    print(f"  Padrão: possível concatenação de campos")
elif ":" in documento_id_real:
    partes = documento_id_real.split(":")
    print(f"  Contém ':': sim, partes: {partes}")
    print(f"  Padrão: possível prefixo:sufixo")
else:
    print(f"  Padrão: possivelmente UUID ou ID aleatório")

# ============================================================================
# PASSO 5: PROCURAR CÓDIGO QUE GERA EVENTO_ID
# ============================================================================
print(f"\n{'='*80}")
print(f"[PASSO-05] Procurar como evento_id é gerado na criação")
print(f"{'='*80}")

print(f"\n[BUSCA] Procurando em handlers/event_handler.py...")

try:
    event_handler_path = project_root / "handlers" / "event_handler.py"
    with open(event_handler_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Procurar padrão de criação de evento_id
    if "uuid" in content.lower():
        print(f"[OK] Referência a UUID encontrada em event_handler.py")

    if "evento_id" in content:
        print(f"[OK] Referência a 'evento_id' encontrada em event_handler.py")

    # Procurar especificamente criação de documento
    if "collection(\"Eventos\")" in content:
        print(f"[OK] Criação de eventos em collection Eventos encontrada")

except Exception as e:
    print(f"[ERRO] Não foi possível ler event_handler.py: {e}")

# ============================================================================
# PASSO 6: RESUMO FINAL
# ============================================================================
print(f"\n{'='*80}")
print(f"[RESUMO FINAL]")
print(f"{'='*80}")

print(f"\n[EVENTO REAL - FIRESTORE]")
print(f"  Path completo: {caminho_completo}")
print(f"  document_id: {documento_id_real}")
print(f"  data: {dados_evento.get('data')}")
print(f"  hora_inicio: {dados_evento.get('hora_inicio')}")
print(f"  profissional: {dados_evento.get('profissional')}")
print(f"  cliente_id: {dados_evento.get('cliente_id')}")
print(f"  status: {dados_evento.get('status')}")

print(f"\n[EVENTO_ID NA SESSÃO]")
print(f"  Path sessão: {session_path}")
print(f"  evento_id armazenado: {evento_id_na_sessao}")

print(f"\n[DIAGNÓSTICO]")
if documento_id_real == evento_id_na_sessao:
    print(f"  Status: ✅ IDs CORRESPONDEM")
    print(f"  Provável causa: Erro em cancelar_evento() na busca/validação")
else:
    print(f"  Status: ❌ IDs DIVERGEM")
    print(f"  DOCUMENTO REAL: {documento_id_real}")
    print(f"  SESSÃO USA  : {evento_id_na_sessao}")
    print(f"  Provável causa: evento_id gerado/armazenado incorretamente")

print(f"\n{'='*80}")
print(f"FIM DA AUDITORIA")
print(f"{'='*80}\n")
