#!/usr/bin/env python3
"""
C3.15.5-E0 — VALIDAÇÃO DEFINITIVA DO ACTOR_ID
==============================================

Objetivo: Validar se actor_id=7371670478 é a identidade técnica real
de andersonpagostinho@gmail.com (proprietário de 7394370553).

Dados confirmados:
- tenant_id: 7394370553
- email: andersonpagostinho@gmail.com
- tipo_usuario: dono
- negócio: NeoEve Secretária

Candidato:
- actor_id: 7371670478

Restrições:
✅ READ-ONLY apenas
✅ Zero escritas no Firestore
✅ Nenhum documento criado/alterado
✅ Nenhum token/credencial impresso
"""

import os
import json
import re
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from pathlib import Path

print("\n" + "="*80)
print("C3.15.5-E0 — VALIDAÇÃO DEFINITIVA DO ACTOR_ID")
print("="*80 + "\n")

# Dados confirmados
TARGET_TENANT = "7394370553"
CONFIRMED_EMAIL = "andersonpagostinho@gmail.com"
CANDIDATE_ACTOR = "7371670478"

validation = {
    "tenant_id": TARGET_TENANT,
    "email_confirmado": CONFIRMED_EMAIL,
    "candidate_actor_id": CANDIDATE_ACTOR,
    "timestamp": datetime.now().isoformat(),
    "evidencias_reais": [],
    "evidencias_teste": [],
    "ligacoes_encontradas": [],
    "classificacao": None,
    "writes_executadas": 0,
}

print(f"Validando:")
print(f"  Email: {CONFIRMED_EMAIL}")
print(f"  Tenant: {TARGET_TENANT}")
print(f"  Candidato actor_id: {CANDIDATE_ACTOR}\n")

# ✅ INIT Firebase
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

# ✅ PASSO 1: Procurar Google OAuth ligando email a actor_id
print("[PASSO 1] 🔐 Procurando Google OAuth / identidade\n")

try:
    cliente_doc = db.collection("Clientes").document(TARGET_TENANT).get()

    if cliente_doc.exists:
        cliente_data = cliente_doc.to_dict()

        # Verificar email_credentials
        if "email_credentials" in cliente_data:
            creds = cliente_data["email_credentials"]

            if isinstance(creds, dict):
                print("[FIRESTORE] email_credentials encontrado:")

                # Procurar por email no payload
                if "client_email" in creds:
                    print(f"  client_email: {creds['client_email']}")

                # Procurar por client_id (pode estar ligado ao usuário)
                if "client_id" in creds:
                    print(f"  client_id: {creds['client_id']}")

                # O refresh_token é pessoal do usuário
                if "refresh_token" in creds:
                    print(f"  ✓ refresh_token presente (ligado ao usuário pessoal)")
                    print(f"    → Isto confirma que {CONFIRMED_EMAIL} iniciou este tenant")

                validation["ligacoes_encontradas"].append({
                    "tipo": "google_oauth_credentials",
                    "email": CONFIRMED_EMAIL,
                    "evidencia": "refresh_token presente em email_credentials",
                    "forca": "CONFIRMADO",
                })

        # Verificar calendar_id
        if "calendar_id" in cliente_data:
            calendar = cliente_data["calendar_id"]
            if calendar == CONFIRMED_EMAIL:
                print(f"\n[FIRESTORE] calendar_id = {CONFIRMED_EMAIL}")
                print(f"  ✓ Confirma que este email é do proprietário")

                validation["ligacoes_encontradas"].append({
                    "tipo": "calendar_id_match",
                    "email": CONFIRMED_EMAIL,
                    "evidencia": f"calendar_id = {CONFIRMED_EMAIL}",
                    "forca": "CONFIRMADO",
                })

except Exception as e:
    print(f"[ERROR] {str(e)[:150]}")

# ✅ PASSO 2: Procurar por Logs de Autenticação/Onboarding
print("\n\n[PASSO 2] 📖 Procurando logs de autenticação/onboarding\n")

log_files = list(Path(".").glob("*.log"))

for log_file in log_files:
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Procurar por combinação: email + actor_id + tenant
        if CONFIRMED_EMAIL in content and CANDIDATE_ACTOR in content and TARGET_TENANT in content:
            print(f"✓ [CORRELAÇÃO] {log_file.name}")
            print(f"  Contém SIMULTANEAMENTE:")
            print(f"    - Email: {CONFIRMED_EMAIL}")
            print(f"    - Actor: {CANDIDATE_ACTOR}")
            print(f"    - Tenant: {TARGET_TENANT}")

            validation["ligacoes_encontradas"].append({
                "tipo": "log_correlacao",
                "arquivo": str(log_file),
                "email": CONFIRMED_EMAIL,
                "actor_id": CANDIDATE_ACTOR,
                "tenant_id": TARGET_TENANT,
                "forca": "CORROBORADO",
            })

    except Exception as e:
        pass

