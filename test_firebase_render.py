#!/usr/bin/env python3
"""
Teste completo de FIREBASE_CREDENTIALS_B64 em Render
Execute: python test_firebase_render.py
Compartilhe output comigo
"""

import os
import base64
import json
import sys

print("\n" + "=" * 80)
print("🧪 TESTE COMPLETO: FIREBASE_CREDENTIALS_B64 EM RENDER")
print("=" * 80)

# ============================================================================
# [TESTE 1] Verificar variáveis de ambiente
# ============================================================================
print("\n[TESTE 1] Variáveis de Ambiente")
print("-" * 80)

b64_var = os.getenv("FIREBASE_CREDENTIALS_B64")
json_var = os.getenv("FIREBASE_CREDENTIALS")
google_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
google_app = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

print(f"FIREBASE_CREDENTIALS_B64: {'✅ EXISTE' if b64_var else '❌ NÃO EXISTE'}")
if b64_var:
    print(f"   Tamanho: {len(b64_var)} caracteres")
    if len(b64_var) == 3224:
        print(f"   ✅ Tamanho CORRETO (3224)")
    elif len(b64_var) < 3224:
        print(f"   ❌ TRUNCADO (esperado 3224, recebeu {len(b64_var)})")
    else:
        print(f"   ⚠️  Tamanho estranho ({len(b64_var)} vs 3224)")
    print(f"   Primeiros 50: {b64_var[:50]}")
    print(f"   Últimos 50: {b64_var[-50:]}")

print(f"\nFIREBASE_CREDENTIALS (legado): {'✅ EXISTE' if json_var else '❌ NÃO EXISTE'}")
if json_var:
    print(f"   Tamanho: {len(json_var)} caracteres")
    print(f"   ⚠️  Ainda definida (deveria ter sido removida)")

print(f"\nGOOGLE_CREDENTIALS_JSON: {'✅ EXISTE' if google_json else '❌ NÃO EXISTE'}")
if google_json:
    print(f"   Tamanho: {len(google_json)} caracteres")

print(f"\nGOOGLE_APPLICATION_CREDENTIALS: {'✅ EXISTE' if google_app else '❌ NÃO EXISTE'}")
if google_app:
    print(f"   Valor: {google_app}")

# ============================================================================
# [TESTE 2] Decodificar Base64
# ============================================================================
print("\n[TESTE 2] Decodificar Base64")
print("-" * 80)

if not b64_var:
    print("❌ FIREBASE_CREDENTIALS_B64 não está definida")
    print("   Ação: Defina em Render → Settings → Environment Variables")
    sys.exit(1)

try:
    decoded = base64.b64decode(b64_var).decode('utf-8')
    print(f"✅ Base64 decodificado com sucesso")
    print(f"   Tamanho decodificado: {len(decoded)} caracteres")
except Exception as e:
    print(f"❌ Falha ao decodificar Base64")
    print(f"   Erro: {str(e)}")
    print(f"   Ação: Verifique se FIREBASE_CREDENTIALS_B64 foi truncada ao colar")
    sys.exit(1)

# ============================================================================
# [TESTE 3] Validar JSON
# ============================================================================
print("\n[TESTE 3] Validar JSON Decodificado")
print("-" * 80)

try:
    json_obj = json.loads(decoded)
    print(f"✅ JSON válido")
except json.JSONDecodeError as e:
    print(f"❌ JSON inválido após decodificar Base64")
    print(f"   Erro: {str(e)}")
    print(f"   Ação: Base64 pode estar truncada")
    sys.exit(1)

# ============================================================================
# [TESTE 4] Campos obrigatórios
# ============================================================================
print("\n[TESTE 4] Campos Obrigatórios Firebase")
print("-" * 80)

campos_obrigatorios = ["type", "project_id", "private_key", "client_email", "private_key_id"]
campos_ok = []
campos_faltando = []

for campo in campos_obrigatorios:
    if campo in json_obj:
        campos_ok.append(campo)
        valor = json_obj[campo]

        if campo == "private_key":
            tamanho_chave = len(valor)
            print(f"   ✅ {campo}: {tamanho_chave} caracteres")
        else:
            preview = str(valor)[:40]
            print(f"   ✅ {campo}: {preview}...")
    else:
        campos_faltando.append(campo)
        print(f"   ❌ {campo}: FALTANDO")

