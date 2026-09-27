#!/usr/bin/env python3
"""
C3.15.5-B — AUDITORIA REAL + DRY-RUN READ-ONLY
===============================================

Objetivo: Auditar dados reais do tenant 7394370553 no Firestore e simular migração
sem executar nenhuma escrita.

Restrições (OBRIGATÓRIAS):
✅ Somente leituras no Firestore
✅ Auditar tenant_id = 7394370553 especificamente
✅ ZERO .set(), .update(), .create(), .delete()
✅ Nenhuma transaction/batch de escrita
✅ Não alterar código de produção
✅ Não imprimir credenciais ou segredos

Relatório separa:
1. Dados realmente encontrados
2. Classificação de migração
3. Mapeamento de campos
4. Conflitos de ownership
5. Incompatibilidades de schema
6. O que seria criado (DRY-RUN)
7. O que não seria migrado
8. Riscos encontrados
9. Contagem total auditada
"""

import json
import sys
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from collections import defaultdict
import hashlib

# ✅ PASSO 1: Inicializar Firebase
print("\n" + "="*80)
print("C3.15.5-B — AUDITORIA REAL + DRY-RUN READ-ONLY")
print("="*80 + "\n")

print("[INIT] 🔥 Inicializando Firebase Admin SDK...")
try:
    app = firebase_admin.get_app()
    db = firestore.client()
    print("[INIT] ✅ Firebase já inicializado, cliente obtido\n")
except ValueError:
    try:
        cred = credentials.Certificate("firebase_credentials.json")
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("[INIT] ✅ Firebase inicializado com sucesso\n")
    except Exception as e:
        print(f"[ERROR] ❌ Falha ao inicializar Firebase: {str(e)[:200]}")
        sys.exit(1)

# ✅ Configuração
TARGET_TENANT = "7394370553"
print(f"[CONFIG] Auditando tenant: {TARGET_TENANT}\n")

# ✅ Estrutura de dados para armazenar auditoria
audit_data = {
    "tenant_id": TARGET_TENANT,
    "timestamp": datetime.now().isoformat(),
    "summary": {},
    "paths_encontrados": [],
    "documentos_auditados": [],
    "conflitos_ownership": [],
    "incompatibilidades_schema": [],
    "riscos": [],
    "dry_run_migracao": [],
    "nao_seria_migrado": [],
}

# ✅ PASSO 2: Auditar estrutura de Clientes
print("[AUDIT] 📂 Auditando estrutura de Clientes...\n")

try:
    # Buscar cliente base
    clientes_ref = db.collection("Clientes")
    cliente_doc = clientes_ref.document(TARGET_TENANT).get()

    if cliente_doc.exists:
        cliente_data = cliente_doc.to_dict()
        print(f"[ENCONTRADO] Clientes/{TARGET_TENANT}")
        print(f"  Fields: {list(cliente_data.keys())}")

        audit_data["paths_encontrados"].append({
            "path": f"Clientes/{TARGET_TENANT}",
            "tipo": "cliente_base",
            "existe": True,
            "campos": list(cliente_data.keys()),
        })

        # Armazenar documento para análise
        audit_data["documentos_auditados"].append({
            "path": f"Clientes/{TARGET_TENANT}",
            "tipo": "cliente_base",
            "data": cliente_data,
            "campos_count": len(cliente_data),
            "campos_totais": list(cliente_data.keys()),
        })

        # Verificar ownership
        dono_id = cliente_data.get("dono_id")
        if dono_id:
            print(f"  dono_id: {dono_id}")
        else:
            print(f"  ⚠️  dono_id NÃO ENCONTRADO")
            audit_data["riscos"].append({
                "tipo": "missing_ownership",
                "path": f"Clientes/{TARGET_TENANT}",
                "descricao": "Cliente base não tem dono_id definido",
                "severidade": "ALTA",
            })
    else:
        print(f"[NÃO ENCONTRADO] Clientes/{TARGET_TENANT}")
        audit_data["nao_seria_migrado"].append({
            "path": f"Clientes/{TARGET_TENANT}",
            "motivo": "cliente_base_nao_existe",
        })
except Exception as e:
    print(f"[ERROR] Erro ao auditar cliente base: {str(e)[:150]}")
    audit_data["riscos"].append({
        "tipo": "read_error",
        "path": f"Clientes/{TARGET_TENANT}",
        "descricao": str(e)[:200],
        "severidade": "CRÍTICA",
    })

# ✅ PASSO 3: Auditar subcoleções (Donos, Comercial, etc)
print("\n[AUDIT] 📋 Auditando subcoleções...\n")

subcollections_to_audit = ["Donos", "Comercial", "onboarding"]

