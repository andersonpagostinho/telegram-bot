# 📋 PROPOSTA DE ORGANIZAÇÃO: Arquivos Permanentes vs Temporários

**Data:** 2026-06-02  
**Objetivo:** Separar docs permanentes de testes/debug temporários  

---

## 📊 TABELA DE CLASSIFICAÇÃO

### A) AUDITORIAS — DOCUMENTAÇÃO PERMANENTE ✅

| Arquivo | Tipo | Severidade | Motivo Permanente | Destino |
|---------|------|-----------|-------------------|---------|
| INCIDENTE_ENCERRADO.md | Incidente P0 | P0 | Registro histórico de bug crítico resolvido | `docs/auditorias/` |
| AUDITORIA_BUG_DATA_HORA_REAL.md | Causa raiz P0 | P0 | Evidência de bug real: data_hora sobrescrita. Aprendizado: mensagem_atual > contexto | `docs/auditorias/` |
| AUDITORIA_CLIENTE_NOME_FLUXO.md | Causa raiz P0 | P0 | Rastreamento completo do caso "Suri". Identificou fallback agressivo em linha 509 | `docs/auditorias/` |
| AUDITORIA_PROFISSIONAIS_DESAPARECIDOS.md | Causa raiz P0 | P0 | Identificou contexto={} vazio em linha 77 de gpt_service.py | `docs/auditorias/` |
| AUDITORIA_ERRO_429_DETALHADO.md | Diagnóstico técnico | - | Mapeamento de códigos HTTP 429 da OpenAI. Referência útil para suporte | `docs/auditorias/` |
| AUDITORIA_CONFIGURACAO_OPENAI.md | Diagnóstico técnico | - | Mapeamento de variáveis de ambiente e configuração OpenAI. Referência para deployment | `docs/auditorias/` |
| AUDITORIA_FLUXO_DETERMINISICO_DISPONIBILIDADE.md | Arquitetura | - | Decisão: disponibilidade NÃO passa por GPT. Motor determinístico. Aprendizado permanente | `docs/auditorias/` |
| AUDITORIA_MOTOR_DISPONIBILIDADE_FINAL.md | Arquitetura | - | Guia final: como usar motor determinístico SEM hardcode. Aprendizado técnico | `docs/auditorias/` |

**Subtotal: 8 arquivos permanentes**

---

### B) AUDITORIAS — EXPLORATÓRIAS (podem ser permanentes ou movidas) ⚠️

| Arquivo | Tipo | Motivo | Decisão | Destino |
|---------|------|--------|---------|---------|
| AUDITORIA_MERGE_CONTEXTO.md | Análise intermediária | Exploração de hipótese (não confirmada como raiz). Valor: histórico de investigação | MOVER (não foi raiz) | `docs/auditorias/historico/` |
| AUDITORIA_429_GPT.md | Análise intermediária | Primeira análise de 429. Confirmou existência de 2 chamadas mas não provou duplicação | MOVER | `docs/auditorias/historico/` |
| AUDITORIA_ESTRUTURAL_1027_vs_2476.md | Análise intermediária | Análise das 2 chamadas GPT. Útil mas sem conclusão definitiva | MOVER | `docs/auditorias/historico/` |
| AUDITORIA_FLUXO_CHAMADAS_GPT.md | Análise intermediária | Rastreamento de fluxo durante investigação de 429 | MOVER | `docs/auditorias/historico/` |
| AUDITORIA_TAMANHO_REQUISICOES.md | Análise técnica | Medição de tamanho de prompts. Útil para debugging mas não é causa raiz | MOVER | `docs/auditorias/historico/` |

