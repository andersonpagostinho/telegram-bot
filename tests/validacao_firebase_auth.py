"""
Teste mínimo de autenticação Firebase
Valida se get_db() consegue inicializar corretamente
Não altera produção - apenas teste de leitura
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

print("="*70)
print("VALIDAÇÃO DE AUTENTICAÇÃO FIREBASE")
print("="*70)

# Teste 1: Verificar estratégias disponíveis
print("\n[TESTE 1] Estratégias de autenticação disponíveis...")
print("  1. firebaseConfig.json (local)")
print("  2. FIREBASE_CREDENTIALS (env var com JSON completo)")
print("  3. GOOGLE_APPLICATION_CREDENTIALS (env var com caminho)")
print("  4. Application Default Credentials (GCP)")

# Teste 2: Verificar arquivo local
print("\n[TESTE 2] Verificar firebaseConfig.json...")
config_paths = [
    os.path.join(os.path.dirname(__file__), "..", "firebaseConfig.json"),
    os.path.join(os.getcwd(), "firebaseConfig.json"),
]

for config_path in config_paths:
    if os.path.exists(config_path):
        print(f"  [OK] Encontrado: {config_path}")
        try:
            import json
            with open(config_path, 'r') as f:
                data = json.load(f)
            if "type" in data:
                print(f"  [OK] JSON válido com campo 'type'")
            else:
                print(f"  [AVISO] JSON válido mas falta campo 'type'")
        except Exception as e:
            print(f"  [ERRO] JSON inválido: {e}")
    else:
        print(f"  [AVISO] Não encontrado: {config_path}")

# Teste 3: Verificar FIREBASE_CREDENTIALS
print("\n[TESTE 3] Verificar FIREBASE_CREDENTIALS (env var)...")
if os.environ.get("FIREBASE_CREDENTIALS"):
    creds_json = os.environ.get("FIREBASE_CREDENTIALS")
    print(f"  [OK] Variável definida (tamanho: {len(creds_json)} chars)")
    if len(creds_json) < 50:
        print(f"  [AVISO] Muito curta (pode estar truncada)")
    else:
        print(f"  [OK] Tamanho ok ({len(creds_json)} chars)")

    try:
        import json
        data = json.loads(creds_json)
        if "type" in data:
            print(f"  [OK] JSON válido com campo 'type'")
        else:
            print(f"  [AVISO] JSON válido mas falta campo 'type'")
    except json.JSONDecodeError as e:
        print(f"  [ERRO] JSON inválido: {e}")
else:
    print(f"  [AVISO] Variável não definida")

# Teste 4: Verificar GOOGLE_APPLICATION_CREDENTIALS
print("\n[TESTE 4] Verificar GOOGLE_APPLICATION_CREDENTIALS (env var)...")
if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
    gac_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    print(f"  [OK] Variável definida: {gac_path}")
    if os.path.exists(gac_path):
        print(f"  [OK] Arquivo existe")
        try:
            import json
            with open(gac_path, 'r') as f:
                data = json.load(f)
            if "type" in data:
                print(f"  [OK] JSON válido com campo 'type'")
            else:
                print(f"  [AVISO] JSON válido mas falta campo 'type'")
        except Exception as e:
            print(f"  [ERRO] Erro ao ler arquivo: {e}")
    else:
        print(f"  [ERRO] Arquivo não existe")
else:
    print(f"  [AVISO] Variável não definida")

# Teste 5: Tentar inicializar get_db()
print("\n[TESTE 5] Tentar inicializar get_db()...")
try:
    from services.firestore_client import get_db
    print("  [OK] get_db importado com sucesso")

    db = get_db()
    print("  [OK] get_db() retornou cliente Firestore")

    # Teste mínimo: listar coleções
    print("\n[TESTE 6] Teste mínimo: listar coleções...")
    try:
        collections = list(db.collections())
        num_collections = len(collections)
        print(f"  [OK] Conseguiu listar coleções (total: {num_collections})")
        if num_collections > 0:
            print(f"  [OK] Primeiras coleções: {', '.join([c.id for c in collections[:3]])}")
    except Exception as e:
        print(f"  [AVISO] Não conseguiu listar coleções (pode ser permissão): {e}")

    print("\n" + "="*70)
    print("[SUCESSO] Firebase autenticado e funcional!")
    print("="*70)
    print("\nPróximos passos:")
    print("1. python -m pytest tests/runner_p1_identidade_canal_onboarding.py -v")
    print("2. Validar 9/9 testes PASS")
    print("3. python -m pytest tests/runner_p0_regressao_completa.py -v")
    print("4. Validar 174/174 testes PASS")

except Exception as e:
    print(f"  [ERRO] Falha ao inicializar Firebase: {e}")
    print("\n" + "="*70)
    print("[FALHA] Firebase não autenticado")
    print("="*70)
    print("\nSolução:")
    print("1. Verifique firebaseConfig.json ou GOOGLE_APPLICATION_CREDENTIALS")
    print("2. Windows PowerShell: $env:GOOGLE_APPLICATION_CREDENTIALS='C:\\caminho\\firebaseConfig.json'")
    print("3. Git Bash: export GOOGLE_APPLICATION_CREDENTIALS='/c/caminho/firebaseConfig.json'")
    print("4. Reexecute este teste")
    sys.exit(1)