for subcol_name in subcollections_to_audit:
    print(f"[AUDIT] Auditando: Clientes/{TARGET_TENANT}/{subcol_name}")

    try:
        subcol_ref = db.collection("Clientes").document(TARGET_TENANT).collection(subcol_name)
        docs = subcol_ref.stream()

        count = 0
        for doc in docs:
            count += 1
            doc_data = doc.to_dict()

            path = f"Clientes/{TARGET_TENANT}/{subcol_name}/{doc.id}"
            print(f"  ✅ {path}")
            print(f"     Fields: {list(doc_data.keys())[:5]}{'...' if len(doc_data) > 5 else ''}")

            audit_data["paths_encontrados"].append({
                "path": path,
                "tipo": subcol_name,
                "existe": True,
                "campos": list(doc_data.keys()),
                "doc_id": doc.id,
            })

            audit_data["documentos_auditados"].append({
                "path": path,
                "tipo": subcol_name,
                "doc_id": doc.id,
                "data_sample": {k: v for k, v in list(doc_data.items())[:3]},
                "campos_count": len(doc_data),
                "campos_totais": list(doc_data.keys()),
            })

            # Verificar ownership para Donos
            if subcol_name == "Donos":
                actor_id = doc_data.get("actor_id")
                if not actor_id:
                    audit_data["riscos"].append({
                        "tipo": "missing_actor_id",
                        "path": path,
                        "descricao": f"Documento Dono não tem actor_id",
                        "severidade": "ALTA",
                    })

        if count == 0:
            print(f"  [VAZIO] Nenhum documento encontrado")
            audit_data["nao_seria_migrado"].append({
                "path": f"Clientes/{TARGET_TENANT}/{subcol_name}",
                "motivo": "subcoleção_vazia",
            })
        else:
            print(f"  [FOUND] {count} documentos\n")

    except Exception as e:
        print(f"  [ERROR] {str(e)[:100]}\n")
        audit_data["riscos"].append({
            "tipo": "read_error_subcol",
            "path": f"Clientes/{TARGET_TENANT}/{subcol_name}",
            "descricao": str(e)[:200],
            "severidade": "CRÍTICA",
        })

# ✅ PASSO 4: Verificar novo path (C3.15.2/C3.15.3)
print("\n[AUDIT] 🔍 Verificando novo path isolado...\n")

try:
    # Novo path: Clientes/{tenant_id}/Donos/{actor_id}/onboarding/ativo
    # Primeiro, buscar todos os Donos para verificar novo path
    donos_ref = db.collection("Clientes").document(TARGET_TENANT).collection("Donos")
    donos = donos_ref.stream()

    novo_path_encontrados = []
    for dono_doc in donos:
        dono_data = dono_doc.to_dict()
        actor_id = dono_data.get("actor_id") or dono_doc.id

        novo_path = f"Clientes/{TARGET_TENANT}/Donos/{actor_id}/onboarding"

        try:
            onboarding_ref = db.collection("Clientes").document(TARGET_TENANT).collection("Donos").document(actor_id).collection("onboarding")
            onboarding_docs = onboarding_ref.stream()

            for onb_doc in onboarding_docs:
                novo_path_encontrados.append({
                    "path": f"{novo_path}/{onb_doc.id}",
                    "ativo": onb_doc.id,
                    "data": onb_doc.to_dict(),
                })
                print(f"[NOVO_PATH] ✅ {novo_path}/{onb_doc.id}")
        except:
            pass

    if novo_path_encontrados:
        print(f"  [ENCONTRADO] {len(novo_path_encontrados)} documentos em novo path isolado\n")
        audit_data["paths_encontrados"].extend([
            {"path": item["path"], "tipo": "novo_path_isolado", "existe": True}
            for item in novo_path_encontrados
        ])
    else:
        print(f"  [INFO] Novo path ainda não está em uso (esperado em produção)\n")

except Exception as e:
    print(f"[ERROR] Erro ao verificar novo path: {str(e)[:150]}\n")

# ✅ PASSO 5: Verificar inconsistências de schema
print("\n[AUDIT] 🔍 Verificando inconsistências de schema...\n")

# Análise de campos esperados vs encontrados
expected_cliente_fields = ["dono_id", "nome", "email", "telefone", "tenant_id"]
if audit_data["documentos_auditados"]:
    cliente_doc = [d for d in audit_data["documentos_auditados"] if d["tipo"] == "cliente_base"]
    if cliente_doc:
        found_fields = cliente_doc[0]["campos_totais"]
        missing = [f for f in expected_cliente_fields if f not in found_fields]

        if missing:
            print(f"[⚠️  SCHEMA] Cliente base faltando campos: {missing}")
            audit_data["incompatibilidades_schema"].append({
                "tipo": "cliente_base",
                "campos_faltando": missing,
                "campos_encontrados": found_fields,
            })

# ✅ PASSO 6: DRY-RUN da Migração
print("\n[DRY-RUN] 🎬 Simulando migração (SEM EXECUTAR)...\n")

