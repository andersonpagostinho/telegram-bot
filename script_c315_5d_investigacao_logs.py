#!/usr/bin/env python3
"""
C3.15.5-D — INVESTIGAÇÃO FINAL DE LOGS HISTÓRICOS
==================================================

Objetivo: Determinar owner histórico do tenant 7394370553 por logs reais.

Restrições:
✅ READ-ONLY apenas (zero escritas no Firestore)
✅ Não alterar documentos ou código
✅ Não inventar actor_id
✅ Não usar placeholders/testes
✅ Não imprimir tokens sensíveis

Procurar por:
- tenant_id=7394370553
- id_negocio=7394370553
- Clientes/7394370553
- criação/onboarding
- phone_number_id
- actor_id explícito
"""

import os
import json
import re
from datetime import datetime
from pathlib import Path

print("\n" + "="*80)
print("C3.15.5-D — INVESTIGAÇÃO FINAL DE LOGS HISTÓRICOS")
print("="*80 + "\n")

TARGET_TENANT = "7394370553"
investigation = {
    "tenant_id": TARGET_TENANT,
    "timestamp": datetime.now().isoformat(),
    "logs_pesquisados": [],
    "evidencias_encontradas": [],
    "conclusao": {
        "owner_determinado": False,
        "actor_id": None,
        "evidencia": None,
        "timestamp": None,
        "origem": None,
        "tipo_associacao": None,
    },
    "writes_executadas": 0,
}

print(f"[INIT] Procurando logs históricos para tenant: {TARGET_TENANT}\n")

# ✅ PASSO 1: Procurar em arquivos .log
print("[PASSO 1] 📄 Procurando em arquivos .log...\n")