**Subtotal: 5 arquivos exploratórios → move para historico/**

---

### C) TESTES TEMPORÁRIOS — DEBUG ❌

| Arquivo | Tipo | Motivo Temporário | Destino |
|---------|------|-------------------|---------|
| teste_firebase.py | Teste básico | Teste de desenvolvimento firebase | `tests/debug/` |
| teste_contexto_merge.py | Teste de patch | Validação da correção de merge | `tests/debug/` |
| teste_patches.py | Teste de patch | Validação geral de patches | `tests/debug/` |
| teste_router_real.py | Teste de router | Teste de comportamento real do router | `tests/debug/` |
| teste_patch_auto_prof.py | Teste de patch | Teste de patch automático de profissional | `tests/debug/` |
| teste_patch_consulta_pura.py | Teste de patch | Teste de consulta sem GPT | `tests/debug/` |
| teste_encontrar_debug.py | Debug | Script de debug isolado | `tests/debug/` |
| teste_encontrar_servico.py | Teste de função | Teste isolado de encontrar_servico_mais_proximo() | `tests/debug/` |
| teste_patch_disponibilidade.py | Teste de patch | Validação do patch de disponibilidade (mais recente) | `tests/debug/` |

**Subtotal: 9 arquivos de teste/debug**

---

## 📁 ESTRUTURA PROPOSTA

```
NeoEve - Empresarial/
├── docs/
│   └── auditorias/
│       ├── INCIDENTE_ENCERRADO.md              (P0 resolvido)
│       ├── AUDITORIA_BUG_DATA_HORA_REAL.md     (P0 causa raiz)
│       ├── AUDITORIA_CLIENTE_NOME_FLUXO.md     (P0 causa raiz)
│       ├── AUDITORIA_PROFISSIONAIS_DESAPARECIDOS.md (P0 causa raiz)
│       ├── AUDITORIA_ERRO_429_DETALHADO.md     (diagnóstico técnico)
│       ├── AUDITORIA_CONFIGURACAO_OPENAI.md    (diagnóstico técnico)
│       ├── AUDITORIA_FLUXO_DETERMINISICO_DISPONIBILIDADE.md (arquitetura)
│       ├── AUDITORIA_MOTOR_DISPONIBILIDADE_FINAL.md (arquitetura)
│       │
│       └── historico/
│           ├── AUDITORIA_MERGE_CONTEXTO.md     (exploratória)
│           ├── AUDITORIA_429_GPT.md            (exploratória)
│           ├── AUDITORIA_ESTRUTURAL_1027_vs_2476.md (exploratória)
│           ├── AUDITORIA_FLUXO_CHAMADAS_GPT.md (exploratória)
│           └── AUDITORIA_TAMANHO_REQUISICOES.md (exploratória)
│
├── tests/
│   └── debug/
│       ├── teste_firebase.py
│       ├── teste_contexto_merge.py
│       ├── teste_patches.py
│       ├── teste_router_real.py
│       ├── teste_patch_auto_prof.py
│       ├── teste_patch_consulta_pura.py
│       ├── teste_encontrar_debug.py
│       ├── teste_encontrar_servico.py
│       └── teste_patch_disponibilidade.py
│
├── CLAUDE.md (será atualizado com aprendizados)
└── [outros arquivos...]
```

---

## 🎓 APRENDIZADOS PERMANENTES

Estes devem ser adicionados ao CLAUDE.md (Seção: Aprendizados Obrigatórios):

### 1. Data/Hora — Regra P0
**De:** INCIDENTE_ENCERRADO.md + AUDITORIA_BUG_DATA_HORA_REAL.md

**Aprendizado:**
```
Prioridade de dados: mensagem_atual > draft_agendamento > ultima_consulta > contexto_antigo

Especificamente para data_hora:
- Se usuário disse hora explícita ("amanhã às 16"), usar SEMPRE a hora nova
- Nunca preservar hora antiga do contexto quando há nova extração
- Patch P0: Passar data_hora explícita como argumento de função, não via contexto
```

### 2. Disponibilidade — Regra Arquitetural
**De:** AUDITORIA_FLUXO_DETERMINISICO_DISPONIBILIDADE.md + AUDITORIA_MOTOR_DISPONIBILIDADE_FINAL.md

**Aprendizado:**
```
Regra Arquitetural: Consulta de disponibilidade é determinística, NUNCA passa por GPT

Padrão:
- Detectar: "quem tem disponível [data] [período]?"
- NÃO chamar GPT com "Profissionais: nenhum"
- SEMPRE usar motor determinístico:
  1. Extrair serviço (normalizacao_service)
  2. Buscar profissionais do serviço (profissional_service)
  3. Verificar disponibilidade por horário (motor)
  4. Retornar resultado determinístico

Benefício: Resposta correta mesmo quando lista de profissionais está vazia
```

### 3. Semântica vs Código — Metodologia de Debug
**De:** AUDITORIA_CLIENTE_NOME_FLUXO.md

**Aprendizado:**
```
Quando encontrar valor errado ("Suri" salvo como profissional):

ANTES de alterar código, perguntar:
1. O sistema entendeu errado (semântica/GPT)?
   → Verificar prompt e JSON retornado pelo GPT
   
2. Ou salvou errado (código)?
   → Verificar Firestore e persistência

Ordem de correção:
1. Se entendimento errado → ajustar prompt/manual (camada 1)
2. Se salvamento errado → ajustar persistência (camada 4)
3. NÃO corrigir código quando problema é semântica

Exemplo: "Suri"
- GPT extraiu como profissional (problema semântica)
- Solução: ajustar manual_secretaria.py, não código de persistência
```

### 4. Tenant — Isolamento Multi-tenant
**De:** AUDITORIA_PROFISSIONAIS_DESAPARECIDOS.md + AUDITORIA_CONFIGURACAO_OPENAI.md

**Aprendizado:**
```
SEMPRE usar obter_id_dono(user_id) para resolver tenant correto

Padrão ERRADO:
await buscar_subcolecao(f"Clientes/{user_id}/Profissionais")

Padrão CORRETO:
dono_id = await obter_id_dono(user_id)
await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais")

Por quê:
- user_id pode ser cliente, não dono
- obter_id_dono() resolve a hierarquia corretamente
- Evita misturar dados de tenants
```

### 5. Fallback Determinístico para Serviços
**De:** AUDITORIA_MOTOR_DISPONIBILIDADE_FINAL.md

**Aprendizado:**
```
Para encontrar serviços quando Firestore está vazio:

Implementar fallback em 3 níveis:
1. Buscar do Firestore (serviços reais do tenant)
2. Se vazio → usar lista padrão (corte, escova, manicure, etc)
3. Se ainda não encontrar → perguntar ao usuário

Código:
try:
    servicos_reais = buscar_do_firestore()
except:
    pass

if not servicos_reais:
    servicos_reais = {"corte", "escova", "manicure", ...}

Nunca deixar vazio sem fallback.
```

---

## ✅ RESUMO

| Ação | Quantidade | Destino |
|------|-----------|---------|
| Documentação permanente | 8 arquivos | `docs/auditorias/` |
| Exploratório (histórico) | 5 arquivos | `docs/auditorias/historico/` |
| Testes/debug | 9 arquivos | `tests/debug/` |
| Total movido | **22 arquivos** | - |
| Aprendizados para CLAUDE.md | 5 seções | CLAUDE.md |

---

## ⚠️ PRÓXIMO PASSO

Antes de mover:

1. ✅ Verificar se há segredos (api keys, tokens)
2. ✅ Mascarar segredos se encontrados
3. ✅ Criar estrutura de diretórios
4. ✅ Mover arquivos
5. ✅ Atualizar CLAUDE.md
6. ✅ Mostrar `git diff --stat`
7. ❌ NÃO fazer commit ainda

**Autorização: Aguardando sua aprovação para proceder.**
