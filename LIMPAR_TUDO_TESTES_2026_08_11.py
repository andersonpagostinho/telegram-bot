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
    pass

db = firestore.client()

# Tenants de teste
tenants = [
    "teste_p0_tenant_a_20260811",
    "teste_p0_dono_20260811",
    "teste_p0_tenant_b_20260811",
    "teste_p0_dono_b_20260811",
]

print("[LIMPEZA] Deletando documentos de teste...")

for tenant in tenants:
    # Deletar eventos
    eventos_ref = db.collection(f"Clientes/{tenant}/Eventos")
    for doc in eventos_ref.stream():
        doc.reference.delete()
        print(f"[DELETE] Clientes/{tenant}/Eventos/{doc.id}")
    
    # Deletar locks
    locks_ref = db.collection(f"Clientes/{tenant}/AgendaLocks")
    for doc in locks_ref.stream():
        doc.reference.delete()
        print(f"[DELETE] Clientes/{tenant}/AgendaLocks/{doc.id}")
    
    # Deletar tenant
    try:
        db.document(f"Clientes/{tenant}").delete()
        print(f"[DELETE] Clientes/{tenant}")
    except:
        pass

print("\n[OK] Limpeza completa realizada")