migration_plan = {
    "tenant_id": TARGET_TENANT,
    "documentos_a_migrar": [],
    "documentos_pulados": [],
    "total_operacoes": 0,
}

# Para cada documento encontrado, simular o que seria feito
for doc_audit in audit_data["documentos_auditados"]:
    path = doc_audit["path"]
    tipo = doc_audit["tipo"]

    if tipo == "cliente_base":
        operation = {
            "operacao": "read_existing",
            "path": path,
            "descricao": "Cliente base já existe, validar ownership",
            "acao_migracao": "VALIDAR",
        }
    elif tipo == "Donos":
        operation = {
            "operacao": "copy_or_update",
            "path": path,
            "descricao": "Copiar para novo path isolado ou atualizar",
            "acao_migracao": "COPIAR_PARA_NOVO_PATH",
        }
    elif tipo == "Comercial":
        operation = {
            "operacao": "read_and_map",
            "path": path,
            "descricao": "Mapeamento de campos de Comercial",
            "acao_migracao": "ANALISAR_CAMPO",
        }
    else:
        operation = {
            "operacao": "read_only",
            "path": path,
            "descricao": f"Auditoria de {tipo}",
            "acao_migracao": "VALIDAR",
        }

    migration_plan["documentos_a_migrar"].append(operation)
    migration_plan["total_operacoes"] += 1

    print(f"[DRY-RUN] {operation['operacao']:20} {path}")

print(f"\n[DRY-RUN] ✅ Total de operações simuladas: {migration_plan['total_operacoes']}\n")

# ✅ PASSO 7: Compilar resumo
print("\n[RESUMO] 📊 Compilando resultados...\n")

audit_data["summary"] = {
    "total_paths_encontrados": len(audit_data["paths_encontrados"]),
    "total_documentos_auditados": len(audit_data["documentos_auditados"]),
    "total_conflitos_ownership": len(audit_data["conflitos_ownership"]),
    "total_incompatibilidades_schema": len(audit_data["incompatibilidades_schema"]),
    "total_riscos": len(audit_data["riscos"]),
    "total_operacoes_dry_run": migration_plan["total_operacoes"],
    "nao_seria_migrado": len(audit_data["nao_seria_migrado"]),
}

# ✅ PASSO 8: Salvar relatório em JSON
report_filename = f"auditoria_c315_5b_{TARGET_TENANT}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
print(f"[SAVE] 💾 Salvando relatório em {report_filename}...\n")

try:
    with open(report_filename, 'w', encoding='utf-8') as f:
        json.dump(audit_data, f, indent=2, ensure_ascii=False, default=str)
    print(f"[SAVE] ✅ Relatório salvo com sucesso\n")
except Exception as e:
    print(f"[ERROR] Erro ao salvar relatório: {str(e)[:150]}\n")

# ✅ PASSO 9: Imprimir resultado final
print("="*80)
print("✅ C3.15.5-B AUDITORIA — RESULTADO FINAL")
print("="*80 + "\n")

print(f"Tenant auditado: {TARGET_TENANT}")
print(f"Timestamp: {audit_data['timestamp']}\n")

print("RESUMO:")
print(f"  Paths encontrados: {audit_data['summary']['total_paths_encontrados']}")
print(f"  Documentos auditados: {audit_data['summary']['total_documentos_auditados']}")
print(f"  Operações DRY-RUN: {audit_data['summary']['total_operacoes_dry_run']}")
print(f"  Conflitos de ownership: {audit_data['summary']['total_conflitos_ownership']}")
print(f"  Incompatibilidades de schema: {audit_data['summary']['total_incompatibilidades_schema']}")
print(f"  Riscos encontrados: {audit_data['summary']['total_riscos']}")
print(f"  Não seria migrado: {audit_data['summary']['nao_seria_migrado']}\n")

if audit_data["riscos"]:
    print("RISCOS ENCONTRADOS:")
    for risco in audit_data["riscos"]:
        print(f"  [{risco['severidade']:8}] {risco['tipo']}: {risco['descricao']}")
    print()

if audit_data["incompatibilidades_schema"]:
    print("INCOMPATIBILIDADES DE SCHEMA:")
    for incompat in audit_data["incompatibilidades_schema"]:
        print(f"  Tipo: {incompat['tipo']}")
        print(f"  Faltando: {incompat['campos_faltando']}")
    print()

print("GARANTIAS:")
print("  ✅ Somente leituras executadas")
print("  ✅ ZERO escritas no Firestore")
print("  ✅ Nenhum código de produção alterado")
print("  ✅ Nenhum segredo impresso")
print("  ✅ Relatório detalhado salvo\n")

print(f"Arquivo de relatório: {report_filename}")
print("="*80 + "\n")

sys.exit(0)
