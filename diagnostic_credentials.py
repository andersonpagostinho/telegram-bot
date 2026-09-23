#!/usr/bin/env python3
"""
Diagnostic script para verificar credenciais em Render/local.
Sem revelar conteúdo, apenas metadados.
"""

import os
import json
import sys

print("=" * 70)
print("🔍 DIAGNÓSTICO DE CREDENCIAIS")
print("=" * 70)

# 1. FIREBASE_CREDENTIALS
print("\n[1] FIREBASE_CREDENTIALS")
print("-" * 70)

firebase_creds = os.getenv("FIREBASE_CREDENTIALS")

if firebase_creds:
    tamanho = len(firebase_creds)
    print(f"✅ EXISTE")
    print(f"   Tamanho: {tamanho} caracteres")

    # Verificar se é exatamente 2047 (truncado)
    if tamanho == 2047:
        print(f"   ⚠️  EXATAMENTE 2047 CHARS → TRUNCADO (confirmado)")
    elif tamanho < 2048:
        print(f"   ⚠️  SUSPEITO: < 2048 chars (pode estar truncado)")
    else:
        print(f"   ✅ Normal: > 2048 chars")

    # Verificar se é JSON ou caminho
    primeiro_char = firebase_creds.strip()[0] if firebase_creds.strip() else None
    print(f"   Primeiro caractere: '{primeiro_char}'")

    if primeiro_char == "{":
        print(f"   📋 Tipo: JSON string (não é caminho)")

        # Tentar fazer parse
        try:
            parsed = json.loads(firebase_creds)
            print(f"   ✅ Parse JSON: SUCESSO")

            # Verificar campos obrigatórios
            campos = ["type", "project_id", "private_key", "client_email"]
            campos_encontrados = [c for c in campos if c in parsed]
            campos_faltando = [c for c in campos if c not in parsed]

            print(f"   Campos (esperados {len(campos)}):")
            for c in campos_encontrados:
                print(f"      ✅ {c}")
            for c in campos_faltando:
                print(f"      ❌ {c} (FALTANDO)")

        except json.JSONDecodeError as e:
            print(f"   ❌ Parse JSON: FALHA")
            print(f"      Erro: {str(e)[:100]}")

    elif primeiro_char in (".", "/", "~"):
        print(f"   📁 Tipo: Caminho de arquivo")
        if os.path.exists(firebase_creds):
            print(f"   ✅ Arquivo EXISTE")
            tamanho_arquivo = os.path.getsize(firebase_creds)
            print(f"      Tamanho: {tamanho_arquivo} bytes")
        else:
            print(f"   ❌ Arquivo NÃO EXISTE")
    else:
        print(f"   ❓ Tipo: Desconhecido (não parece JSON nem caminho)")
else:
    print(f"❌ NÃO DEFINIDA")

# 2. GOOGLE_CREDENTIALS_JSON
print("\n[2] GOOGLE_CREDENTIALS_JSON")
print("-" * 70)

google_creds = os.getenv("GOOGLE_CREDENTIALS_JSON")

if google_creds:
    tamanho = len(google_creds)
    print(f"✅ EXISTE")
    print(f"   Tamanho: {tamanho} caracteres")

    # Verificar se é exatamente 2047 (truncado)
    if tamanho == 2047:
        print(f"   ⚠️  EXATAMENTE 2047 CHARS → TRUNCADO (suspeito)")
    elif tamanho < 2048:
        print(f"   ⚠️  SUSPEITO: < 2048 chars (pode estar truncado)")
    else:
        print(f"   ✅ Normal: > 2048 chars")

    # Verificar se é JSON
    primeiro_char = google_creds.strip()[0] if google_creds.strip() else None
    print(f"   Primeiro caractere: '{primeiro_char}'")

    if primeiro_char == "{":
        try:
            parsed = json.loads(google_creds)
            print(f"   ✅ Parse JSON: SUCESSO")
        except json.JSONDecodeError as e:
            print(f"   ❌ Parse JSON: FALHA")
            print(f"      Erro: {str(e)[:100]}")
    else:
        print(f"   ❓ Tipo: Não é JSON")
else:
    print(f"❌ NÃO DEFINIDA")

# 3. GOOGLE_APPLICATION_CREDENTIALS (se foi definida automaticamente)
print("\n[3] GOOGLE_APPLICATION_CREDENTIALS")
print("-" * 70)

google_app_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

if google_app_creds:
    print(f"✅ EXISTE")
    print(f"   Valor: {google_app_creds}")
    if os.path.exists(google_app_creds):
        print(f"   ✅ Arquivo EXISTE")
        tamanho_arquivo = os.path.getsize(google_app_creds)
        print(f"      Tamanho: {tamanho_arquivo} bytes")
    else:
        print(f"   ⚠️  Arquivo NÃO EXISTE")
else:
    print(f"❌ NÃO DEFINIDA (será definida em runtime)")

# 4. Resumo
print("\n" + "=" * 70)
print("📊 RESUMO")
print("=" * 70)

problemas = []

if not firebase_creds:
    problemas.append("❌ FIREBASE_CREDENTIALS não definida")
elif len(firebase_creds) == 2047:
    problemas.append("⚠️  FIREBASE_CREDENTIALS truncada em 2047 chars")
elif len(firebase_creds) < 2048:
    problemas.append("⚠️  FIREBASE_CREDENTIALS suspeita de truncamento")

if not google_creds:
    problemas.append("⚠️  GOOGLE_CREDENTIALS_JSON não definida (pode não ser crítico se Google Calendar não é usado)")
elif len(google_creds) == 2047:
    problemas.append("⚠️  GOOGLE_CREDENTIALS_JSON truncada em 2047 chars")

if problemas:
    print("\n🚨 PROBLEMAS ENCONTRADOS:\n")
    for p in problemas:
        print(f"  {p}")
else:
    print("\n✅ Nenhum problema óbvio detectado")

print("\n" + "=" * 70)
