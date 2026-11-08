from services.classificador_conversa import classificar_intencao_conversacional

# Caso 1: "deixa pra la" SEM contexto operacional
resultado1 = classificar_intencao_conversacional(
    "deixa pra la",
    {},
    ["corte feminino", "manicure"],
    ["Bruna", "Gloria", "Joana", "Carla"]
)

print(f"[CASO 1] sem contexto: {resultado1['intencao_conversacional']}")

# Caso 2: "deixa pra la" com draft
resultado2 = classificar_intencao_conversacional(
    "deixa pra la",
    {
        "draft_agendamento": {"servico": "corte", "profissional": "Bruna"},
        "estado_fluxo": "agendando"
    },
    ["corte feminino", "manicure"],
    ["Bruna", "Gloria", "Joana", "Carla"]
)

print(f"[CASO 2] com draft: {resultado2['intencao_conversacional']}")

if resultado1['intencao_conversacional'] == 'cancelamento':
    print("RISCO: deixa pra la isolada retorna cancelamento")
else:
    print("OK: deixa pra la isolada nao cancela sem contexto")
