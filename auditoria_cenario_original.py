from services.classificador_conversa import classificar_intencao_conversacional

# Cenário exato da auditoria original
draft_antigo = {
    "servico": "corte feminino",
    "profissional": "Bruna",
    "data_hora": "2026-11-03T09:00:00"  # Data passada
}

contexto = {
    "draft_agendamento": draft_antigo,
    "estado_fluxo": "agendando",
    "profissional_escolhido": "Bruna",
    "aguardando_confirmacao_agendamento": False  # Nenhuma confirmacao pendente
}

resultado = classificar_intencao_conversacional(
    "desculpe, nao era com voce, enviei errado.",
    contexto,
    ["corte feminino", "manicure"],
    ["Bruna", "Gloria", "Joana", "Carla"]
)

print("=" * 70)
print("CENARIO ORIGINAL DA AUDITORIA")
print("=" * 70)
print(f"Mensagem: 'desculpe, nao era com voce, enviei errado.'")
print(f"Draft: {draft_antigo}")
print()
print("Resultado:")
print(f"  intencao_conversacional: {resultado['intencao_conversacional']}")
print(f"  tipo_ajuste: {resultado.get('tipo_ajuste_incremental')}")
print(f"  confianca: {resultado['confianca']}")
print()
print("Features:")
print(f"  tem_ref_profissional: {resultado['features']['tem_ref_profissional']}")
print(f"  tem_referencia_pessoa_profissional: {resultado['features']['tem_referencia_pessoa_profissional']}")
print(f"  tem_draft: {resultado['features']['tem_draft']}")
print(f"  tem_fluxo_ativo: {resultado['features']['tem_fluxo_ativo']}")
print()

expected = "indefinida"
actual = resultado['intencao_conversacional']

if actual == expected:
    print(f"✅ CORRETO: Retorna '{expected}' (mensagem neutra nao operacional)")
else:
    print(f"❌ ERRO: Retorna '{actual}' em vez de '{expected}'")
    print(f"   Este era o bug original!")
