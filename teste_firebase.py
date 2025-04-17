from services.firebase_service_async import salvar_dado_em_path, buscar_subcolecao

user_id = "7394370553"
event_id = "evento_teste_firebase"

evento_data = {
    "descricao": "Teste de salvamento",
    "data": "2025-03-25",
    "hora_inicio": "14:00",
    "hora_fim": "15:00",
    "confirmado": False,
    "link": "https://exemplo.com/evento-teste"
}

# 🔹 Tenta salvar o evento em um caminho aninhado
print("🔹 Salvando no Firebase...")
sucesso = salvar_dado_em_path(f"Clientes/{user_id}/Eventos/{event_id}", evento_data)

if sucesso:
    print("✅ Evento de teste salvo com sucesso!")
else:
    print("❌ Falha ao salvar o evento.")

# 🔹 Agora tenta buscar para ver se foi salvo corretamente
print("\n🔍 Buscando subcoleção de eventos...")
eventos = buscar_subcolecao(f"Clientes/{user_id}/Eventos")

if eventos:
    print("✅ Eventos encontrados:")
    for eid, ev in eventos.items():
        print(f"📌 {eid}: {ev}")
else:
    print("❌ Nenhum evento encontrado.")
