#!/usr/bin/env python3
"""Limpeza de sessão para teste limpo do fluxo WhatsApp."""

import os
import firebase_admin
from firebase_admin import credentials, firestore

# Inicializar Firebase
cred_path = "firebase_credentials.json"
if os.path.exists(cred_path):
    try:
        firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)

db = firestore.client()

tenant_id = "7394370553"
actor_id = "whatsapp:5511991382080"
doc_path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"

print("="*80)
print("LIMPEZA DE SESSÃO - TESTE LIMPO")
print("="*80)
print(f"\nDocumento alvo: {doc_path}\n")

# 1. LER ANTES
print("[1] Lendo documento antes da limpeza...")
doc_antes = db.document(doc_path).get()

if doc_antes.exists:
    data = doc_antes.to_dict()
    print("✅ Documento encontrado\n")

    print("CAMPOS RELEVANTES ANTES:")
    print("-" * 80)
    campos = [
        "estado_fluxo",
        "modo_incremental",
        "objetivo_conversacional",
        "intencao_conversacional",
        "draft_agendamento",
        "dados_confirmacao_agendamento",
        "aguardando_confirmacao_agendamento",
        "profissional_escolhido",
        "servico",
        "data_hora",
    ]

    for campo in campos:
        valor = data.get(campo)
        if valor is not None:
            print(f"  {campo}: {valor!r}")

    print(f"\n  historico_texto: {len(data.get('historico_texto', []))} mensagens")
else:
    print("❌ Documento não encontrado\n")
    exit(1)

# 2. DELETAR
print("\n" + "="*80)
print("[2] Deletando documento...")
print("="*80 + "\n")

try:
    db.document(doc_path).delete()
    print(f"✅ Documento deletado com sucesso")
except Exception as e:
    print(f"❌ Erro ao deletar: {e}")
    exit(1)

# 3. CONFIRMAR EXCLUSÃO
print("\n" + "="*80)
print("[3] Confirmando exclusão...")
print("="*80 + "\n")

doc_depois = db.document(doc_path).get()

if not doc_depois.exists:
    print("✅ CONFIRMADO: Documento não existe mais\n")
    print("="*80)
    print("LIMPEZA CONCLUÍDA COM SUCESSO")
    print("="*80)
    print("\nPróxima ação: Enviar mensagem ao WhatsApp")
    print("O webhook criará nova sessão limpa automaticamente.\n")
else:
    print("❌ ERRO: Documento ainda existe após tentativa de exclusão\n")
    exit(1)
