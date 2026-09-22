import asyncio
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

from firebase_admin import initialize_app, credentials
from services.firebase_service_async import buscar_dado_em_path
from services.event_service_async import obter_id_dono
import json

with open('firebase_credentials.json', 'r', encoding='utf-8') as f:
    cred_dict = json.load(f)

try:
    initialize_app(credentials.Certificate(cred_dict))
except:
    pass

async def debug():
    print("\n[DEBUG] Cenario 3 - Investigando id_negocio de cliente_maria_001\n")
    
    dono_id = "teste_p0_dono_20260811"
    cliente_maria_id = "cliente_maria_001"
    evento_id = "evt_c3_maria"
    
    # 1. Verificar documento do dono
    print(f"[1] Verificando dono: {dono_id}")
    dono = await buscar_dado_em_path(f"Clientes/{dono_id}")
    if dono:
        print(f"    OK - Dono encontrado")
        print(f"    id_negocio: {dono.get('id_negocio')}")
    else:
        print(f"    ERRO - Dono NAO encontrado!")
    
    # 2. Verificar documento do cliente Maria
    print(f"\n[2] Verificando cliente: {cliente_maria_id}")
    cliente_maria = await buscar_dado_em_path(f"Clientes/{cliente_maria_id}")
    if cliente_maria:
        print(f"    OK - Cliente encontrado")
        print(f"    id_negocio: {cliente_maria.get('id_negocio')}")
    else:
        print(f"    ERRO - Cliente NAO encontrado!")
        print(f"    ^^ CAUSA RAIZ DO CENARIO 3")
    
    # 3. Verificar evento de Maria
    print(f"\n[3] Verificando evento: {evento_id}")
    evento = await buscar_dado_em_path(f"Clientes/{dono_id}/Eventos/{evento_id}")
    if evento:
        print(f"    OK - Evento encontrado em: Clientes/{dono_id}/Eventos/{evento_id}")
        print(f"    cliente_id: {evento.get('cliente_id')}")
    else:
        print(f"    ERRO - Evento NAO encontrado em {dono_id}!")
    
    # 4. Listar todos os clientes em Firestore
    print(f"\n[4] Listar todos os documentos em Clientes/ raiz:")
    from firebase_admin import firestore
    db = firestore.client()
    docs = db.collection("Clientes").list_documents()
    for doc in docs:
        print(f"    - {doc.id}")

asyncio.run(debug())
