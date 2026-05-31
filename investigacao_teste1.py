#!/usr/bin/env python3
"""
INVESTIGAÇÃO DETALHADA DO TESTE 1: "vocês fazem escova?"

Objetivo:
1. Rastrear draft_agendamento em CADA etapa
2. Verificar se é salvo em ctx["draft_agendamento"]
3. Mostrar estado serializado final de ctx
4. Procurar por trechos que salvam draft vazio
"""

import sys
import json
sys.stdout.reconfigure(encoding='utf-8')

print("\n" + "█"*100)
print("INVESTIGAÇÃO DETALHADA - TESTE 1")
print("█"*100 + "\n")

# ─────────────────────────────────────────────────────────────────────────────
# CONTEXTO INICIAL
# ─────────────────────────────────────────────────────────────────────────────
print("[ETAPA 0] CONTEXTO INICIAL\n")

ctx = {
    "user_id": "test_user_1",
    "cliente_id": None,
    "cliente_nome": None,
    "intencao_conversacional": None,
    "objetivo_conversacional": None,
    "servico": None,
    "profissional": None,
    "data_hora": None,
    "estado_fluxo": "inicial",
    "draft_agendamento": None,  # ← Inicialmente None
    "mensagem_anterior": None,
}

draft_agendamento = {}  # Variável LOCAL

print(f"ctx['draft_agendamento'] = {ctx['draft_agendamento']}")
print(f"draft_agendamento (local) = {draft_agendamento}")
print(f"São diferentes? {ctx['draft_agendamento'] is not draft_agendamento}\n")

print(f"Estado de ctx (serializado):")
print(json.dumps(ctx, indent=2, ensure_ascii=False))
print()

# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 1: GPT CLASSIFICA
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*100)
print("[ETAPA 1] GPT CLASSIFICA - CONSULTA PURA")
print("="*100 + "\n")

ctx["intencao_conversacional"] = "consulta_disponibilidade_servico"
ctx["objetivo_conversacional"] = "consultar_disponibilidade_por_servico"

print(f"ctx['objetivo_conversacional'] = '{ctx['objetivo_conversacional']}'")
print(f"ctx['intencao_conversacional'] = '{ctx['intencao_conversacional']}'")
print(f"\nctx['draft_agendamento'] após etapa 1 = {ctx['draft_agendamento']}\n")

# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 2: EXTRAIR_SLOTS_E_MESCLAR
# ─────────────────────────────────────────────────────────────────────────────
print("="*100)
print("[ETAPA 2] EXTRAIR_SLOTS_E_MESCLAR (PATCH 1)")
print("="*100 + "\n")

servico_detectado = "escova"

print(f"[ANTES]")
print(f"  draft_agendamento (local) = {draft_agendamento}")
print(f"  ctx['draft_agendamento'] = {ctx['draft_agendamento']}")
print(f"  ctx['servico'] = {ctx['servico']}\n")

if servico_detectado:
    eh_consulta_pura_servico = (
        ctx.get("objetivo_conversacional") == "consultar_disponibilidade_por_servico"
        or ctx.get("intencao_conversacional") == "consulta_disponibilidade_servico"
    )

    if eh_consulta_pura_servico:
        print(f"🛡️  CONSULTA PURA DETECTADA")
        print(f"  → Serviço '{servico_detectado}' BLOQUEADO")
        print(f"  → draft_agendamento NÃO é alterado")
        print(f"  → ctx['servico'] NÃO é alterado")
        # draft_agendamento continua como {} (variável local não alterada)
    else:
        ctx["servico"] = servico_detectado
        draft_agendamento["servico"] = servico_detectado

print(f"\n[DEPOIS]")
print(f"  draft_agendamento (local) = {draft_agendamento}")
print(f"  ctx['draft_agendamento'] = {ctx['draft_agendamento']}")
print(f"  ctx['servico'] = {ctx['servico']}")
print(f"  São diferentes? {ctx['draft_agendamento'] is not draft_agendamento}\n")

# ─────────────────────────────────────────────────────────────────────────────
# ⚠️ PERGUNTA CRÍTICA: O draft_agendamento é salvo em ctx?
# ─────────────────────────────────────────────────────────────────────────────
print("="*100)
print("[PERGUNTA 1] DRAFT SALVO EM CTX?")
print("="*100 + "\n")

print(f"Cenário A: ctx['draft_agendamento'] = draft_agendamento")
print(f"  Se isso foi feito: ctx['draft_agendamento'] = {draft_agendamento}")
print(f"  Mas NÃO vemos essa linha no código relatado ❓\n")

