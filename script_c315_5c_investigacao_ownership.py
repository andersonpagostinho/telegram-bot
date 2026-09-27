#!/usr/bin/env python3
"""
C3.15.5-C — INVESTIGAÇÃO READ-ONLY DO OWNERSHIP
================================================

Objetivo: Determinar qual actor_id/dono_actor_id é proprietário do tenant 7394370553
usando exclusivamente dados existentes (READ-ONLY).

Restrições:
✅ READ-ONLY apenas
✅ Zero escritas no Firestore
✅ Não inventar actor_id
✅ Não fazer backfill
✅ Não alterar código

Distinguir:
- dono_id
- dono_actor_id
- actor_id
- user_id
- tenant_id
"""

import json
import sys
import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from pathlib import Path
import re

# ✅ INIT Firebase
print("\n" + "="*80)
print("C3.15.5-C — INVESTIGAÇÃO READ-ONLY DO OWNERSHIP")
print("="*80 + "\n")

print("[INIT] 🔥 Inicializando Firebase...")
try:
    app = firebase_admin.get_app()
    db = firestore.client()
    print("[INIT] ✅ Firebase inicializado\n")
except ValueError:
    try:
        cred = credentials.Certificate("firebase_credentials.json")
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("[INIT] ✅ Firebase inicializado\n")
    except Exception as e:
        print(f"[ERROR] ❌ Falha ao inicializar: {str(e)[:200]}")
        sys.exit(1)

# ✅ Configuração
TARGET_TENANT = "7394370553"
SUSPECTED_ACTOR = "5511991382080"  # De investigações anteriores

investigation_report = {
    "tenant_id": TARGET_TENANT,
    "timestamp": datetime.now().isoformat(),
    "campos_identidade_encontrados": {},
    "candidatos_owner": [],
    "evidencias_historicas": [],
    "arquivos_locais_pesquisados": [],
    "conclusao": {
        "owner_determinado": False,
        "actor_id": None,
        "evidencia_explícita": None,
        "força_evidencia": None,
        "caminho_evidencia": None,
        "campo_canonico": None,
    },
    "writes_executadas": 0,
}

# ✅ PASSO 1: Ler Clientes/7394370553 INTEGRALMENTE e listar TODOS os campos
print("[PASSO 1] 📖 Lendo Clientes/7394370553 integralmente...\n")

try:
    cliente_doc = db.collection("Clientes").document(TARGET_TENANT).get()

    if cliente_doc.exists:
        cliente_data = cliente_doc.to_dict()

        print(f"[ENCONTRADO] Clientes/{TARGET_TENANT}")
        print(f"Total de campos: {len(cliente_data)}\n")

        # Listar TODOS os campos e identificar os de identidade/ownership
        campos_identidade = {}

        for key, value in cliente_data.items():
            # Truncar valores longos para exibição
            if isinstance(value, str) and len(value) > 50:
                display_value = value[:50] + "..." if len(value) > 50 else value
            elif isinstance(value, dict):
                display_value = f"<dict com {len(value)} keys>"
            elif isinstance(value, list):
                display_value = f"<list com {len(value)} items>"
            else:
                display_value = str(value)

            print(f"  {key}: {display_value}")

            # Classificar campos de identidade/ownership
            if any(keyword in key.lower() for keyword in ["id", "dono", "actor", "owner", "usuario", "tenant"]):
                campos_identidade[key] = value

        investigation_report["campos_identidade_encontrados"] = {
            k: str(v)[:200] for k, v in campos_identidade.items()
        }

        print(f"\n[IDENTIDADE] Campos de identidade/ownership encontrados:\n")
        for key, value in campos_identidade.items():
            print(f"  ✓ {key}: {value}")

        if not campos_identidade:
            print(f"  ⚠️  Nenhum campo óbvio de identidade/ownership encontrado")

    else:
        print(f"[ERROR] Clientes/{TARGET_TENANT} não existe")
        sys.exit(1)

except Exception as e:
    print(f"[ERROR] Erro ao ler documento: {str(e)[:200]}")
    sys.exit(1)