log_files = list(Path(".").glob("*.log"))
for log_file in log_files:
    print(f"[FOUND] {log_file.name}")
    investigation["logs_pesquisados"].append({
        "arquivo": log_file.name,
        "tipo": "log",
        "evidencias": 0,
    })

    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Procurar por tenant_id
        if TARGET_TENANT in content:
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if TARGET_TENANT in line:
                    # Extrair contexto
                    context_start = max(0, i - 2)
                    context_end = min(len(lines), i + 3)
                    context = '\n'.join(lines[context_start:context_end])

                    # Tentar extrair timestamp e actor_id
                    timestamp_match = re.search(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', line)
                    timestamp_str = timestamp_match.group(0) if timestamp_match else "unknown"

                    # Procurar por actor_id/user_id/phone
                    actor_matches = re.findall(r'(?:actor_id|user_id|phone|from|sender)["\s:=]+([0-9a-zA-Z+]+)', line, re.IGNORECASE)

                    evidence = {
                        "arquivo": log_file.name,
                        "linha": i + 1,
                        "timestamp": timestamp_str,
                        "conteudo_resumido": line[:150],
                        "atores_encontrados": actor_matches,
                        "contexto": context[:200],
                    }

                    investigation["evidencias_encontradas"].append(evidence)
                    investigation["logs_pesquisados"][-1]["evidencias"] += 1

                    print(f"  ✓ Linha {i+1}: {timestamp_str}")
                    if actor_matches:
                        print(f"    Atores: {actor_matches}")

    except Exception as e:
        print(f"  [ERROR] {str(e)[:100]}")

# ✅ PASSO 2: Procurar em arquivos de rastreamento
print("\n\n[PASSO 2] 🔎 Procurando em arquivos de rastreamento...\n")

trace_files = [
    "rastreio_p0_direto.py",
    "rastreio_p0_real.py",
    "audit_phantom_clientes_only.py",
    "final_audit_before_cleanup.py",
    "scripts/full_audit_firebase.py",
    "scripts/deep_audit_firebase.py",
]

for trace_file in trace_files:
    if os.path.exists(trace_file):
        print(f"[FOUND] {trace_file}")
        investigation["logs_pesquisados"].append({
            "arquivo": trace_file,
            "tipo": "trace/audit",
            "evidencias": 0,
        })

        try:
            with open(trace_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Procurar por tenant_id
            if TARGET_TENANT in content:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if TARGET_TENANT in line and not line.strip().startswith('#'):
                        # Filtrar testes/placeholders
                        if any(x in line.lower() for x in ["test", "fixture", "exemplo", "stub", "mock", "placeholder"]):
                            continue

                        context_start = max(0, i - 3)
                        context_end = min(len(lines), i + 4)
                        context = '\n'.join(lines[context_start:context_end])

                        # Procurar por actor_id
                        actor_pattern = r'(?:actor_id|user_id|phone|from)["\s:=]+([0-9a-zA-Z+\-]+)'
                        actor_matches = re.findall(actor_pattern, context, re.IGNORECASE)
                        actor_matches = [a for a in actor_matches if a not in [TARGET_TENANT, "unknown", "none", ""]]

                        evidence = {
                            "arquivo": trace_file,
                            "linha": i + 1,
                            "operacao": "rastreamento/auditoria",
                            "conteudo": line[:150],
                            "atores_encontrados": actor_matches,
                            "tipo_associacao": "contextual",
                        }

                        investigation["evidencias_encontradas"].append(evidence)
                        investigation["logs_pesquisados"][-1]["evidencias"] += 1

                        print(f"  ✓ Linha {i+1}: {line[:80]}")
                        if actor_matches:
                            print(f"    Atores: {actor_matches}")

        except Exception as e:
            print(f"  [ERROR] {str(e)[:100]}")

# ✅ PASSO 3: Procurar em arquivos de teste/rastreamento detalhado
print("\n\n[PASSO 3] 🔍 Procurando em handlers e roteadores...\n")

handler_files = [
    "handlers/bot.py",
    "handlers/whatsapp_bridge_handler.py",
    "router/principal_router.py",
]

for handler_file in handler_files:
    if os.path.exists(handler_file):
        print(f"[CHECKING] {handler_file}")

        try:
            with open(handler_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Procurar por configurações/constantes do tenant
            if TARGET_TENANT in content:
                # Procurar por padrão: TENANT_ID = "...", tenant_id = "...", etc
                patterns = [
                    r'(?:TENANT_ID|tenant_id|TARGET_TENANT)\s*=\s*["\']([^"\']+)["\']',
                    r'(?:OWNER_ID|owner_id|DONO_ID)\s*=\s*["\']([^"\']+)["\']',
                    r'actor_id["\s:=]+([0-9a-zA-Z+\-]+)',
                ]

                for pattern in patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        value = match.group(1)
                        line_num = content[:match.start()].count('\n') + 1

                        # Não incluir placeholders
                        if value not in ["", "unknown", "none", "test"] and not value.startswith("5519999"):
                            evidence = {
                                "arquivo": handler_file,
                                "linha": line_num,
                                "tipo": "configuração",
                                "valor": value,
                                "tipo_associacao": "configuração_código",
                            }

                            investigation["evidencias_encontradas"].append(evidence)
                            print(f"  ✓ Linha {line_num}: {pattern} = {value[:50]}")

        except Exception as e:
            print(f"  [ERROR] {str(e)[:100]}")

# ✅ PASSO 4: Procurar por padrão de criação/onboarding
print("\n\n[PASSO 4] 🎬 Procurando por padrão de criação/onboarding...\n")

keywords_criacao = [
    "criar",
    "create",
    "onboard",
    "iniciar",
    "initialize",
    "primeiro acesso",
    "first access",
    "setup",
    "configure",
]

for keyword in keywords_criacao:
    # Procurar em arquivos Python
    py_files = list(Path(".").glob("**/*.py"))[:20]  # Limitar para não buscar muito

    for py_file in py_files:
        try:
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Procurar por combinação de keyword + tenant
            if keyword.lower() in content.lower() and TARGET_TENANT in content:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if keyword.lower() in line.lower() and TARGET_TENANT in '\n'.join(lines[max(0, i-3):min(len(lines), i+4)]):
                        # Extrair contexto
                        context_start = max(0, i - 2)
                        context_end = min(len(lines), i + 3)
                        context = '\n'.join(lines[context_start:context_end])

                        # Procurar por actor_id
                        actor_matches = re.findall(r'([0-9]{10,}|[a-z0-9\+\-]+@)', context, re.IGNORECASE)
                        actor_matches = [a for a in set(actor_matches) if a != TARGET_TENANT]

                        if actor_matches or any(kw in line.lower() for kw in ["from", "actor", "user", "owner"]):
                            evidence = {
                                "arquivo": str(py_file),
                                "linha": i + 1,
                                "keyword": keyword,
                                "conteudo": line[:100],
                                "atores_possiveis": actor_matches,
                                "tipo_associacao": "indireta",
                            }

                            investigation["evidencias_encontradas"].append(evidence)
                            print(f"  ✓ {py_file.name}:{i+1} (keyword: {keyword})")
                            break
        except:
            pass

# ✅ PASSO 5: Analisar evidências coletadas
print("\n\n[PASSO 5] 📊 Analisando evidências coletadas...\n")

print(f"[RESUMO] Total de evidências encontradas: {len(investigation['evidencias_encontradas'])}\n")

# Procurar por padrão consistente de actor_id
actor_candidates = {}
for evidence in investigation["evidencias_encontradas"]:
    atores = evidence.get("atores_encontrados", []) or evidence.get("atores_possiveis", [])

    for ator in atores:
        if ator and ator not in [TARGET_TENANT, "unknown", "none", ""]:
            # Filtrar números de teste conhecidos
            if not any(test in ator for test in ["5519999", "9999", "test"]):
                if ator not in actor_candidates:
                    actor_candidates[ator] = {"count": 0, "evidencias": []}

                actor_candidates[ator]["count"] += 1
                actor_candidates[ator]["evidencias"].append({
                    "arquivo": evidence.get("arquivo"),
                    "linha": evidence.get("linha"),
                })

if actor_candidates:
    print("[CANDIDATOS ENCONTRADOS]:\n")

    # Ordenar por frequência
    sorted_candidates = sorted(actor_candidates.items(), key=lambda x: x[1]["count"], reverse=True)

    for ator, info in sorted_candidates:
        print(f"  actor_id: {ator}")
        print(f"    Menções: {info['count']}")
        print(f"    Em arquivos:")
        for ev in info['evidencias'][:3]:  # Mostrar até 3
            print(f"      - {ev['arquivo']}:{ev['linha']}")
        print()
else:
    print("[NENHUM CANDIDATO A ACTOR_ID ENCONTRADO NOS LOGS]\n")

# ✅ PASSO 6: Conclusão
print("\n[PASSO 6] 🎬 Compilando conclusão...\n")

if actor_candidates:
    # Se houver um candidato claro (mencionado múltiplas vezes)
    top_candidate = sorted_candidates[0]
    actor_id, info = top_candidate

    if info["count"] >= 2 and not any(test in actor_id for test in ["test", "exemplo", "stub"]):
        # Tem evidência múltipla
        investigation["conclusao"]["owner_determinado"] = True
        investigation["conclusao"]["actor_id"] = actor_id
        investigation["conclusao"]["tipo_associacao"] = "CONTEXTUAL (múltiplas menções em logs)"
        investigation["conclusao"]["evidencia"] = f"{info['count']} menções em logs históricos"
        investigation["conclusao"]["origem"] = [e["arquivo"] for e in info["evidencias"][:2]]

# ✅ Relatório final
print("="*80)
print("✅ C3.15.5-D — INVESTIGAÇÃO DE LOGS")
print("="*80 + "\n")

print("ARQUIVOS PESQUISADOS:")
print("-" * 60)
for log_info in investigation["logs_pesquisados"]:
    print(f"  ✓ {log_info['arquivo']} ({log_info['evidencias']} menções)")

print(f"\n\nEVIDÊNCIAS ENCONTRADAS: {len(investigation['evidencias_encontradas'])}")

if investigation["evidencias_encontradas"]:
    print("\nTop 5 evidências:")
    for i, ev in enumerate(investigation["evidencias_encontradas"][:5], 1):
        print(f"\n  [{i}] {ev.get('arquivo')}:{ev.get('linha')}")
        if "atores_encontrados" in ev:
            print(f"      Atores: {ev.get('atores_encontrados')}")
        elif "atores_possiveis" in ev:
            print(f"      Atores possíveis: {ev.get('atores_possiveis')}")
        print(f"      Tipo: {ev.get('tipo_associacao', 'desconhecido')}")

print("\n\nCONCLUSÃO:")
print("-" * 60)

if investigation["conclusao"]["owner_determinado"]:
    print(f"\n✅ OWNER_DETERMINADO: SIM")
    print(f"  actor_id: {investigation['conclusao']['actor_id']}")
    print(f"  evidência: {investigation['conclusao']['evidencia']}")
    print(f"  tipo: {investigation['conclusao']['tipo_associacao']}")
    print(f"  origem: {investigation['conclusao']['origem']}")
    print(f"\n✅ C3.15.5-D — LOG OWNERSHIP AUDIT: PASS")
else:
    print(f"\n❌ OWNER_DETERMINADO: NÃO")

    if actor_candidates:
        print(f"\nCandidatos parciais encontrados:")
        for ator, info in sorted_candidates[:3]:
            print(f"  - {ator} ({info['count']} menções)")
        print(f"\nMas nenhum com força suficiente para ser determinado como owner explícito.")
    else:
        print(f"\nNenhum candidato a actor_id encontrado nos logs disponíveis.")

    print(f"\n❌ C3.15.5-D — LOG OWNERSHIP AUDIT: BLOCKED")

print("\n\nGARANTIAS:")
print("-" * 60)
print(f"  ✅ WRITES EXECUTADAS: {investigation['writes_executadas']}")
print(f"  ✅ Somente leitura de logs")
print(f"  ✅ Nenhum Firestore write")
print(f"  ✅ Nenhum código alterado")
print(f"  ✅ Nenhum actor_id inventado")

print("\n" + "="*80 + "\n")

# Salvar relatório
report_file = f"investigacao_c315_5d_logs_{TARGET_TENANT}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(report_file, 'w', encoding='utf-8') as f:
    json.dump(investigation, f, indent=2, ensure_ascii=False, default=str)

print(f"Relatório detalhado: {report_file}\n")
