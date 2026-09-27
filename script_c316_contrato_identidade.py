#!/usr/bin/env python3
"""
C3.16 — CONTRATO DE IDENTIDADE DE ATORES
==========================================

Objetivo: Responder de forma DETERMINÍSTICA:

1. Como nasce um actor_id?
2. Quem pode criar um dono?
3. Quem pode criar um profissional?
4. Quem pode criar um cliente?
5. Como um WhatsApp novo é associado a um actor_id?
6. Como o sistema diferencia dono/profissional/cliente?
7. O mesmo telefone pode existir em tenants diferentes?
8. O que acontece quando o mesmo cliente usa o NeoEve em dois salões?
9. Como funciona troca de número?
10. Como funciona profissional que trabalha em dois tenants?
11. Qual é a fonte de verdade da identidade?
12. Qual documento Firestore representa o vínculo?
13. Como impedir que um cliente seja confundido com profissional?
14. Como impedir que um ator de Tenant A seja resolvido no Tenant B?
15. Como onboarding e WhatsApp compartilham essa identidade?

Restrições:
- READ-ONLY
- Sem escrever Firestore
- Procurar evidência no código
"""

import os
import re
from pathlib import Path
from datetime import datetime
import json

print("\n" + "="*80)
print("C3.16 — CONTRATO DE IDENTIDADE DE ATORES")
print("="*80 + "\n")

contratos = {
    "timestamp": datetime.now().isoformat(),
    "questoes": {}
}

# ✅ QUESTÃO 1: Como nasce um actor_id?
print("[Q1] 🆔 Como nasce um actor_id?\n")

questao_1 = {
    "pergunta": "Como nasce um actor_id?",
    "evidencias": [],
    "resposta": None,
}

# Procurar por uuid, uuid5, phone, etc
py_files = list(Path(".").glob("**/*.py"))[:50]

