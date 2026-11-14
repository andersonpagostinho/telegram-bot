#!/usr/bin/env python3
import re

msg = "Consigo chegar a partir das 14h, mas tenho um compromisso no final do dia e preciso terminar os dois serviços até, no máximo, 17h."
msg_lower = msg.lower()

print("="*80)
print("[TEST 1] PADRÃO 1: 'das 14 às 17'")
print("="*80)
match1 = re.search(
    r"(?:das?|de)?\s*(\d{1,2})(?::00|h)?\s*(?:as?|às?)\s*(\d{1,2})(?::00|h)?",
    msg_lower,
    re.IGNORECASE
)
if match1:
    print(f"OK MATCH: ({match1.group(1)}, {match1.group(2)})")
else:
    print("NO MATCH")

print("\n" + "="*80)
print("[TEST 2] PADRÃO 2: 'a partir de' + 'até'")
print("="*80)

# Part 1: "a partir de"
match_inicio = re.search(r"a partir d(?:e|as?)\s*(\d{1,2})(?::00|h)?", msg_lower)
if match_inicio:
    inicio = int(match_inicio.group(1))
    print(f"OK INICIO: {inicio}")
else:
    inicio = None
    print("NO INICIO")

# Part 2: "até" (SEM \s+ obrigatório)
match_fim = re.search(r"(?:até|ate)[^0-9]*?(\d{1,2})(?::00|h)?", msg_lower)
if match_fim:
    fim = int(match_fim.group(1))
    print(f"OK FIM (com fix): {fim}")
else:
    fim = None
    print("NO FIM")

# Part 2b: "até" (COM \s+ obrigatório — versão antiga)
match_fim_old = re.search(r"(?:até|ate)\s+[^0-9]*?(\d{1,2})(?::00|h)?", msg_lower)
if match_fim_old:
    fim_old = int(match_fim_old.group(1))
    print(f"WARN FIM (versão antiga com \\s+): {fim_old}")
else:
    fim_old = None
    print("NO FIM (versão antiga com \\s+)")

print(f"\n>> Resultado PADRÃO 2: ({inicio}, {fim})")

if inicio is not None or fim is not None:
    result = (inicio, fim)
    print(f"OK FINAL: {result}")
else:
    print("FAIL FINAL: (None, None)")

print("\n" + "="*80)
print("[CONCLUSAO]")
print("="*80)
if match1:
    print(f"PADRÃO 1 RETORNARIA: ({match1.group(1)}, {match1.group(2)})")
elif inicio is not None:
    print(f"PADRÃO 2 RETORNARIA: ({inicio}, {fim})")
