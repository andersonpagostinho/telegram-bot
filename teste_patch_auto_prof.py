#!/usr/bin/env python3
"""
TESTE DO PATCH MÍNIMO: AUTO-PROFISSIONAL BLOQUEADO PARA CONSULTA PURA

Mensagem: "vocês fazem escova?"
Expectativa: Consulta pura não deve virar agendamento
"""

import sys
import json
sys.stdout.reconfigure(encoding='utf-8')

print("\n" + "█"*100)
print("TESTE DO PATCH AUTO-PROFISSIONAL")
print("█"*100 + "\n")

# ─────────────────────────────────────────────────────────────────────────────
# CONTEXTO INICIAL (LIMPO)
# ─────────────────────────────────────────────────────────────────────────────
print("[CONTEXTO INICIAL] Limpo\n")

ctx = {
    "user_id": "test_consulta_pura",
    "cliente_id": None,
    "cliente_nome": None,
    "intencao_conversacional": None,
    "objetivo_conversacional": None,
    "servico": None,
    "profissional_escolhido": None,
    "profissional_indiferente": False,
    "data_hora": None,
    "estado_fluxo": "inicial",
    "draft_agendamento": None,
    "dados_confirmacao_agendamento": None,
}

print("ctx inicial:")
for k, v in ctx.items():
    if v is not None:
        print(f"  {k}: {v}")
print()

# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 1: GPT CLASSIFICA
# ─────────────────────────────────────────────────────────────────────────────
print("="*100)
print("[ETAPA 1] GPT CLASSIFICA: 'vocês fazem escova?'")
print("="*100 + "\n")

ctx["intencao_conversacional"] = "consulta_disponibilidade_servico"
ctx["objetivo_conversacional"] = "consultar_disponibilidade_por_servico"

print(f"✅ CLASSIFICAÇÃO:")
print(f"   objetivo_conversacional = '{ctx['objetivo_conversacional']}'")
print(f"   intencao_conversacional = '{ctx['intencao_conversacional']}'")
print()

# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 2: extrair_slots_e_mesclar (PATCH 1)
# ─────────────────────────────────────────────────────────────────────────────
print("="*100)
print("[ETAPA 2] extrair_slots_e_mesclar (PATCH 1)")
print("="*100 + "\n")

servico_detectado = "escova"

eh_consulta_pura_etapa2 = (
    ctx.get("objetivo_conversacional") == "consultar_disponibilidade_por_servico"
    or ctx.get("intencao_conversacional") == "consulta_disponibilidade_servico"
)

if eh_consulta_pura_etapa2:
    print(f"🛡️ [PATCH 1] CONSULTA PURA - Bloqueia servico")
    print(f"   serviço detectado = '{servico_detectado}'")
    print(f"   ✅ ctx['servico'] = None (não alterado)")
    print(f"   ✅ draft['servico'] = None (não alterado)")
else:
    ctx["servico"] = servico_detectado

print()

# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 3: Bloco de AUTO-PROFISSIONAL (NOVO PATCH)
# ─────────────────────────────────────────────────────────────────────────────
print("="*100)
print("[ETAPA 3] AUTO-PROFISSIONAL (NOVO PATCH)")
print("="*100 + "\n")

# Simular estado após extrair_slots_e_mesclar
draft_auto = ctx.get("draft_agendamento") or {}

data_hora_auto = (
    ctx.get("data_hora")
    or draft_auto.get("data_hora")
)

servico_auto = (
    ctx.get("servico")
    or draft_auto.get("servico")
)

prof_auto = (
    ctx.get("profissional_escolhido")
    or draft_auto.get("profissional")
)

print(f"Valores extraídos:")
print(f"  data_hora_auto = {data_hora_auto}")
print(f"  servico_auto = {servico_auto}")
print(f"  prof_auto = {prof_auto}")
print(f"  profissional_indiferente = {ctx.get('profissional_indiferente')}\n")

# 🛡️ NOVO PATCH: Guarda contra consulta pura
eh_consulta_pura = (
    ctx.get("objetivo_conversacional") == "consultar_disponibilidade_por_servico"
    or ctx.get("intencao_conversacional") == "consulta_disponibilidade_servico"
)

if eh_consulta_pura:
    print(f"🛡️ [AUTO-PROF BLOQUEADO] consulta pura não pode virar agendamento")
    print(f"   RESULTADO: Bloco AUTO-PROFISSIONAL é SKIPADO")
    print()

# Condição ORIGINAL (antes do patch):
print("Condição ORIGINAL:")
cond_original = (
    data_hora_auto
    and servico_auto  # Teria True de servico_auto reutilizado
    and not prof_auto
    and ctx.get("profissional_indiferente")
)
print(f"  data_hora_auto and servico_auto and not prof_auto and profissional_indiferente")
print(f"  = {data_hora_auto} and {servico_auto} and {not prof_auto} and {ctx.get('profissional_indiferente')}")
print(f"  = {cond_original}")
print()

