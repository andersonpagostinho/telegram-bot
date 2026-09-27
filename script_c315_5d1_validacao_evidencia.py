#!/usr/bin/env python3
"""
C3.15.5-D.1 — VALIDAÇÃO DA EVIDÊNCIA DE OWNERSHIP
==================================================

Objetivo: Determinar se actor_id=7371670478 pode ser considerado OWNER
do tenant_id=7394370553 com evidência suficiente.

Restrições:
✅ READ-ONLY apenas
✅ Zero escritas no Firestore
✅ Nenhuma alteração de código
✅ Nenhum backfill
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path

print("\n" + "="*80)
print("C3.15.5-D.1 — VALIDAÇÃO DA EVIDÊNCIA DE OWNERSHIP")
print("="*80 + "\n")

TARGET_TENANT = "7394370553"
CANDIDATE_ACTOR = "7371670478"

validation = {
    "tenant_id": TARGET_TENANT,
    "candidate_actor_id": CANDIDATE_ACTOR,
    "timestamp": datetime.now().isoformat(),
    "analise_origem": {},
    "corroboracoes_independentes": [],
    "outros_atores_encontrados": [],
    "aparicoes_em_outro_tenant": [],
    "evidencia_como_dono": [],
    "classificacao_final": None,
    "justificativa": None,
    "writes_executadas": 0,
}

# ✅ PASSO 1: Analisar rastreio_p0_direto.py
print("[PASSO 1] 📖 Analisando rastreio_p0_direto.py\n")

rastreio_direto = "rastreio_p0_direto.py"
if os.path.exists(rastreio_direto):
    with open(rastreio_direto, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    lines = content.split('\n')

    # Procurar por todas as ocorrências do actor
    print(f"Procurando por '{CANDIDATE_ACTOR}' em {rastreio_direto}...\n")

    ocorrencias = []
    for i, line in enumerate(lines):
        if CANDIDATE_ACTOR in line:
            context_start = max(0, i - 10)
            context_end = min(len(lines), i + 10)
            context = '\n'.join([f"{j+1:4}: {lines[j]}" for j in range(context_start, context_end)])

            ocorrencias.append({
                "linha": i + 1,
                "conteudo": line.strip(),
                "contexto_antes": '\n'.join(lines[max(0, i-5):i]),
                "contexto_depois": '\n'.join(lines[i+1:min(len(lines), i+6)]),
                "contexto_full": context,
            })

            print(f"[LINHA {i+1}] {line.strip()}")

    validation["analise_origem"][rastreio_direto] = {
        "total_ocorrencias": len(ocorrencias),
        "detalhes": ocorrencias,
    }

    # Analisar cada ocorrência
    if ocorrencias:
        print(f"\nTotal de ocorrências: {len(ocorrencias)}\n")

        for i, occ in enumerate(ocorrencias, 1):
            print(f"[OCORRÊNCIA {i}] Linha {occ['linha']}")
            print(f"Conteúdo: {occ['conteudo']}\n")

            # Determinar origem do valor
            if "=" in occ['conteudo']:
                # É uma atribuição
                if "user_id" in occ['conteudo']:
                    print(f"  → Origem: ATRIBUIÇÃO de user_id")
                    print(f"  → Tipo: Variável local")

                    # Procurar onde user_id vem de
                    for j in range(max(0, occ['linha']-20), occ['linha']):
                        if "user_id" in lines[j] and "=" in lines[j] and j < occ['linha']-1:
                            print(f"  → Definição anterior (linha {j+1}): {lines[j].strip()}")

                elif "input(" in occ['conteudo'] or "read" in occ['conteudo'].lower():
                    print(f"  → Origem: ENTRADA DO USUÁRIO")
                    print(f"  → Tipo: Informado manualmente")
                else:
                    print(f"  → Origem: HARDCODED")
                    print(f"  → Tipo: Valor literal no código")
            else:
                print(f"  → Origem: REFERÊNCIA de variável anterior")
                print(f"  → Tipo: Reutilização")

            print()

# ✅ PASSO 2: Analisar rastreio_p0_real.py
print("\n\n[PASSO 2] 📖 Analisando rastreio_p0_real.py\n")

rastreio_real = "rastreio_p0_real.py"
if os.path.exists(rastreio_real):
    with open(rastreio_real, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    lines = content.split('\n')

    print(f"Procurando por '{CANDIDATE_ACTOR}' em {rastreio_real}...\n")

    ocorrencias = []
    for i, line in enumerate(lines):
        if CANDIDATE_ACTOR in line:
            context_start = max(0, i - 10)
            context_end = min(len(lines), i + 10)
            context = '\n'.join([f"{j+1:4}: {lines[j]}" for j in range(context_start, context_end)])

            ocorrencias.append({
                "linha": i + 1,
                "conteudo": line.strip(),
                "contexto_antes": '\n'.join(lines[max(0, i-5):i]),
                "contexto_depois": '\n'.join(lines[i+1:min(len(lines), i+6)]),
                "contexto_full": context,
            })

            print(f"[LINHA {i+1}] {line.strip()}")

    validation["analise_origem"][rastreio_real] = {
        "total_ocorrencias": len(ocorrencias),
        "detalhes": ocorrencias,
    }

    # Analisar cada ocorrência
    if ocorrencias:
        print(f"\nTotal de ocorrências: {len(ocorrencias)}\n")

        for i, occ in enumerate(ocorrencias, 1):
            print(f"[OCORRÊNCIA {i}] Linha {occ['linha']}")
            print(f"Conteúdo: {occ['conteudo']}\n")

            # Mesmo padrão de análise
            if "=" in occ['conteudo']:
                if "user_id" in occ['conteudo']:
                    print(f"  → Origem: ATRIBUIÇÃO de user_id")
                    print(f"  → Tipo: Variável local")
                elif "input(" in occ['conteudo'] or "read" in occ['conteudo'].lower():
                    print(f"  → Origem: ENTRADA DO USUÁRIO")
                    print(f"  → Tipo: Informado manualmente")
                else:
                    print(f"  → Origem: HARDCODED")
                    print(f"  → Tipo: Valor literal no código")
            else:
                print(f"  → Origem: REFERÊNCIA de variável anterior")
                print(f"  → Tipo: Reutilização")

            print()

# ✅ PASSO 3: Procurar corroboração independente
print("\n\n[PASSO 3] 🔍 Procurando corroboração independente\n")

print("[CHECK] Firestore - Procurando por evidência de ownership\n")

try:
    import firebase_admin
    from firebase_admin import credentials, firestore

    try:
        app = firebase_admin.get_app()
        db = firestore.client()
    except ValueError:
        try:
            cred = credentials.Certificate("firebase_credentials.json")
            firebase_admin.initialize_app(cred)
            db = firestore.client()
        except:
            db = None

    if db:
        # Procurar em Firestore por associação explícita
        print("Procurando em Firestore...\n")

        # Check 1: Clientes/{tenant}/Donos/{actor_id}
        try:
            dono_doc = db.collection("Clientes").document(TARGET_TENANT).collection("Donos").document(CANDIDATE_ACTOR).get()
            if dono_doc.exists:
                print(f"✓ [FIRESTORE] Clientes/{TARGET_TENANT}/Donos/{CANDIDATE_ACTOR} EXISTE")
                print(f"  Dados: {dono_doc.to_dict()}")

                validation["corroboracoes_independentes"].append({
                    "tipo": "FIRESTORE",
                    "força": "EXPLÍCITA",
                    "caminho": f"Clientes/{TARGET_TENANT}/Donos/{CANDIDATE_ACTOR}",
                    "conteudo": str(dono_doc.to_dict())[:200],
                })
        except:
            print(f"✗ [FIRESTORE] Clientes/{TARGET_TENANT}/Donos/{CANDIDATE_ACTOR} não existe")

        # Check 2: Procurar em onboarding
        try:
            onboarding_docs = db.collection("Clientes").document(TARGET_TENANT).collection("onboarding").stream()
            count = 0
            for doc in onboarding_docs:
                count += 1
                if CANDIDATE_ACTOR in str(doc.to_dict()):
                    print(f"✓ [FIRESTORE] Onboarding contém referência a {CANDIDATE_ACTOR}")

                    validation["corroboracoes_independentes"].append({
                        "tipo": "FIRESTORE_ONBOARDING",
                        "força": "INDIRETA",
                        "caminho": f"Clientes/{TARGET_TENANT}/onboarding/{doc.id}",
                        "conteudo": str(doc.to_dict())[:200],
                    })

            if count == 0:
                print(f"✗ [FIRESTORE] Nenhum documento de onboarding encontrado")
        except:
            pass

        # Check 3: Procurar sessões com esse actor
        try:
            sessao_docs = db.collection("Clientes").document(TARGET_TENANT).collection("sessoes").stream()
            count = 0
            for doc in sessao_docs:
                count += 1
                if CANDIDATE_ACTOR in str(doc.to_dict()):
                    print(f"✓ [FIRESTORE] Sessão contém {CANDIDATE_ACTOR}")

                    validation["corroboracoes_independentes"].append({
                        "tipo": "FIRESTORE_SESSAO",
                        "força": "INDIRETA",
                        "caminho": f"Clientes/{TARGET_TENANT}/sessoes/{doc.id}",
                    })

            if count == 0:
                print(f"✗ [FIRESTORE] Nenhuma sessão encontrada")
        except:
            pass

        # Check 4: Procurar por outros atores no mesmo tenant
        print(f"\n[CHECK] Procurando por OUTROS atores no tenant {TARGET_TENANT}...\n")

        try:
            donos_docs = db.collection("Clientes").document(TARGET_TENANT).collection("Donos").stream()
            outros_count = 0
            for doc in donos_docs:
                otros_count += 1
                actor_id = doc.id
                if actor_id != CANDIDATE_ACTOR:
                    print(f"  ✓ Encontrado outro ator: {actor_id}")

                    validation["outros_atores_encontrados"].append({
                        "actor_id": actor_id,
                        "caminho": f"Clientes/{TARGET_TENANT}/Donos/{actor_id}",
                    })

            if outros_count == 0:
                print(f"  ✗ Nenhum outro ator encontrado")
        except:
            pass

    else:
        print("❌ Firestore não está inicializado, pulando verificações de banco")

except Exception as e:
    print(f"[ERROR] Erro ao acessar Firestore: {str(e)[:150]}")

# ✅ PASSO 4: Procurar se o actor aparece em outro tenant
print("\n\n[PASSO 4] 🔎 Verificando se {0} aparece em outro tenant\n".format(CANDIDATE_ACTOR))

# Procurar em arquivos
py_files = list(Path(".").glob("**/*.py"))[:30]

for py_file in py_files:
    try:
        with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Procurar por padrão: CANDIDATE_ACTOR + tenant_id (que não é TARGET_TENANT)
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if CANDIDATE_ACTOR in line:
                # Procurar no contexto por outro tenant_id
                context = '\n'.join(lines[max(0, i-5):min(len(lines), i+6)])

                # Procurar por tenant_id diferente
                other_tenants = re.findall(r'tenant_id["\s:=]+([0-9]+)', context, re.IGNORECASE)
                for tenant in other_tenants:
                    if tenant != TARGET_TENANT:
                        print(f"✓ [ENCONTRADO] {py_file.name}:{i+1}")
                        print(f"  {CANDIDATE_ACTOR} aparece com tenant_id={tenant}")

                        validation["aparicoes_em_outro_tenant"].append({
                            "arquivo": str(py_file),
                            "linha": i + 1,
                            "outro_tenant": tenant,
                            "contexto": line[:100],
                        })
    except:
        pass

if not validation["aparicoes_em_outro_tenant"]:
    print(f"✓ [CONFIRMADO] {CANDIDATE_ACTOR} NÃO aparece em outro tenant")

# ✅ PASSO 5: Procurar evidência de que atuou como DONO
print("\n\n[PASSO 5] 👑 Procurando evidência de que {0} atuou como DONO\n".format(CANDIDATE_ACTOR))

dono_keywords = [
    "tipo_usuario.*dono",
    "is_dono",
    "dono_actor_id",
    "owner",
    "proprietario",
    "criador",
    "iniciou_onboarding",
]

for py_file in py_files:
    try:
        with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        lines = content.split('\n')
        for i, line in enumerate(lines):
            if CANDIDATE_ACTOR in line:
                # Procurar por keywords de ownership no contexto
                context = '\n'.join(lines[max(0, i-5):min(len(lines), i+6)])

                for keyword in dono_keywords:
                    if re.search(keyword, context, re.IGNORECASE):
                        print(f"✓ [ENCONTRADO] {py_file.name}:{i+1}")
                        print(f"  Keyword: {keyword}")
                        print(f"  Contexto: {line[:100]}")

                        validation["evidencia_como_dono"].append({
                            "arquivo": str(py_file),
                            "linha": i + 1,
                            "keyword": keyword,
                        })
                        break
    except:
        pass

if not validation["evidencia_como_dono"]:
    print(f"✗ Nenhuma evidência de que {CANDIDATE_ACTOR} atuou como DONO")

# ✅ PASSO 6: Classificação Final
print("\n\n[PASSO 6] 📊 Classificação Final\n")

num_corroboracoes = len(validation["corroboracoes_independentes"])
tem_firestore_explicit = any(c["força"] == "EXPLÍCITA" for c in validation["corroboracoes_independentes"])
tem_evidencia_dono = len(validation["evidencia_como_dono"]) > 0

print(f"Corroborações independentes: {num_corroboracoes}")
print(f"Tem evidência EXPLÍCITA em Firestore: {tem_firestore_explicit}")
print(f"Tem evidência como DONO: {tem_evidencia_dono}")
print(f"Aparece em outro tenant: {len(validation['aparicoes_em_outro_tenant']) > 0}")
print(f"Outros atores no mesmo tenant: {len(validation['outros_atores_encontrados'])}")

print("\n\nDECISÃO:")
print("-" * 60)

if tem_firestore_explicit:
    validation["classificacao_final"] = "A - EXPLÍCITA"
    validation["justificativa"] = "Existe registro real em Firestore que estabelece diretamente o ownership"
    status = "✅ PASS"
elif num_corroboracoes >= 2 and all(c["força"] != "CONTEXTUAL" for c in validation["corroboracoes_independentes"]):
    validation["classificacao_final"] = "B - CORROBORADA"
    validation["justificativa"] = "Existem múltiplas fontes independentes consistentes que estabelecem a associação"
    status = "✅ PASS"
elif num_corroboracoes >= 1 or tem_evidencia_dono:
    validation["classificacao_final"] = "C - CONTEXTUAL"
    validation["justificativa"] = "A associação aparece somente em scripts/rastreios/contexto, sem comprovação independente"
    status = "❌ BLOCKED"
else:
    validation["classificacao_final"] = "D - INSUFICIENTE"
    validation["justificativa"] = "Não é possível estabelecer ownership com segurança"
    status = "❌ BLOCKED"

print(f"\n{status}: Classificação {validation['classificacao_final']}")
print(f"\nJustificativa: {validation['justificativa']}")

if status == "❌ BLOCKED":
    print(f"\n⚠️  NÃO LIBERAR BACKFILL SEM VALIDAÇÃO ADICIONAL")

# ✅ Relatório final
print("\n" + "="*80)
print("RESULTADO FINAL")
print("="*80 + "\n")

print(f"Tenant: {TARGET_TENANT}")
print(f"Candidate actor_id: {CANDIDATE_ACTOR}")
print(f"Classificação: {validation['classificacao_final']}")
print(f"Justificativa: {validation['justificativa']}\n")

print(f"OWNER_DETERMINADO: {'SIM' if status == '✅ PASS' else 'NÃO'}")
print(f"WRITES EXECUTADAS: {validation['writes_executadas']}")

print(f"\n{status}")

if status == "✅ PASS":
    print(f"\n✅ C3.15.5-D.1 — VALIDAÇÃO: PASS")
    print(f"Evidência suficiente para backfill técnico")
else:
    print(f"\n❌ C3.15.5-D.1 — VALIDAÇÃO: BLOCKED")
    print(f"Evidência INSUFICIENTE para backfill")

print("\n" + "="*80 + "\n")

# Salvar relatório
report_file = f"validacao_c315_5d1_{TARGET_TENANT}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(report_file, 'w', encoding='utf-8') as f:
    json.dump(validation, f, indent=2, ensure_ascii=False, default=str)

print(f"Relatório detalhado: {report_file}\n")
