ctx = {}
entidades = {'profissional': 'Carla', 'data': '2026-10-28', 'horario': '10:00'}
if entidades.get('data') and entidades.get('horario'):
    ctx['data_hora'] = f"{entidades['data']}T{entidades['horario']}:00"
    print(f"data_hora setado: {ctx.get('data_hora')}")
else:
    print("Condição falhou")
    print(f"data: {entidades.get('data')}")
    print(f"horario: {entidades.get('horario')}")

intencao_final = "consulta_disponibilidade_aberta"
deve_validar_conflito = (
    intencao_final == "consulta_disponibilidade_aberta"
    and ctx.get("profissional")
    and ctx.get("data_hora")
)
print(f"deve_validar_conflito: {deve_validar_conflito}")
print(f"ctx.get('profissional'): {ctx.get('profissional')}")