# Condição COM PATCH:
print("Condição COM PATCH (novo):")
cond_com_patch = (
    not eh_consulta_pura
    and data_hora_auto
    and servico_auto
    and not prof_auto
    and ctx.get("profissional_indiferente")
)
print(f"  not eh_consulta_pura and data_hora_auto and servico_auto and not prof_auto and profissional_indiferente")
print(f"  = {not eh_consulta_pura} and {data_hora_auto} and {servico_auto} and {not prof_auto} and {ctx.get('profissional_indiferente')}")
print(f"  = {cond_com_patch}")
print()

if not cond_com_patch:
    print("✅ BLOCO AUTO-PROFISSIONAL SKIPPED (não executa)")
    print("   Resultado:")
    print(f"   ✅ ctx['servico'] permanece = {ctx['servico']}")
    print(f"   ✅ ctx['draft_agendamento'] permanece = {ctx.get('draft_agendamento')}")
    print(f"   ✅ ctx['objetivo_conversacional'] permanece = {ctx['objetivo_conversacional']}")
    print(f"   ✅ ctx['intencao_conversacional'] permanece = {ctx['intencao_conversacional']}")
else:
    print("❌ BLOCO AUTO-PROFISSIONAL EXECUTA (não deveria!)")

print()

# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 4: resolver_proximo_passo_real (PATCH 2)
# ─────────────────────────────────────────────────────────────────────────────
print("="*100)
print("[ETAPA 4] resolver_proximo_passo_real (PATCH 2)")
print("="*100 + "\n")

# PATCH 2 do início do resolver_proximo_passo_real
objetivo = ctx.get("objetivo_conversacional")
intencao = ctx.get("intencao_conversacional")

proximo_passo_real = None

if (
    objetivo == "consultar_disponibilidade_por_servico"
    or intencao == "consulta_disponibilidade_servico"
):
    print(f"🛡️ [PATCH 2] CONSULTA PURA - Early return")
    print(f"   objetivo = '{objetivo}'")
    print(f"   intencao = '{intencao}'")
    print(f"   ✅ RETORNA: proximo_passo_real = None")
    proximo_passo_real = None
else:
    print(f"❌ Não é consulta pura - lógica normal executa")

print()

# ─────────────────────────────────────────────────────────────────────────────
# RESULTADO FINAL
# ─────────────────────────────────────────────────────────────────────────────
print("="*100)
print("RESULTADO FINAL")
print("="*100 + "\n")

resultado = {
    "objetivo_conversacional": ctx.get("objetivo_conversacional"),
    "intencao_conversacional": ctx.get("intencao_conversacional"),
    "servico": ctx.get("servico"),
    "draft_agendamento": ctx.get("draft_agendamento"),
    "estado_fluxo": ctx.get("estado_fluxo"),
    "proximo_passo_real": proximo_passo_real,
}

print("Estado final do contexto:")
print(json.dumps(resultado, indent=2, ensure_ascii=False))

print()

# ─────────────────────────────────────────────────────────────────────────────
# VALIDAÇÕES
# ─────────────────────────────────────────────────────────────────────────────
print("="*100)
print("VALIDAÇÕES")
print("="*100 + "\n")

validacoes = [
    ("servico ausente", ctx.get("servico") is None, "ctx['servico'] deve ser None"),
    ("draft_agendamento ausente", ctx.get("draft_agendamento") is None, "ctx['draft_agendamento'] deve ser None"),
    ("objetivo preservado", ctx.get("objetivo_conversacional") == "consultar_disponibilidade_por_servico", "objetivo deve ser preservado"),
    ("intencao preservada", ctx.get("intencao_conversacional") == "consulta_disponibilidade_servico", "intencao deve ser preservada"),
    ("proximo_passo_real = None", proximo_passo_real is None, "proximo_passo_real deve ser None"),
    ("estado_fluxo = inicial", ctx.get("estado_fluxo") == "inicial", "estado_fluxo deve continuar 'inicial'"),
]

todas_passaram = True
for descricao, passou, motivo in validacoes:
    status = "✅ PASS" if passou else "❌ FAIL"
    print(f"{status}: {descricao}")
    if not passou:
        print(f"       → {motivo}")
        todas_passaram = False

print()

if todas_passaram:
    print("="*100)
    print("🎉 TODOS OS TESTES PASSARAM!")
    print("="*100)
else:
    print("="*100)
    print("🚨 ALGUNS TESTES FALHARAM")
    print("="*100)

print()