# ✅ PASSO 2: Procurar evidências históricas dentro do tenant
print("\n\n[PASSO 2] 🔍 Procurando evidências históricas dentro do tenant...\n")

# Verificar todas as subcoleções
subcollections_to_check = [
    "Donos",
    "Comercial",
    "onboarding",
    "sessoes",
    "atores",
    "auditorias",
    "eventos",
    "criacao",
    "configuracao",
    "_metadata",
]

for subcol_name in subcollections_to_check:
    print(f"[CHECK] Procurando em Clientes/{TARGET_TENANT}/{subcol_name}...")

    try:
        subcol_ref = db.collection("Clientes").document(TARGET_TENANT).collection(subcol_name)
        docs = subcol_ref.stream()

        count = 0
        for doc in docs:
            count += 1
            doc_data = doc.to_dict()

            # Procurar por campos de identidade
            identidade_fields = {}
            for key, value in doc_data.items():
                if any(kw in key.lower() for kw in ["id", "dono", "actor", "owner", "usuario", "tenant"]):
                    identidade_fields[key] = value

            if identidade_fields:
                evidence = {
                    "subcoleção": subcol_name,
                    "doc_id": doc.id,
                    "path": f"Clientes/{TARGET_TENANT}/{subcol_name}/{doc.id}",
                    "campos_identidade": identidade_fields,
                    "todos_os_campos": list(doc_data.keys()),
                }

                investigation_report["evidencias_historicas"].append(evidence)

                print(f"  ✅ {subcol_name}/{doc.id}")
                for k, v in identidade_fields.items():
                    print(f"     {k}: {v}")

        if count == 0:
            print(f"  ❌ Subcoleção vazia")

    except Exception as e:
        # Subcoleção pode não existir
        pass

# ✅ PASSO 3: Pesquisar em arquivos locais do projeto
print("\n\n[PASSO 3] 📁 Pesquisando em arquivos locais do projeto...\n")

# Procurar por referências a 7394370553 em arquivos de testes/logs
files_to_search = [
    "teste.py",
    "rastreio_p0_direto.py",
    "rastreio_p0_real.py",
    "teste_firebase.py",
    "handlers/bot.py",
    "handlers/whatsapp_bridge_handler.py",
]

for filepath in files_to_search:
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Procurar por 7394370553 e contexto ao redor
            if TARGET_TENANT in content:
                print(f"[ENCONTRADO] {filepath}")

                # Extrair linhas relevantes
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if TARGET_TENANT in line:
                        # Procurar por assignment ou contexto
                        context_start = max(0, i - 2)
                        context_end = min(len(lines), i + 3)

                        context = '\n'.join([f"  {lines[j]}" for j in range(context_start, context_end)])

                        # Procurar por actor_id ou dono
                        if any(kw in '\n'.join(lines[context_start:context_end]).lower() for kw in ["actor", "dono", "owner"]):
                            print(f"  Linha {i+1}: {line.strip()}")

                            investigation_report["arquivos_locais_pesquisados"].append({
                                "arquivo": filepath,
                                "linha": i + 1,
                                "conteudo": line.strip(),
                                "contexto": context,
                            })
        except Exception as e:
            pass

# ✅ PASSO 4: Verificar se actor_id 5511991382080 aparece associado
print("\n\n[PASSO 4] 🔎 Verificando actor_id suspeito: {}\n".format(SUSPECTED_ACTOR))

suspected_found = False
for evidence in investigation_report["evidencias_historicas"]:
    for key, value in evidence["campos_identidade"].items():
        if SUSPECTED_ACTOR in str(value):
            print(f"  ✅ ENCONTRADO em {evidence['path']}")
            print(f"     Campo: {key} = {value}")
            suspected_found = True

            investigation_report["candidatos_owner"].append({
                "actor_id": SUSPECTED_ACTOR,
                "fonte": "evidência histórica em Firestore",
                "caminho": evidence["path"],
                "campo": key,
                "força_evidencia": "INDIRETA",
                "tipo": "encontrado em subcoleção",
            })

