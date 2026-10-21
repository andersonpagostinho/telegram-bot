import re

files = [
    "C:/dev/neoeve/tests/test_p0_lote1_1_classificacao_e2e_firebase.py",
    "C:/dev/neoeve/tests/test_p0_lote1_2_cancelar_evento_e2e_firebase.py",
    "C:/dev/neoeve/tests/test_p0_lote1_3_confirmacao_cancelamento_e2e_firebase.py",
    "C:/dev/neoeve/tests/test_p0_lote1_4_data_sem_hora_e2e_firebase.py",
    "C:/dev/neoeve/tests/test_p0_lote1_5_extracao_termo_cancelamento_e2e_firebase.py",
]

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern 1: Replace actor_id = f"whatsapp:... with phone_number = ... and full_actor_id = whatsapp:...
    # For T2/T3 in first test
    content = re.sub(
        r'actor_id = f"whatsapp:5511991([^"]+)"',
        r'phone_number = f"5511991\1"\n    full_actor_id = f"whatsapp:{phone_number}"',
        content
    )
    
    content = re.sub(
        r'actor_id = f"whatsapp:5511992([^"]+)"',
        r'phone_number = f"5511992\1"\n    full_actor_id = f"whatsapp:{phone_number}"',
        content
    )
    
    content = re.sub(
        r'actor_id = f"whatsapp:5511993([^"]+)"',
        r'phone_number = f"5511993\1"\n    full_actor_id = f"whatsapp:{phone_number}"',
        content
    )
    
    # Pattern for all other patterns (5511994-5511999, 551200-551205)
    for prefix in range(5511994, 5512000):
        content = re.sub(
            rf'actor_id = f"whatsapp:{prefix}([^"]+)"',
            rf'phone_number = f"{prefix}\1"\n    full_actor_id = f"whatsapp:{{phone_number}}"',
            content
        )
    
    for prefix in range(551200, 551206):
        content = re.sub(
            rf'actor_id = f"whatsapp:{prefix}([^"]+)"',
            rf'phone_number = f"{prefix}\1"\n    full_actor_id = f"whatsapp:{{phone_number}}"',
            content
        )
    
    # Replace user_id=actor_id with user_id=phone_number
    content = re.sub(r'user_id=actor_id,', 'user_id=phone_number,', content)
    
    # Replace paths with actor_id to use full_actor_id
    content = re.sub(
        r'path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{actor_id}"',
        r'path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}"',
        content
    )
    
    # Same for buscar_dado_em_path
    content = re.sub(
        r'buscar_dado_em_path\(f"Clientes/{E2E_TENANT_ID}/Sessoes/{actor_id}"\)',
        r'buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")',
        content
    )
    
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ {file.split('/')[-1]} corrigido")

print("\n✅ Todos os arquivos corrigidos!")
