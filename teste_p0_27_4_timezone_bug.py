"""
P0.27.4 — Teste para identificar bug de timezone

Problema: Linha 959 em agenda_lock_service.py:
  agora = datetime.now()  ← NAIVE (sem timezone)

Mas Firestore retorna:
  expira_em: "2026-10-21T22:00:00.119453"  ← Pode ter timezone

Comparação entre datetime com e sem timezone pode falhar!
"""

from datetime import datetime
from pytz import timezone

FUSO_BR = timezone("America/Sao_Paulo")

# Simulando dados do Firestore
expira_em_str = "2026-10-21T22:00:00.119453"  # Expirado (20 out < 5 nov)

print("="*80)
print("P0.27.4 — TESTE DE TIMEZONE")
print("="*80)

print(f"\nData de expiração (Firestore): {expira_em_str}")
print(f"Hoje: 2026-11-05")

# Teste 1: Como P0.27.3 faz (BUGADO)
print(f"\n{'-'*80}")
print("TESTE 1: Lógica atual (línha 959 + 982)")
print(f"{'-'*80}")

try:
    agora = datetime.now()  # NAIVE
    expira_em = datetime.fromisoformat(expira_em_str)  # Pode ter tzinfo

    print(f"agora = datetime.now()")
    print(f"  Valor: {agora}")
    print(f"  Tzinfo: {agora.tzinfo}")
    print(f"  É naive? {agora.tzinfo is None}")

    print(f"\nexpira_em = datetime.fromisoformat(...)")
    print(f"  Valor: {expira_em}")
    print(f"  Tzinfo: {expira_em.tzinfo}")
    print(f"  É aware? {expira_em.tzinfo is not None}")

    # Tentativa de comparação
    print(f"\nComparação: expira_em > agora")
    resultado = expira_em > agora
    print(f"  ✓ FUNCIONA: {resultado}")
    print(f"  Interpretação: Lock está {'válido' if resultado else 'EXPIRADO'}")

except TypeError as e:
    print(f"  ❌ TypeError na comparação: {e}")
except Exception as e:
    print(f"  ❌ Erro: {e}")

# Teste 2: Forma correta (com FUSO_BR)
print(f"\n{'-'*80}")
print("TESTE 2: Lógica corrigida (com timezone)")
print(f"{'-'*80}")

try:
    agora_correto = datetime.now(FUSO_BR)  # COM timezone
    expira_em = datetime.fromisoformat(expira_em_str)

    # Se expira_em é naive, adicionar timezone
    if expira_em.tzinfo is None:
        expira_em = FUSO_BR.localize(expira_em)

    print(f"agora = datetime.now(FUSO_BR)")
    print(f"  Valor: {agora_correto}")
    print(f"  Tzinfo: {agora_correto.tzinfo}")

    print(f"\nexpira_em (com timezone se necessário)")
    print(f"  Valor: {expira_em}")
    print(f"  Tzinfo: {expira_em.tzinfo}")

    print(f"\nComparação: expira_em > agora")
    resultado = expira_em > agora_correto
    print(f"  ✓ FUNCIONA: {resultado}")
    print(f"  Interpretação: Lock está {'válido' if resultado else 'EXPIRADO'}")

    expirado = expira_em <= agora_correto
    print(f"\nCritério P0.27.3 (expira_em <= agora): {expirado}")

except Exception as e:
    print(f"  ❌ Erro: {e}")

# Teste 3: Verificar se locks de Bruna deveriam ser identificados
print(f"\n{'-'*80}")
print("TESTE 3: Aplicar ao caso de Bruna 10:00 em 2026-11-06")
print(f"{'-'*80}")

# Dados reais de Bruna
bruna_expira_em = "2026-10-21T22:00:00.119453"
bruna_timestamp_lock = "2026-10-20T22:00:00.119453"

print(f"\nLock de Bruna:")
print(f"  timestamp_lock: {bruna_timestamp_lock}")
print(f"  expira_em: {bruna_expira_em}")
print(f"  status: confirmado")
print(f"  evento_id: (seria buscado)")

print(f"\nHoje: 2026-11-05 (15:00 São Paulo)")

agora_br = datetime.now(FUSO_BR)
expira_br = datetime.fromisoformat(bruna_expira_em)

# Localize se naive
if expira_br.tzinfo is None:
    expira_br = FUSO_BR.localize(expira_br)

expirado = expira_br <= agora_br
print(f"\nExpira_em <= agora: {expirado}")
print(f"  expira_em: {expira_br}")
print(f"  agora: {agora_br}")

if expirado:
    print(f"\n✓ Lock DEVERIA SER IDENTIFICADO COMO EXPIRADO")
else:
    print(f"\n❌ Lock NÃO seria identificado (ainda válido)")

# Teste 4: Entender por que P0.27.3 retornou 0
print(f"\n{'-'*80}")
print("TESTE 4: Diagnóstico — por que P0.27.3 retornou 0?")
print(f"{'-'*80}")

print(f"""
Possíveis causas:

1. **Timezone mismatch** (PROVÁVEL)
   - `datetime.now()` é naive, Firestore pode ter aware
   - Comparação pode falhar silenciosamente

2. **Locks NÃO estão expirados**
   - `expira_em > agora` retorna True (ainda válido)
   - Locks com data de 20 out deveriam estar expirados em 5 nov
   - Mas se há erro de conversão, comparação fica errada

3. **Evento correspondente EXISTE**
   - Um dos eventos foi encontrado (ID legado?)
   - Não seria classificado como órfão

4. **Status não é "confirmado"**
   - Status foi alterado para outro valor
   - Função ignora (linha 973: `if ... != "confirmado": continue`)

5. **Lock_id não foi retornado corretamente**
   - `lock_item.get("id")` retorna None
   - Lock é ignorado (linha 969: `if not lock_id: continue`)
""")

print(f"\n{'='*80}")
print("RECOMENDAÇÃO: Adicionar logging à P0.27.3 para cada lock processado")
print(f"{'='*80}\n")