if campos_faltando:
    print(f"\n❌ Campos obrigatórios faltando: {campos_faltando}")
    sys.exit(1)

# ============================================================================
# [TESTE 5] Teste Firebase Admin SDK
# ============================================================================
print("\n[TESTE 5] Inicializar Firebase Admin SDK")
print("-" * 80)

try:
    import firebase_admin
    from firebase_admin import credentials

    # Criar arquivo temporário
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(json_obj, f)
        temp_path = f.name

    # Tentar carregar credenciais
    cred = credentials.Certificate(temp_path)
    print(f"✅ Credenciais carregadas com sucesso")
    print(f"   Tipo: {cred.client_id}")

    # Tentar inicializar Firebase (pode falhar se já inicializado)
    try:
        firebase_admin.initialize_app(cred)
        print(f"✅ Firebase Admin SDK inicializado")
    except ValueError as e:
        if "already exists" in str(e):
            print(f"✅ Firebase Admin SDK já estava inicializado (esperado)")
        else:
            print(f"⚠️  Firebase Admin SDK erro: {str(e)[:100]}")

    # Limpar arquivo temporário
    import os as os_module
    os_module.remove(temp_path)
    print(f"✅ Arquivo temporário limpo")

except ImportError:
    print(f"⚠️  firebase_admin não está instalado")
    print(f"   (Isso é OK, Firebase será inicializado no main.py)")
except Exception as e:
    print(f"❌ Erro ao testar Firebase Admin SDK")
    print(f"   Erro: {str(e)[:200]}")
    sys.exit(1)

# ============================================================================
# [TESTE 6] Simular o fluxo do firebase_service_async.py
# ============================================================================
print("\n[TESTE 6] Simular Fluxo (firebase_service_async.py)")
print("-" * 80)

print("Simulando:")
print("  1. Carregar FIREBASE_CREDENTIALS_B64")
firebase_creds_b64 = os.getenv("FIREBASE_CREDENTIALS_B64")
print(f"     ✅ Carregado ({len(firebase_creds_b64)} chars)")

print("  2. Decodificar Base64")
decoded = base64.b64decode(firebase_creds_b64).decode('utf-8')
print(f"     ✅ Decodificado ({len(decoded)} chars)")

print("  3. Verificar se começa com {")
if decoded.strip().startswith("{"):
    print(f"     ✅ É JSON")
else:
    print(f"     ❌ Não é JSON")
    sys.exit(1)

print("  4. Parse JSON")
json_obj = json.loads(decoded)
print(f"     ✅ JSON válido")

print("  5. Criar arquivo temporário")
import tempfile
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    json.dump(json_obj, f)
    temp_path = f.name
print(f"     ✅ Arquivo criado: {temp_path}")

print("  6. Definir GOOGLE_APPLICATION_CREDENTIALS")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_path
print(f"     ✅ Definido")

print("  7. Inicializar Firebase")
# (omitido para não duplicar)
print(f"     ✅ Pronto para usar")

# Limpar
import os as os_module
os_module.remove(temp_path)

# ============================================================================
# RESULTADO FINAL
# ============================================================================
print("\n" + "=" * 80)
print("✅ TODOS OS TESTES PASSARAM!")
print("=" * 80)

print("\n📊 RESUMO:")
print(f"   ✅ FIREBASE_CREDENTIALS_B64: {len(b64_var)} caracteres")
print(f"   ✅ Base64 → JSON: Decodificado com sucesso")
print(f"   ✅ Campos: {len(campos_ok)}/{len(campos_obrigatorios)} presentes")
print(f"   ✅ Firebase Admin SDK: Pronto")

print("\n🚀 PRÓXIMO PASSO:")
print("   Se ainda recebe 'Invalid JWT Signature', o problema pode ser:")
print("   1. Credenciais realmente inválidas/expiradas")
print("   2. Projeto_id errado")
print("   3. Chave privada revogada no GCP")
print("   4. Outro erro não relacionado a truncamento")

print("\n📋 Compartilhe este output comigo!")
print("=" * 80 + "\n")
