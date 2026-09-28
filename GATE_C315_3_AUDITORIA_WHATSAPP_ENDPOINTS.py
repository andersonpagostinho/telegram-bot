#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from config.firebase_config import firebase_admin, firestore

def auditoria_completa():
    print("\n" + "=" * 80)
    print("AUDITORIA COMPLETA - WhatsAppEndpoints")
    print("=" * 80)
    print("Timestamp: " + datetime.now().isoformat())
    print()

    db = firestore.client()

    # 1. Listar todos os documentos em WhatsAppEndpoints
    print("[1] Listar todos os documentos em WhatsAppEndpoints")
    print("-" * 80)

    docs = db.collection("WhatsAppEndpoints").stream()
    doc_count = 0
    endpoints = []

    for doc in docs:
        doc_count += 1
        data = doc.to_dict()
        endpoints.append({
            'id': doc.id,
            'data': data
        })
        print("ID: " + str(doc.id))
        print("  Dados: " + json.dumps(data, ensure_ascii=False))
        print()

    if doc_count == 0:
        print("[RESULTADO] Nenhum documento encontrado em WhatsAppEndpoints")
    else:
        print("[RESULTADO] {} documento(s) encontrado(s)".format(doc_count))

    print()

    # 2. Verificar especificamente o ID 1350170954840548
    print("[2] Verificar documento especifico: 1350170954840548")
    print("-" * 80)

    doc_ref = db.collection("WhatsAppEndpoints").document("1350170954840548")
    doc_snapshot = doc_ref.get()

    if doc_snapshot.exists:
        print("[OK] Documento EXISTE")
        print(json.dumps(doc_snapshot.to_dict(), indent=2, ensure_ascii=False))
    else:
        print("[NAO EXISTE] O documento nao esta no Firestore")

    print()

    # 3. Verificar se resolve_tenant_por_endpoint existe
    print("[3] Verificar funcao resolve_tenant_por_endpoint")
    print("-" * 80)

    try:
        from services.whatsapp_service import resolve_tenant_por_endpoint
        print("[OK] Funcao importada com sucesso")

        # Tentar executar
        try:
            resultado = resolve_tenant_por_endpoint("1350170954840548")
            print("Resultado da chamada: " + str(resultado))
        except Exception as e:
            print("[ERRO] Erro ao executar: " + str(e))

    except ImportError as e:
        print("[NAO EXISTE] Funcao nao encontrada: " + str(e))

    print()

    # 4. Buscar por WhatsApp em todas as colecoes
    print("[4] Listar todas as colecoes (amostra)")
    print("-" * 80)

    try:
        colecoes = db.collections()
        colecoes_lista = []

        for colecao in colecoes:
            colecoes_lista.append(colecao.id)

        print("Colecoes encontradas:")
        for col in sorted(colecoes_lista):
            print("  - " + str(col))
    except Exception as e:
        print("[ERRO] Erro ao listar colecoes: " + str(e))

    print()
    print("=" * 80)

if __name__ == "__main__":
    try:
        auditoria_completa()
        sys.exit(0)
    except Exception as e:
        print("\n[ERRO FATAL] " + str(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)
