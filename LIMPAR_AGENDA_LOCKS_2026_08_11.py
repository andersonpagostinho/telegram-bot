import sys
sys.path.insert(0, '.')

from firebase_admin import firestore, initialize_app, credentials
import json

# Carregar credenciais
with open('firebase_credentials.json', 'r', encoding='utf-8') as f:
    cred_dict = json.load(f)

# Inicializar Firebase
try:
    initialize_app(credentials.Certificate(cred_dict))
except:
    pass  # Já inicializado

db = firestore.client()

# Coleções de tenants de teste
tenants = [
    "teste_p0_tenant_a_20260811",
    "teste_p0_dono_20260811",
    "teste_p0_tenant_b_20260811",
    "teste_p0_dono_b_20260811",
]

total_deletado = 0

for tenant in tenants:
    path = f"Clientes/{tenant}/AgendaLocks"
    try:
        locks = db.collection(path).stream()
        count = 0
        for lock_doc in locks:
            lock_doc.reference.delete()
            count += 1
            total_deletado += 1
            print(f"[DELETE] {path}/{lock_doc.id}")
        
        if count > 0:
            print(f"[OK] {path}: {count} locks deletados")
    except Exception as e:
        print(f"[ERRO] {path}: {str(e)}")

print(f"\n[RESUMO] Total de AgendaLocks deletados: {total_deletado}")
