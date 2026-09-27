#!/usr/bin/env python3
"""
C3.15.5 — INVESTIGAÇÃO PROFUNDA FINAL PARA CONFIRMAR OWNER

Objetivo: Encontrar confirmação definitiva do actor_id do proprietário
usando TODOS os dados disponíveis (READ-ONLY).

Estratégias:
1. Analisar calendar_id para extrair identidade
2. Procurar por primeiro acesso ao tenant
3. Procurar por webhooks/eventos de criação
4. Procurar por email_credentials
5. Procurar por telefone/WhatsApp associado
6. Procurar por integração com serviços externos
7. Correlacionar com histórico de commits/logs
"""

import os
import json
import re
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from pathlib import Path

print("\n" + "="*80)
print("C3.15.5 — INVESTIGAÇÃO PROFUNDA FINAL PARA CONFIRMAR OWNER")
print("="*80 + "\n")

TARGET_TENANT = "7394370553"
investigation = {
    "tenant_id": TARGET_TENANT,
    "timestamp": datetime.now().isoformat(),
    "identidades_encontradas": {},
    "candidatos_confirmados": [],
    "evidencia_definitiva": None,
    "writes_executadas": 0,
}

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

# ✅ PASSO 1: Análise Completa do Documento Cliente Base
print("[PASSO 1] 📖 Analisando documento cliente base em profundidade\n")

try:
    cliente_doc = db.collection("Clientes").document(TARGET_TENANT).get()

    if cliente_doc.exists:
        cliente_data = cliente_doc.to_dict()

        print(f"[ENCONTRADO] Clientes/{TARGET_TENANT}\n")
        print("Campos de IDENTIDADE/EMAIL/CONTATO:\n")

        # Extrair todos os identificadores possíveis
        identity_fields = {}

        # Email pessoal
        if "email" in cliente_data and cliente_data["email"]:
            email = cliente_data["email"]
            identity_fields["email"] = email
            print(f"  email: {email}")

        # Calendar ID (Google)
        if "calendar_id" in cliente_data and cliente_data["calendar_id"]:
            calendar = cliente_data["calendar_id"]
            identity_fields["calendar_id"] = calendar
            print(f"  calendar_id: {calendar}")
            print(f"    → POSSÍVEL IDENTIDADE: {calendar}")

        # Email credentials (Google OAuth)
        if "email_credentials" in cliente_data:
            creds = cliente_data["email_credentials"]
            if isinstance(creds, dict):
                if "client_id" in creds:
                    print(f"  email_credentials.client_id: {creds['client_id']}")
                if "client_email" in creds:
                    print(f"  email_credentials.client_email: {creds.get('client_email', 'N/A')}")

        # ID do negócio
        if "id_negocio" in cliente_data:
            print(f"  id_negocio: {cliente_data['id_negocio']}")

        # Tipo de usuário
        if "tipo_usuario" in cliente_data:
            print(f"  tipo_usuario: {cliente_data['tipo_usuario']}")

        # Nome
        if "nome" in cliente_data:
            print(f"  nome: {cliente_data['nome']}")

        # Telefone/WhatsApp
        if "telefone" in cliente_data and cliente_data["telefone"]:
            print(f"  telefone: {cliente_data['telefone']}")

        investigation["identidades_encontradas"] = identity_fields

except Exception as e:
    print(f"[ERROR] {str(e)[:150]}")

# ✅ PASSO 2: Procurar por Webhooks/Eventos de Criação
print("\n\n[PASSO 2] 🔍 Procurando por webhooks/eventos de criação\n")

webhook_patterns = [
    "7394370553",
    "dono",
    "criacao",
    "onboarding",
]

webhook_files = list(Path(".").glob("**/*.py"))[:50]