if not suspected_found:
    print(f"  ❌ Actor {SUSPECTED_ACTOR} NÃO encontrado em evidências históricas")

# ✅ PASSO 5: Verificar se existem outros candidatos a owner
print("\n\n[PASSO 5] 🎯 Analisando todos os candidatos encontrados...\n")

if investigation_report["candidatos_owner"]:
    print(f"[CANDIDATOS] Total de candidatos encontrados: {len(investigation_report['candidatos_owner'])}\n")

    for i, candidato in enumerate(investigation_report["candidatos_owner"], 1):
        print(f"[CANDIDATO {i}]")
        print(f"  actor_id: {candidato['actor_id']}")
        print(f"  fonte: {candidato['fonte']}")
        print(f"  caminho: {candidato['caminho']}")
        print(f"  campo: {candidato['campo']}")
        print(f"  força: {candidato['força_evidencia']}\n")
else:
    print(f"[INFO] Nenhum candidato a owner identificado com certeza")

# ✅ PASSO 6: Determinar o contrato canônico
print("\n\n[PASSO 6] 📋 Determinando contrato canônico...\n")

# Procurar por definição de schema em código
print("[PROCURANDO] Definição de dono_id vs dono_actor_id em código...\n")

schema_files = [
    "config/firebase_config.py",
    "services/onboarding_dono_service.py",
    "services/onboarding_service.py",
    "router/integracao_identidade_onboarding.py",
]

schema_findings = []

