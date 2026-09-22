import asyncio
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

from firebase_admin import initialize_app, credentials
from services.firebase_service_async import buscar_dado_em_path, salvar_dado_em_path
from services.event_service_async import obter_id_dono
import json

with open('firebase_credentials.json', 'r', encoding='utf-8') as f:
    cred_dict = json.load(f)

try:
    initialize_app(credentials.Certificate(cred_dict))
except:
    pass

async def debug():
    print("\n[DEBUG] Testando obter_id_dono com cliente_maria_001\n")
    
    dono_id = "teste_p0_dono_20260811"
    cliente_maria_id = "cliente_maria_001"
    
    # 1. Criar cliente Maria
    print(f"[1] Criando cliente: {cliente_maria_id}")
    await salvar_dado_em_path(
        f"Clientes/{cliente_maria_id}",
        {
            "tipo_usuario": "cliente",
            "id_negocio": dono_id,
        }
    )
    print(f"    OK - Criado com id_negocio={dono_id}")
    
    # 2. Verificar documento
    print(f"\n[2] Verificando cliente no Firestore:")
    cliente = await buscar_dado_em_path(f"Clientes/{cliente_maria_id}")
    print(f"    id_negocio: {cliente.get('id_negocio') if cliente else 'NOU ENCONTRADO'}")
    
    # 3. Chamar obter_id_dono
    print(f"\n[3] Chamando obter_id_dono('{cliente_maria_id}')")
    resultado = await obter_id_dono(cliente_maria_id)
    print(f"    Retorno: '{resultado}'")
    print(f"    Esperado: '{dono_id}'")
    print(f"    Match: {resultado == dono_id}")

asyncio.run(debug())
