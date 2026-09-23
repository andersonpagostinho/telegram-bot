#!/usr/bin/env python3
"""
Teste para validar se Base64 funciona corretamente.
"""

import os
import base64
import json
import sys

print("=" * 70)
print("🧪 TESTE: FIREBASE_CREDENTIALS_B64")
print("=" * 70)

# Simular leitura de Base64 (como faria em Render)
firebase_creds_b64 = os.getenv("FIREBASE_CREDENTIALS_B64")

if not firebase_creds_b64:
    print("\n❌ FIREBASE_CREDENTIALS_B64 não definida localmente")
    print("   Em Render, defina a variável de ambiente com o valor de firebase_credentials_b64.txt")

    # Para teste local, gerar Base64 do arquivo original
    print("\n📝 Gerando Base64 a partir de firebase_credentials.json...")
    try:
        with open("firebase_credentials.json", "r") as f:
            json_content = f.read()
        firebase_creds_b64 = base64.b64encode(json_content.encode('utf-8')).decode('utf-8')
        print("   ✅ Base64 gerado")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        sys.exit(1)

# Teste 1: Decodificar Base64
print("\n[TESTE 1] Decodificar Base64")
print("-" * 70)

try:
    decoded = base64.b64decode(firebase_creds_b64).decode('utf-8')
    print("✅ Base64 decodificado com sucesso")
    print(f"   Tamanho: {len(decoded)} caracteres")
except Exception as e:
    print(f"❌ Falha ao decodificar: {e}")
    sys.exit(1)

# Teste 2: Validar JSON
print("\n[TESTE 2] Validar JSON")
print("-" * 70)

try:
    json_obj = json.loads(decoded)
    print("✅ JSON válido")

    # Verificar campos obrigatórios
    campos_obrigatorios = ["type", "project_id", "private_key", "client_email"]
    campos_encontrados = []
    campos_faltando = []

    for campo in campos_obrigatorios:
        if campo in json_obj:
            campos_encontrados.append(campo)
            valor = json_obj[campo]
            if campo == "private_key":
                print(f"   ✅ {campo}: (privado, não mostrado)")
            else:
                preview = str(valor)[:50]
                print(f"   ✅ {campo}: {preview}...")
        else:
            campos_faltando.append(campo)
            print(f"   ❌ {campo}: FALTANDO")

    if campos_faltando:
        print(f"\n❌ Campos obrigatórios faltando: {campos_faltando}")
        sys.exit(1)

except json.JSONDecodeError as e:
    print(f"❌ JSON inválido: {e}")
    sys.exit(1)

# Teste 3: Simular inicialização Firebase
print("\n[TESTE 3] Simular inicialização Firebase")
print("-" * 70)

try:
    # Criar arquivo temporário como faria em produção
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(json_obj, f)
        temp_path = f.name

    print(f"✅ Arquivo temporário criado: {temp_path}")
    print(f"   Tamanho: {os.path.getsize(temp_path)} bytes")

    # Limpar
    os.remove(temp_path)
    print(f"✅ Arquivo temporário removido")

except Exception as e:
    print(f"❌ Erro ao criar arquivo temporário: {e}")
    sys.exit(1)

# Resultado final
print("\n" + "=" * 70)
print("✅ TODOS OS TESTES PASSARAM!")
print("=" * 70)

print("\n📋 Resumo:")
print(f"   ✅ Base64 decodificado: {len(decoded)} caracteres")
print(f"   ✅ JSON válido com {len(campos_encontrados)}/{len(campos_obrigatorios)} campos")
print(f"   ✅ Pronto para Firebase!")

print("\n🚀 Próximos passos:")
print("   1. Copiar firebase_credentials_b64.txt")
print("   2. Em Render, definir FIREBASE_CREDENTIALS_B64 = <conteúdo>")
print("   3. Remover ou comentar FIREBASE_CREDENTIALS em Render")
print("   4. Deploy e validar!")

print("\n")
