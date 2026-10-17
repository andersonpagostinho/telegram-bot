#!/usr/bin/env python3
"""Auditoria: função _normalizar_hora()"""

def _normalizar_hora(hora_str: str) -> str:
    """Normaliza hora para formato HH:MM."""
    partes = hora_str.split(":")
    horas = partes[0].zfill(2)
    minutos = partes[1].zfill(2)
    return f"{horas}:{minutos}"

print("=" * 70)
print("AUDITORIA: _normalizar_hora()")
print("=" * 70)

# Teste 1: Entrada padrão com zero à esquerda
testes_validos = [
    ("9:00", "09:00"),
    ("09:00", "09:00"),
    ("9:30", "09:30"),
    ("12:00", "12:00"),
    ("0:00", "00:00"),
    ("23:59", "23:59"),
]

print("\n[TESTE 1] Valores válidos:")
for entrada, esperado in testes_validos:
    try:
        resultado = _normalizar_hora(entrada)
        status = "✓ PASS" if resultado == esperado else f"✗ FAIL (got {resultado})"
        print(f"  {entrada:10} → {resultado:10} (esperado {esperado:10}) {status}")
    except Exception as e:
        print(f"  {entrada:10} → ERROR: {e}")

# Teste 2: Valores inválidos (sem `:`)
print("\n[TESTE 2] Valores inválidos (sem separador):")
testes_invalidos = ["900", "9", "9h00"]
for entrada in testes_invalidos:
    try:
        resultado = _normalizar_hora(entrada)
        print(f"  {entrada:10} → {resultado:10} (RESULTADO: sem validação prévia)")
    except Exception as e:
        print(f"  {entrada:10} → ERROR: {e} (esperado - função não valida)")

# Teste 3: Chame a função com a mesma entrada 2x (idempotência)
print("\n[TESTE 3] Idempotência (normalizar 2x):")
for entrada, _ in testes_validos[:3]:
    resultado1 = _normalizar_hora(entrada)
    resultado2 = _normalizar_hora(resultado1)
    status = "✓ IDEMPOTENT" if resultado1 == resultado2 else "✗ NOT IDEMPOTENT"
    print(f"  {entrada} → {resultado1} → {resultado2} {status}")

# Teste 4: Onde são usados os valores
print("\n[TESTE 4] Uso em agenda_padrao (Firestore):")
inicio = _normalizar_hora("9:00")
fim = _normalizar_hora("18:00")
print(f"  agenda_padrao['0'] = {{'aberto': True, 'inicio': '{inicio}', 'fim': '{fim}'}}")
print(f"  Tipo de 'inicio': {type(inicio).__name__}")
print(f"  Tipo de 'fim': {type(fim).__name__}")

print("\n" + "=" * 70)
print("CONCLUSÃO:")
print("=" * 70)
print("✓ Função normaliza 'H:MM' → 'HH:MM' adicionando zero à esquerda")
print("✓ Função NÃO valida entrada (aceita qualquer string com ':')")
print("✓ Função é idempotente (normalizar 2x = mesma saída)")
print("✓ Valores salvos em Firestore como strings com formato HH:MM")