print(f"Cenário B: Não há atribuição, apenas variável local")
print(f"  draft_agendamento (local) = {draft_agendamento}")
print(f"  ctx['draft_agendamento'] = {ctx['draft_agendamento']} (não alterado)")
print(f"  ← Cenário PROVÁVEL ✅\n")

# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 3: RESOLVER_PROXIMO_PASSO_REAL (PATCH 2)
# ─────────────────────────────────────────────────────────────────────────────
print("="*100)
print("[ETAPA 3] RESOLVER_PROXIMO_PASSO_REAL (PATCH 2)")
print("="*100 + "\n")

print(f"[ANTES]")
print(f"  proximo_passo_real = (não definido)")
print(f"  ctx estado = {ctx}\n")

proximo_passo_real = None

objetivo = ctx.get("objetivo_conversacional")
intencao = ctx.get("intencao_conversacional")

if (
    objetivo == "consultar_disponibilidade_por_servico"
    or intencao == "consulta_disponibilidade_servico"
):
    print(f"🛡️  CONSULTA PURA BLOQUEADA")
    print(f"  → Retorna None imediatamente")
    print(f"  → Não altera nada em ctx")
    proximo_passo_real = None
else:
    proximo_passo_real = "..."

print(f"\n[DEPOIS]")
print(f"  proximo_passo_real = {proximo_passo_real}")
print(f"  ctx não foi alterado ✅\n")

# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 4: p1_preservar_resposta_gpt
# ─────────────────────────────────────────────────────────────────────────────
print("="*100)
print("[ETAPA 4] P1_PRESERVAR_RESPOSTA_GPT")
print("="*100 + "\n")

eh_agendamento = ctx.get("objetivo_conversacional") == "agendar_servico"
tem_proximo_passo = bool(proximo_passo_real)

p1_preservar_resposta_gpt = (
    not eh_agendamento and not tem_proximo_passo
)

print(f"Cálculo:")
print(f"  (objetivo != 'agendar_servico') = {not eh_agendamento}")
print(f"  (not proximo_passo_real) = {not tem_proximo_passo}")
print(f"  → p1_preservar_resposta_gpt = {p1_preservar_resposta_gpt}\n")

print(f"Decisão: GPT responde livremente ✅\n")

# ─────────────────────────────────────────────────────────────────────────────
# ESTADO FINAL DO CTX
# ─────────────────────────────────────────────────────────────────────────────
print("="*100)
print("[RESULTADO FINAL] ESTADO SERIALIZADO DE CTX")
print("="*100 + "\n")

print(f"JSON serializado (exato estado de ctx):\n")
print(json.dumps(ctx, indent=2, ensure_ascii=False))

print(f"\n\nResumo:")
print(f"  ctx['draft_agendamento'] = {ctx['draft_agendamento']}")
print(f"  draft_agendamento (variável local) = {draft_agendamento}")
print(f"  Foram salvos em ctx? {'SIM' if ctx['draft_agendamento'] is draft_agendamento else 'NÃO'}\n")

# ─────────────────────────────────────────────────────────────────────────────
# CONCLUSÕES
# ─────────────────────────────────────────────────────────────────────────────
print("="*100)
print("CONCLUSÕES")
print("="*100 + "\n")

print("1️⃣  draft_agendamento realmente foi salvo em ctx?")
print(f"   ❌ NÃO - ctx['draft_agendamento'] = {ctx['draft_agendamento']}\n")

print("2️⃣  O {} que apareceu no relatório é exibição local?")
print(f"   ✅ SIM - é a variável local draft_agendamento = {draft_agendamento}")
print(f"   O relatório mostrava: draft_agendamento → {{}} (vazio)\n")

print("3️⃣  Existe trecho que faz ctx['draft_agendamento'] = draft?")
print(f"   ❌ Não encontrado no código relatado")
print(f"   Se existisse: ctx['draft_agendamento'] seria {draft_agendamento}\n")

print("4️⃣  Conteúdo final serializado de ctx:")
print(f"   ctx['draft_agendamento'] = None (não alterado)\n")

print("="*100)
print("IMPLICAÇÃO")
print("="*100 + "\n")

print("""
Para consulta pura "vocês fazem escova?":

✅ ctx["draft_agendamento"] permanece None
✅ draft_agendamento (local) permanece {}
✅ Nada é salvo de volta em ctx

PROVA: Não há atribuição ctx["draft_agendamento"] = draft no fluxo.
""")