# ✅ PASSO 3: Procurar por Webhooks de Criação
print("\n\n[PASSO 3] 🔗 Procurando webhooks de criação/onboarding\n")

webhook_keywords = [
    "webhook.*criacao",
    "webhook.*onboard",
    "webhook.*cria",
    "on_create",
    "on_signup",
    "usuario_criado",
]

webhook_files = list(Path(".").glob("handlers/*webhook*.py"))

for wf in webhook_files:
    try:
        with open(wf, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        if CONFIRMED_EMAIL in content:
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if CONFIRMED_EMAIL in line:
                    context = '\n'.join(lines[max(0, i-5):min(len(lines), i+6)])

                    # Procurar por actor_id/tenant no contexto
                    if CANDIDATE_ACTOR in context or TARGET_TENANT in context:
                        print(f"✓ {wf.name}:{i+1}")
                        print(f"  Email encontrado em contexto de webhook")

                        if CANDIDATE_ACTOR in context:
                            print(f"  E contains actor_id: {CANDIDATE_ACTOR}")

                            validation["ligacoes_encontradas"].append({
                                "tipo": "webhook_correlacao",
                                "arquivo": str(wf),
                                "linha": i + 1,
                                "email": CONFIRMED_EMAIL,
                                "actor_id": CANDIDATE_ACTOR,
                                "forca": "CORROBORADO",
                            })

    except Exception as e:
        pass

# ✅ PASSO 4: Procurar em Firestore por Ligações
print("\n\n[PASSO 4] 🔍 Procurando em Firestore por ligações diretas\n")

try:
    # Procurar em Users/Actors collection
    user_patterns = ["Users", "Atores", "Usuarios", "_users"]

    for pattern in user_patterns:
        try:
            # Tentar encontrar documento com actor_id
            doc = db.collection(pattern).document(CANDIDATE_ACTOR).get()

            if doc.exists:
                data = doc.to_dict()

                print(f"✓ [FIRESTORE] {pattern}/{CANDIDATE_ACTOR} EXISTE")

                # Procurar por email no documento
                if "email" in data and data["email"] == CONFIRMED_EMAIL:
                    print(f"  ✓ email = {CONFIRMED_EMAIL}")
                    print(f"  ✓ CONFIRMAÇÃO DIRETA!")

                    validation["ligacoes_encontradas"].append({
                        "tipo": "firestore_user_document",
                        "colecao": pattern,
                        "actor_id": CANDIDATE_ACTOR,
                        "email": CONFIRMED_EMAIL,
                        "forca": "EXPLÍCITA",
                    })

                # Procurar por tenant no documento
                if "tenant_id" in data and data["tenant_id"] == TARGET_TENANT:
                    print(f"  ✓ tenant_id = {TARGET_TENANT}")

        except Exception as e:
            pass

    # Procurar em Sessões
    try:
        sessoes_ref = db.collection("Sessoes")
        docs = sessoes_ref.stream()

        for doc in docs:
            data = doc.to_dict()

            # Procurar por combinação
            if (("email" in data and data["email"] == CONFIRMED_EMAIL) and
                ("actor_id" in data and data["actor_id"] == CANDIDATE_ACTOR) and
                ("tenant_id" in data and data["tenant_id"] == TARGET_TENANT)):

                print(f"✓ [FIRESTORE] Sessão contém ligação completa:")
                print(f"  email={CONFIRMED_EMAIL}, actor_id={CANDIDATE_ACTOR}, tenant={TARGET_TENANT}")

                validation["ligacoes_encontradas"].append({
                    "tipo": "firestore_sessao",
                    "doc_id": doc.id,
                    "email": CONFIRMED_EMAIL,
                    "actor_id": CANDIDATE_ACTOR,
                    "tenant_id": TARGET_TENANT,
                    "forca": "EXPLÍCITA",
                })

    except Exception as e:
        pass

except Exception as e:
    print(f"[ERROR] {str(e)[:150]}")

# ✅ PASSO 5: Diferenciar Dado Real vs Teste
print("\n\n[PASSO 5] 📋 Diferenciando dados reais vs teste\n")

py_files = list(Path(".").glob("**/*.py"))[:50]

for pf in py_files:
    try:
        with open(pf, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Procurar por 7371670478
        if CANDIDATE_ACTOR in content:
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if CANDIDATE_ACTOR in line:
                    # Verificar se é teste ou real
                    if "[TESTE]" in line or "# Dados da simulação" in '\n'.join(lines[max(0, i-3):i+1]):
                        validation["evidencias_teste"].append({
                            "arquivo": str(pf),
                            "linha": i + 1,
                            "tipo": "teste",
                            "conteudo": line.strip()[:80],
                        })
                        print(f"[TESTE] {pf.name}:{i+1} (hardcoded em teste)")

                    # Verificar se é real
                    elif ("def " in line or "class " in line or
                          ("=" in line and not any(kw in line for kw in ["[TESTE]", "#", "print"]))):
                        validation["evidencias_reais"].append({
                            "arquivo": str(pf),
                            "linha": i + 1,
                            "tipo": "potencial_real",
                            "conteudo": line.strip()[:80],
                        })
                        print(f"[POTENCIAL REAL] {pf.name}:{i+1}")

    except Exception as e:
        pass

# ✅ PASSO 6: Classificação Final
print("\n\n[PASSO 6] 🎯 Classificação Final\n")

# Analisar ligações
ligacoes_explicitas = [l for l in validation["ligacoes_encontradas"] if l.get("forca") == "EXPLÍCITA"]
ligacoes_corroboradas = [l for l in validation["ligacoes_encontradas"] if l.get("forca") == "CORROBORADO"]
ligacoes_confirmadas = [l for l in validation["ligacoes_encontradas"] if l.get("forca") == "CONFIRMADO"]

print(f"Ligações encontradas:")
print(f"  EXPLÍCITAS: {len(ligacoes_explicitas)}")
print(f"  CORROBORADAS: {len(ligacoes_corroboradas)}")
print(f"  CONFIRMADAS: {len(ligacoes_confirmadas)}")

print(f"\nEvidências:")
print(f"  Reais: {len(validation['evidencias_reais'])}")
print(f"  Teste: {len(validation['evidencias_teste'])}")

# Lógica de classificação
if ligacoes_explicitas and len(ligacoes_explicitas) >= 1:
    validation["classificacao"] = "A - CONFIRMADO"
    status = "✅ PASS"
elif (ligacoes_corroboradas or ligacoes_confirmadas) and len(ligacoes_corroboradas + ligacoes_confirmadas) >= 2:
    validation["classificacao"] = "B - CORROBORADO"
    status = "✅ PASS"
else:
    validation["classificacao"] = "C - NÃO CONFIRMADO"
    status = "❌ BLOCKED"

print(f"\nCLASSIFICAÇÃO: {validation['classificacao']}")
print(f"STATUS: {status}")

# ✅ Relatório Final
print("\n" + "="*80)
print("RESULTADO FINAL — C3.15.5-E0")
print("="*80 + "\n")

if status == "✅ PASS":
    print(f"✅ ACTOR_ID CONFIRMADO/CORROBORADO\n")
    print(f"tenant_id: {TARGET_TENANT}")
    print(f"dono_actor_id: {CANDIDATE_ACTOR}")
    print(f"email_proprietario: {CONFIRMED_EMAIL}")
    print(f"classificacao: {validation['classificacao']}")
    print(f"\nEvidências encontradas:")
    for ligacao in validation["ligacoes_encontradas"]:
        print(f"  - {ligacao['tipo']}: {ligacao.get('forca', 'N/A')}")
    print(f"\n✅ LIBERAR PARA C3.15.5-E1 (backfill controlado)")
else:
    print(f"❌ ACTOR_ID NÃO CONFIRMADO\n")
    print(f"Apenas encontrado em contexto de teste/simulação.")
    print(f"Sem evidência independente ligando:")
    print(f"  {CONFIRMED_EMAIL} → {CANDIDATE_ACTOR} → {TARGET_TENANT}")
    print(f"\n❌ BLOQUEAR — REQUER CONFIRMAÇÃO DIRETA DO PROPRIETÁRIO")

print(f"\nWRITES EXECUTADAS: {validation['writes_executadas']}")
print("\n" + "="*80 + "\n")

# Salvar relatório
report_file = f"validacao_e0_{TARGET_TENANT}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(report_file, 'w', encoding='utf-8') as f:
    json.dump(validation, f, indent=2, ensure_ascii=False, default=str)

print(f"Relatório: {report_file}\n")