for pf in py_files:
    try:
        with open(pf, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Procurar por geração de ID
        if re.search(r'uuid\.uuid5|uuid5|uuid4|generate.*id|create.*actor', content, re.IGNORECASE):
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if re.search(r'uuid\.uuid5|uuid5|uuid4|actor.*=|actor_id.*=', line, re.IGNORECASE):
                    questao_1["evidencias"].append({
                        "arquivo": pf.name,
                        "linha": i + 1,
                        "conteudo": line.strip()[:100],
                        "tipo": "geração_id",
                    })
                    print(f"  ✓ {pf.name}:{i+1}")
                    print(f"    {line.strip()[:80]}")
    except:
        pass

if questao_1["evidencias"]:
    print(f"\nEvidências encontradas: {len(questao_1['evidencias'])}\n")
else:
    print(f"⚠️  Nenhuma evidência de geração de actor_id encontrada\n")

contratos["questoes"]["1_nascimento_actor_id"] = questao_1

# ✅ QUESTÃO 2-4: Permissões para criar atores
print("\n[Q2-4] 👥 Quem pode criar dono/profissional/cliente?\n")

questao_234 = {
    "pergunta": "Quem pode criar dono/profissional/cliente?",
    "evidencias_dono": [],
    "evidencias_profissional": [],
    "evidencias_cliente": [],
    "resposta": None,
}

# Procurar por verificações de permissão
for pf in py_files:
    try:
        with open(pf, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        lines = content.split('\n')
        for i, line in enumerate(lines):
            if re.search(r'criar.*dono|create.*dono|is_dono|type.*dono', line, re.IGNORECASE):
                questao_234["evidencias_dono"].append({
                    "arquivo": pf.name,
                    "linha": i + 1,
                    "conteudo": line.strip()[:100],
                })
                print(f"  ✓ [DONO] {pf.name}:{i+1}")

            if re.search(r'criar.*profissional|create.*professional|is_profissional', line, re.IGNORECASE):
                questao_234["evidencias_profissional"].append({
                    "arquivo": pf.name,
                    "linha": i + 1,
                    "conteudo": line.strip()[:100],
                })
                print(f"  ✓ [PROF] {pf.name}:{i+1}")

            if re.search(r'criar.*cliente|create.*client|is_cliente', line, re.IGNORECASE):
                questao_234["evidencias_cliente"].append({
                    "arquivo": pf.name,
                    "linha": i + 1,
                    "conteudo": line.strip()[:100],
                })
                print(f"  ✓ [CLIENTE] {pf.name}:{i+1}")
    except:
        pass

print(f"\nDono: {len(questao_234['evidencias_dono'])} evidências")
print(f"Profissional: {len(questao_234['evidencias_profissional'])} evidências")
print(f"Cliente: {len(questao_234['evidencias_cliente'])} evidências\n")

contratos["questoes"]["2_4_criar_atores"] = questao_234

# ✅ QUESTÃO 5: Como WhatsApp novo é associado a actor_id?
print("\n[Q5] 📱 Como um WhatsApp novo é associado a um actor_id?\n")

questao_5 = {
    "pergunta": "Como um WhatsApp novo é associado a um actor_id?",
    "evidencias": [],
    "resposta": None,
}

wa_files = list(Path(".").glob("handlers/*whatsapp*"))

for wf in wa_files:
    try:
        with open(wf, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Procurar por resolver_tenant_por_endpoint, phone_number_id, etc
        if re.search(r'phone_number_id|resolver_tenant|associate.*phone|from_number', content, re.IGNORECASE):
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if re.search(r'phone_number_id|from_number|actor_id.*phone|phone.*actor', line, re.IGNORECASE):
                    questao_5["evidencias"].append({
                        "arquivo": wf.name,
                        "linha": i + 1,
                        "conteudo": line.strip()[:100],
                    })
                    print(f"  ✓ {wf.name}:{i+1}")
                    print(f"    {line.strip()[:80]}")
    except:
        pass

if not questao_5["evidencias"]:
    # Procurar em serviços
    service_files = list(Path("services").glob("*whatsapp*.py"))
    for sf in service_files:
        try:
            with open(sf, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            if re.search(r'phone|actor|user', content, re.IGNORECASE):
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'from' in line or 'user_id' in line or 'actor_id' in line:
                        questao_5["evidencias"].append({
                            "arquivo": sf.name,
                            "linha": i + 1,
                            "conteudo": line.strip()[:100],
                        })
                        print(f"  ✓ {sf.name}:{i+1}")
        except:
            pass

print()

contratos["questoes"]["5_whatsapp_associacao"] = questao_5

# ✅ QUESTÃO 6: Como o sistema diferencia dono/profissional/cliente?
print("\n[Q6] 🏷️ Como o sistema diferencia dono/profissional/cliente?\n")

questao_6 = {
    "pergunta": "Como o sistema diferencia dono/profissional/cliente?",
    "campos_encontrados": set(),
    "evidencias": [],
}

# Procurar por tipo_usuario, role, tipo, etc
for pf in py_files:
    try:
        with open(pf, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        lines = content.split('\n')
        for i, line in enumerate(lines):
            if re.search(r'tipo_usuario|role|tipo.*usuario|user_type', line, re.IGNORECASE):
                match = re.search(r'(tipo_usuario|role|tipo|type)["\s:=]+(["\']?)([a-z_]+)', line, re.IGNORECASE)
                if match:
                    campo = match.group(1)
                    valor = match.group(3)
                    questao_6["campos_encontrados"].add(f"{campo}={valor}")
                    questao_6["evidencias"].append({
                        "arquivo": pf.name,
                        "linha": i + 1,
                        "campo": campo,
                        "valor": valor,
                    })
                    print(f"  ✓ {pf.name}:{i+1} — {campo}={valor}")
    except:
        pass

print(f"\nCampos únicos encontrados: {list(questao_6['campos_encontrados'])}\n")

contratos["questoes"]["6_diferenciar_tipos"] = questao_6

# ✅ QUESTÃO 7: O mesmo telefone pode existir em tenants diferentes?
print("\n[Q7] 🔄 O mesmo telefone pode existir em tenants diferentes?\n")

questao_7 = {
    "pergunta": "O mesmo telefone pode existir em tenants diferentes?",
    "evidencias_sim": [],
    "evidencias_nao": [],
    "resposta": None,
}

# Procurar por validação de unicidade
for pf in py_files:
    try:
        with open(pf, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Procurar por "unique", "tenant isolation", "phone unique"
        if re.search(r'unique.*phone|phone.*unique|phone_number.*global|isolacao.*phone', content, re.IGNORECASE):
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if re.search(r'unique|isolacao|tenant', line, re.IGNORECASE):
                    questao_7["evidencias_nao"].append({
                        "arquivo": pf.name,
                        "linha": i + 1,
                        "conteudo": line.strip()[:80],
                    })
                    print(f"  ✓ {pf.name}:{i+1} — isolação/unicidade")
    except:
        pass

if not questao_7["evidencias_nao"]:
    print(f"  ⚠️  Nenhuma evidência de isolação encontrada")
    print(f"  Isto sugere que o MESMO telefone PODE existir em tenants diferentes\n")
    questao_7["resposta"] = "SIM - Permitido (sem validação global)"
else:
    questao_7["resposta"] = "NÃO - Isolado por tenant"

contratos["questoes"]["7_telefone_multiplos_tenants"] = questao_7

# ✅ QUESTÃO 11: Qual é a fonte de verdade da identidade?
print("\n[Q11] 🗿 Qual é a fonte de verdade da identidade?\n")

questao_11 = {
    "pergunta": "Qual é a fonte de verdade da identidade?",
    "fontes_potenciais": {},
    "resposta": None,
}

# Procurar por menções de "source of truth", "canonical", "single source"
for pf in py_files:
    try:
        with open(pf, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        if re.search(r'source.*truth|canonical|single.*source|fonte.*verdade', content, re.IGNORECASE):
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if re.search(r'firestore|database|cache|memory', line, re.IGNORECASE):
                    tipo = re.search(r'(firestore|database|cache|memory)', line, re.IGNORECASE).group(1)
                    if tipo not in questao_11["fontes_potenciais"]:
                        questao_11["fontes_potenciais"][tipo] = []
                    questao_11["fontes_potenciais"][tipo].append({
                        "arquivo": pf.name,
                        "linha": i + 1,
                    })
                    print(f"  ✓ {pf.name}:{i+1} — {tipo}")
    except:
        pass

if not questao_11["fontes_potenciais"]:
    print(f"  ℹ️  Procurando por padrões de persistência...\n")
    print(f"  Firestore é o banco principal → Presumivelmente é a fonte de verdade\n")
    questao_11["resposta"] = "Firestore (presumido)"

contratos["questoes"]["11_fonte_verdade"] = questao_11

# ✅ QUESTÃO 12: Qual documento Firestore representa o vínculo?
print("\n[Q12] 📄 Qual documento Firestore representa o vínculo?\n")

questao_12 = {
    "pergunta": "Qual documento Firestore representa o vínculo?",
    "colecoes_encontradas": set(),
    "caminhos": [],
}

# Procurar por padrões de colection/document
for pf in py_files:
    try:
        with open(pf, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Procurar por db.collection(...).document(...)
        matches = re.findall(r'collection\(["\']([^"\']+)["\']\).*document\(["\']([^"\']+)["\']\)', content)
        for coll, doc in matches:
            path = f"{coll}/{doc}"
            questao_12["caminhos"].append({
                "colecao": coll,
                "documento": doc,
                "caminho": path,
            })
            questao_12["colecoes_encontradas"].add(coll)
            if any(kw in coll.lower() for kw in ["actor", "user", "tenant", "dono"]):
                print(f"  ✓ {coll}/{doc}")
    except:
        pass

print(f"\nColeções de identidade: {list(questao_12['colecoes_encontradas'])}\n")

contratos["questoes"]["12_documento_vinculo"] = questao_12

# ✅ QUESTÃO 14: Como impedir que um ator de Tenant A seja resolvido no Tenant B?
print("\n[Q14] 🔒 Como impedir que um ator de Tenant A seja resolvido no Tenant B?\n")

questao_14 = {
    "pergunta": "Como impedir que um ator de Tenant A seja resolvido no Tenant B?",
    "mecanismos": [],
    "resposta": None,
}

# Procurar por validação de tenant_id, isolacao, etc
for pf in py_files:
    try:
        with open(pf, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        if re.search(r'tenant.*check|tenant.*validat|tenant.*isolat|where.*tenant', content, re.IGNORECASE):
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if re.search(r'tenant_id.*==|where.*tenant|tenant.*check', line, re.IGNORECASE):
                    questao_14["mecanismos"].append({
                        "arquivo": pf.name,
                        "linha": i + 1,
                        "mecanismo": line.strip()[:80],
                    })
                    print(f"  ✓ {pf.name}:{i+1}")
                    print(f"    {line.strip()[:70]}")
    except:
        pass

if questao_14["mecanismos"]:
    questao_14["resposta"] = f"{len(questao_14['mecanismos'])} pontos de validação encontrados"
else:
    questao_14["resposta"] = "⚠️  Nenhuma validação óbvia encontrada"

contratos["questoes"]["14_isolacao_tenant"] = questao_14

# ✅ Salvar relatório
print("\n" + "="*80)
print("RESUMO DO CONTRATO DE IDENTIDADE")
print("="*80 + "\n")

total_questoes = len(contratos["questoes"])
questoes_respondidas = sum(1 for q in contratos["questoes"].values() if q.get("resposta") or q.get("evidencias"))

print(f"Questões analisadas: {total_questoes}")
print(f"Questões com evidências: {questoes_respondidas}")
print(f"Cobertura: {questoes_respondidas}/{total_questoes} ({100*questoes_respondidas//total_questoes}%)\n")

# Salvar
report_file = f"contrato_identidade_c316_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(report_file, 'w', encoding='utf-8') as f:
    # Converter sets para lists para JSON
    contratos_serializable = json.loads(json.dumps(contratos, default=str))
    json.dump(contratos_serializable, f, indent=2, ensure_ascii=False)

print(f"Relatório: {report_file}\n")

print("="*80 + "\n")
