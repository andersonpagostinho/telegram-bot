import re

# Lista simulada de profissionais
profissionais = [
    {"nome": "Gloria", "servicos": ["corte", "escova"]},
    {"nome": "Carla", "servicos": ["coloração", "hidratação"]},
    {"nome": "Amanda", "servicos": ["botox capilar", "luzes"]},
    {"nome": "Joana", "servicos": ["corte", "coloração"]},
]

# Texto simulado do usuário
texto = "quem trabalha aí"

# Detecta intenção de listar todos os profissionais
palavras_chave = [
    "todos os profissionais", "todas as profissionais",
    "quem trabalha aí", "quais são as profissionais", "todo mundo que trabalha"
]

servico_mencionado = None
texto_baixo = texto.lower()

# Simula detecção de serviço
servicos_disponiveis = [s.lower() for p in profissionais for s in p["servicos"]]
for s in servicos_disponiveis:
    if re.search(rf'\b{s}\b', texto_baixo):
        servico_mencionado = s
        break

# Aplica lógica de filtragem
if any(p in texto_baixo for p in palavras_chave):
    profissionais_filtrados = profissionais  # mostra todos
else:
    if servico_mencionado:
        profissionais_filtrados = [
            p for p in profissionais
            if servico_mencionado in [s.lower() for s in p.get("servicos", [])]
        ]
    else:
        profissionais_filtrados = profissionais

# Mostra o resultado
print("👥 Profissionais encontrados:")
for p in profissionais_filtrados:
    print(f"• {p['nome']}: {', '.join(p['servicos'])}")