for schema_file in schema_files:
    if os.path.exists(schema_file):
        try:
            with open(schema_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Procurar por menções de dono_id ou dono_actor_id
            if "dono_id" in content:
                schema_findings.append({
                    "arquivo": schema_file,
                    "campo": "dono_id",
                    "encontrado": True,
                })
                print(f"  ✓ {schema_file} menciona 'dono_id'")

            if "dono_actor_id" in content:
                schema_findings.append({
                    "arquivo": schema_file,
                    "campo": "dono_actor_id",
                    "encontrado": True,
                })
                print(f"  ✓ {schema_file} menciona 'dono_actor_id'")

            if "actor_id" in content:
                schema_findings.append({
                    "arquivo": schema_file,
                    "campo": "actor_id",
                    "encontrado": True,
                })
                print(f"  ✓ {schema_file} menciona 'actor_id'")
        except:
            pass

# ✅ PASSO 7: Compilar conclusão
print("\n\n[PASSO 7] 🎬 Compilando conclusão...\n")

# Lógica para determinar owner
if len(investigation_report["candidatos_owner"]) == 1:
    candidato = investigation_report["candidatos_owner"][0]
    if candidato["força_evidencia"] == "EXPLÍCITA":
        investigation_report["conclusao"]["owner_determinado"] = True
        investigation_report["conclusao"]["actor_id"] = candidato["actor_id"]
        investigation_report["conclusao"]["evidencia_explícita"] = candidato["campo"]
        investigation_report["conclusao"]["caminho_evidencia"] = candidato["caminho"]
        investigation_report["conclusao"]["força_evidencia"] = "EXPLÍCITA"
        investigation_report["conclusao"]["campo_canonico"] = candidato["campo"]
elif len(investigation_report["candidatos_owner"]) > 1:
    # Verificar se há consenso
    actors = [c["actor_id"] for c in investigation_report["candidatos_owner"]]
    if len(set(actors)) == 1:
        # Todos apontam para o mesmo actor
        investigation_report["conclusao"]["owner_determinado"] = True
        investigation_report["conclusao"]["actor_id"] = actors[0]
        investigation_report["conclusao"]["força_evidencia"] = "INDIRETA (múltiplas evidências convergentes)"
        investigation_report["conclusao"]["caminho_evidencia"] = [c["caminho"] for c in investigation_report["candidatos_owner"]]

# Determinar campo canônico a partir de schema findings
campo_preferido = None
if any(f["campo"] == "dono_actor_id" for f in schema_findings):
    campo_preferido = "dono_actor_id"
elif any(f["campo"] == "dono_id" for f in schema_findings):
    campo_preferido = "dono_id"
elif any(f["campo"] == "actor_id" for f in schema_findings):
    campo_preferido = "actor_id"

if campo_preferido:
    investigation_report["conclusao"]["campo_canonico"] = campo_preferido

# ✅ PASSO 8: Relatório final
print("="*80)
print("✅ C3.15.5-C — INVESTIGAÇÃO DO OWNERSHIP")
print("="*80 + "\n")

# Campos de identidade encontrados
print("CAMPOS DE IDENTIDADE ENCONTRADOS EM Clientes/7394370553:")
print("-" * 60)
for key, value in investigation_report["campos_identidade_encontrados"].items():
    print(f"  {key}: {value}")

if not investigation_report["campos_identidade_encontrados"]:
    print("  ❌ Nenhum campo óbvio de identidade/ownership")

# Candidatos encontrados
print("\n\nCANDIDATOS A OWNER IDENTIFICADOS:")
print("-" * 60)

if investigation_report["candidatos_owner"]:
    for i, cand in enumerate(investigation_report["candidatos_owner"], 1):
        print(f"\n[CANDIDATO {i}]")
        print(f"  actor_id: {cand['actor_id']}")
        print(f"  tenant_id: {TARGET_TENANT}")
        print(f"  tipo_usuario: {cand.get('tipo_usuario', 'desconhecido')}")
        print(f"  fonte: {cand['fonte']}")
        print(f"  caminho: {cand['caminho']}")
        print(f"  força: {cand['força_evidencia']}")
else:
    print("  ❌ Nenhum candidato identificado")

# Conclusão
print("\n\nCONCLUSÃO:")
print("="*80)

owner_det = investigation_report["conclusao"]["owner_determinado"]
actor = investigation_report["conclusao"]["actor_id"]
forca = investigation_report["conclusao"]["força_evidencia"]
campo = investigation_report["conclusao"]["campo_canonico"]

if owner_det:
    print(f"\n✅ OWNER_DETERMINADO: SIM")
    print(f"  actor_id: {actor}")
    print(f"  evidência: {investigation_report['conclusao']['evidencia_explícita']}")
    print(f"  força: {forca}")
    print(f"  caminho: {investigation_report['conclusao']['caminho_evidencia']}")
    print(f"  campo canônico: {campo}")
    print(f"\n✅ C3.15.5-C — OWNERSHIP AUDIT: PASS")
else:
    print(f"\n❌ OWNER_DETERMINADO: NÃO")
    print(f"\nMotivo: Evidência insuficiente para determinar owner inequivocamente")

    if investigation_report["candidatos_owner"]:
        print(f"\nCandidatos com evidência parcial:")
        for cand in investigation_report["candidatos_owner"]:
            print(f"  - {cand['actor_id']} (força: {cand['força_evidencia']})")
        print(f"\n⚠️  Nenhum desses candidatos tem evidência EXPLÍCITA suficiente")
    else:
        print(f"\nNão há evidência de qualquer candidato a owner nos dados existentes")

    print(f"\n❌ C3.15.5-C — OWNERSHIP AUDIT: BLOCKED")

# Garantias finais
print("\n\nGARANTIAS CUMPRIDAS:")
print("-" * 60)
print(f"  ✅ WRITES EXECUTADAS: {investigation_report['writes_executadas']}")
print(f"  ✅ Somente leituras no Firestore")
print(f"  ✅ Nenhum documento modificado")
print(f"  ✅ Nenhum código alterado")
print(f"  ✅ Nenhum ator_id inventado")
print(f"\n  {'✅ PASS' if owner_det else '❌ BLOCKED'}: Investigação de ownership")

print("\n" + "="*80 + "\n")

# Salvar relatório
report_file = f"investigacao_c315_5c_{TARGET_TENANT}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(report_file, 'w', encoding='utf-8') as f:
    json.dump(investigation_report, f, indent=2, ensure_ascii=False, default=str)

print(f"Relatório detalhado: {report_file}\n")

sys.exit(0 if owner_det else 1)
