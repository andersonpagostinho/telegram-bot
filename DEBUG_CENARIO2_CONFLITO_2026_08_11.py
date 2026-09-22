import asyncio
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

from firebase_admin import initialize_app, credentials
from services.firebase_service_async import salvar_dado_em_path, buscar_subcolecao
from services.event_service_async import verificar_conflito_e_sugestoes_profissional
from services.agenda_lock_service import criar_evento_com_lock as criar_com_lock_real
import json

with open('firebase_credentials.json', 'r', encoding='utf-8') as f:
    cred_dict = json.load(f)

try:
    initialize_app(credentials.Certificate(cred_dict))
except:
    pass

async def debug():
    print("\n[DEBUG] Cenario 2 - Investigando deteccao de conflito em 15h\n")
    
    tenant = "teste_p0_tenant_a_20260811"
    profissional = "Bruno"
    data = "2026-08-15"
    
    # 1. Criar evento bloqueante (15:00-15:30)
    print(f"[1] Criando evento bloqueante: 15:00-15:30")
    resultado_bloquante = await criar_com_lock_real(
        dono_id=tenant,
        evento={
            "profissional": profissional,
            "servico": "Barba",
            "data": data,
            "hora_inicio": "15:00",
            "hora_fim": "15:30",
            "duracao_minutos": 30,
            "confirmado": True,
            "status": "confirmado",
            "cliente_id": "cliente_003",
            "cliente_nome": "Cliente 003",
        },
        event_id="evt_c2_bloqueante",
    )
    if resultado_bloquante.get("ok"):
        print(f"    OK - Evento bloqueante criado")
    else:
        print(f"    ERRO - {resultado_bloquante}")
    
    # 2. Listar eventos do Bruno
    print(f"\n[2] Listando eventos do profissional {profissional} em {data}")
    eventos = await buscar_subcolecao(f"Clientes/{tenant}/Eventos", filters={
        "profissional": profissional,
        "data": data
    })
    for evt in eventos:
        print(f"    - {evt['id']}: {evt.get('hora_inicio')}-{evt.get('hora_fim')}")
    
    # 3. Chamar verificar_conflito_e_sugestoes_profissional
    print(f"\n[3] Chamando verificar_conflito para 15:00 (ignora evt_c2_alter)")
    resultado = await verificar_conflito_e_sugestoes_profissional(
        user_id=tenant,
        data=data,
        hora_inicio="15:00",
        duracao_min=30,
        profissional=profissional,
        servico="Corte",
        event_id="evt_c2_alter"  # Deve ignorar este
    )
    
    print(f"    conflito: {resultado.get('conflito')}")
    print(f"    sugestoes: {resultado.get('sugestoes', [])}")
    print(f"\n    ESPERADO: conflito=True, sugestoes != []")

asyncio.run(debug())