for wf in webhook_files:
    try:
        with open(wf, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Procurar por padrões de webhook/handler que mencionem o tenant
        if TARGET_TENANT in content:
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if TARGET_TENANT in line and any(kw in content[max(0, (i-5)*100):(i+10)*100].lower() for kw in webhook_patterns):
                    # Procurar por actor_id/phone próximo
                    context = '\n'.join(lines[max(0, i-5):min(len(lines), i+6)])

                    actor_match = re.search(r'(?:actor_id|user_id|phone)["\s:=]+([0-9a-z+\-]+)', context, re.IGNORECASE)
                    if actor_match:
                        actor = actor_match.group(1)
                        if actor not in [TARGET_TENANT, "test", "exemplo"]:
                            print(f"✓ {wf.name}:{i+1} → actor_id: {actor}")

                            investigation["candidatos_confirmados"].append({
                                "arquivo": str(wf),
                                "linha": i + 1,
                                "actor_id": actor,
                                "contexto": line[:100],
                                "tipo": "webhook/evento",
                            })
    except:
        pass

# ✅ PASSO 3: Procurar por Primeiro Acesso / Criação
print("\n\n[PASSO 3] 📅 Procurando por primeiro acesso/criação\n")

# Procurar em arquivos de auditoria por "first_access", "created_by", etc
audit_keywords = [
    "first_access",
    "criado",
    "created_by",
    "created_at",
    "iniciad",
    "iniciou",
    "setup",
    "onboarding_iniciado",
]

audit_files = [
    "scripts/full_audit_firebase.py",
    "scripts/deep_audit_firebase.py",
    "final_audit_before_cleanup.py",
]

for af in audit_files:
    if os.path.exists(af):
        try:
            with open(af, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            if TARGET_TENANT in content:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if TARGET_TENANT in line:
                        # Procurar no contexto
                        context = '\n'.join(lines[max(0, i-10):min(len(lines), i+10)])

                        for keyword in audit_keywords:
                            if keyword in context.lower():
                                # Procurar por actor_id
                                actor_match = re.search(r'(?:actor|user|created_by)["\s:=]+([0-9a-z+\-]+)', context, re.IGNORECASE)
                                if actor_match:
                                    actor = actor_match.group(1)
                                    print(f"✓ {af}:{i+1} (keyword: {keyword}) → actor: {actor}")

                                    investigation["candidatos_confirmados"].append({
                                        "arquivo": af,
                                        "linha": i + 1,
                                        "actor_id": actor,
                                        "keyword": keyword,
                                        "tipo": "auditoria",
                                    })
                                break
        except:
            pass

# ✅ PASSO 4: Correlacionar com WhatsApp/Telefone
print("\n\n[PASSO 4] 📱 Correlacionando com WhatsApp/Telefone\n")

# Procurar por WHATSAPP_NEOEVE_NUMBER e associações
whatsapp_pattern = r'WHATSAPP.*5519\d{7,}'

wa_files = list(Path(".").glob("**/*.py"))[:30]

for wf in wa_files:
    try:
        with open(wf, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        if TARGET_TENANT in content:
            # Procurar por padrão WhatsApp associado
            wa_match = re.search(r'5519\d{7,}', content)
            if wa_match:
                wa_number = wa_match.group(0)
                print(f"✓ {wf.name} → WhatsApp number: {wa_number}")
                print(f"  Possível actor_id: {wa_number}")

                investigation["candidatos_confirmados"].append({
                    "arquivo": str(wf),
                    "actor_id": wa_number,
                    "tipo": "whatsapp_number",
                    "observacao": "Pode ser phone_number_id do proprietário",
                })
    except:
        pass

# ✅ PASSO 5: Analisar Git/Histórico
print("\n\n[PASSO 5] 📜 Procurando em histórico de commits\n")

try:
    import subprocess

    # Procurar por commits que mencionem o tenant
    result = subprocess.run(
        ['git', 'log', '--all', '--oneline', f'--grep={TARGET_TENANT}'],
        capture_output=True,
        text=True,
        timeout=5
    )

    if result.stdout:
        print("[GIT] Commits mencionando o tenant:\n")
        lines = result.stdout.strip().split('\n')
        for line in lines[:5]:
            print(f"  {line}")
    else:
        print("[GIT] Nenhum commit encontrado")

except Exception as e:
    print(f"[INFO] Git não disponível: {str(e)[:50]}")

# ✅ PASSO 6: Consolidar e Classificar Candidatos
print("\n\n[PASSO 6] 🎯 Consolidando candidatos\n")

print(f"Total de candidatos encontrados: {len(investigation['candidatos_confirmados'])}\n")

if investigation["candidatos_confirmados"]:
    # Agrupar por actor_id
    candidatos_por_id = {}
    for cand in investigation["candidatos_confirmados"]:
        actor = cand.get("actor_id")
        if actor:
            if actor not in candidatos_por_id:
                candidatos_por_id[actor] = []
            candidatos_por_id[actor].append(cand)

    # Mostrar resumo
    for actor_id, evidencias in sorted(candidatos_por_id.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"[CANDIDATO] actor_id: {actor_id}")
        print(f"  Menções: {len(evidencias)}")
        for ev in evidencias[:2]:
            print(f"    - Tipo: {ev.get('tipo')}")
            print(f"      Arquivo: {ev.get('arquivo', 'N/A')}")

        # Verificar se é o WhatsApp do tenant
        if actor_id == "5519994443694":
            print(f"  ⚠️  Este é o WHATSAPP_NEOEVE_NUMBER (número do bot, não do proprietário)")
        elif "55199" in str(actor_id):
            print(f"  ⚠️  Parece ser número de telefone/WhatsApp")

        print()

# ✅ PASSO 7: Tentar Confirmar com Lógica
print("\n\n[PASSO 7] 🔐 Tentando confirmar com lógica disponível\n")

# Se temos calendar_id, é a chave
if "calendar_id" in investigation["identidades_encontradas"]:
    calendar = investigation["identidades_encontradas"]["calendar_id"]
    print(f"[CHAVE] Calendar ID encontrado: {calendar}\n")
    print(f"Este é o email pessoal do proprietário.")
    print(f"Porém, sem integração com sistema de usuarios,")
    print(f"não conseguimos extrair o actor_id automaticamente.\n")

    investigation["evidencia_definitiva"] = {
        "tipo": "IDENTIDADE_CONFIRMADA_PARCIALMENTE",
        "email_proprietario": calendar,
        "problema": "Sem mapeamento direto para actor_id no Firestore",
        "solucao": "Contatar proprietário (este email) para confirmar actor_id",
    }

# ✅ RESULTADO FINAL
print("="*80)
print("RESULTADO FINAL DA INVESTIGAÇÃO PROFUNDA")
print("="*80 + "\n")

print(f"Tenant: {TARGET_TENANT}\n")

print("IDENTIDADES ENCONTRADAS:")
for key, value in investigation["identidades_encontradas"].items():
    print(f"  {key}: {value}")

print(f"\nCANDIDATOS A OWNER:")
if investigation["candidatos_confirmados"]:
    candidatos_unicos = set(c.get("actor_id") for c in investigation["candidatos_confirmados"] if c.get("actor_id"))
    for actor in sorted(candidatos_unicos):
        print(f"  - {actor}")
else:
    print(f"  (Nenhum encontrado)")

print(f"\nEVIDÊNCIA DEFINITIVA:")
if investigation["evidencia_definitiva"]:
    print(f"  {json.dumps(investigation['evidencia_definitiva'], indent=2, ensure_ascii=False)}")
else:
    print(f"  Nenhuma evidência definitiva de actor_id em dados técnicos")

print(f"\n" + "="*80)
print("CONCLUSÃO")
print("="*80 + "\n")

if "calendar_id" in investigation["identidades_encontradas"]:
    calendar = investigation["identidades_encontradas"]["calendar_id"]
    print(f"✓ PROPRIETÁRIO CONFIRMADO PARCIALMENTE:")
    print(f"  Email: {calendar}")
    print(f"  Nome: {investigation['identidades_encontradas'].get('nome', 'N/A')}")
    print(f"\n⚠️  Porém: actor_id não foi encontrado em dados técnicos.")
    print(f"\n✅ RECOMENDAÇÃO:")
    print(f"  Contatar: {calendar}")
    print(f"  Pergunta: Qual é seu actor_id/phone_id no NeoEve?")
    print(f"  (Este é o email que deve ser usado para confirmar)")
else:
    print(f"❌ Proprietário não pode ser confirmado com dados disponíveis")

print(f"\nWRITES EXECUTADAS: {investigation['writes_executadas']}")
print("\n" + "="*80 + "\n")

# Salvar relatório
report_file = f"investigacao_profunda_owner_{TARGET_TENANT}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(report_file, 'w', encoding='utf-8') as f:
    json.dump(investigation, f, indent=2, ensure_ascii=False, default=str)

print(f"Relatório detalhado: {report_file}\n")
