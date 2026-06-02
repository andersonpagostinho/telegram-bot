# CLAUDE.md — Regras Obrigatórias para NeoEve

## 🔒 Arquivos

- **NUNCA** criar um arquivo sem antes verificar se já existe algo equivalente no projeto.
- Antes de criar qualquer arquivo novo, **listar os arquivos candidatos já existentes**.
- **Preferir editar arquivos existentes** ao invés de criar novos.
- Sempre informar em qual arquivo pretende atuar antes de gerar alterações.

## 📦 Dependências

- **NUNCA** instalar dependências sem verificar:
  - `requirements.txt`
  - `pyproject.toml`
  - ambiente virtual existente
  - imports já utilizados no projeto
  
- Antes de sugerir instalação, informar:
  - dependência encontrada?
  - versão encontrada?
  - onde foi encontrada?

## 🌍 Ambiente

- **NUNCA** editar arquivos `.env`.
- **NUNCA** criar variáveis de ambiente automaticamente.
- Apenas informar ao usuário quais variáveis precisam ser adicionadas.

## 💾 Alterações de Código

- **NUNCA** aplicar patches diretamente.
- Sempre gerar alteração em formato `.diff` (ou mostrar contexto suficiente).
- Explicar o impacto da alteração antes de aplicá-la.

## ⚠️ Segurança de Alteração

Antes de qualquer ação destrutiva (delete, overwrite, rename, move):
- **Solicitar confirmação explícita**.
- **Nunca remover código** sem mostrar exatamente o que será removido.

## 🏗️ Arquitetura

- **NUNCA** criar fluxo novo sem verificar se já existe fluxo equivalente.
- Antes de implementar qualquer funcionalidade:
  1. localizar fluxo existente
  2. identificar ponto de entrada
  3. identificar funções já utilizadas
  4. reutilizar componentes existentes
  
- **Priorizar correção do fluxo existente** ao invés de criar fluxo paralelo.

- **NUNCA duplicar:**
  - regras de negócio
  - validações
  - templates
  - verificações de conflito
  - verificações de disponibilidade
  
- Se existir função equivalente, **reutilizar**.

## 🐛 Debug

Antes de propor correção:
- localizar origem do erro
- identificar causa raiz
- mostrar arquivo e linha
- **Não corrigir sintomas** sem validar a causa raiz

Para bugs:
- mostrar evidência
- mostrar stack trace relevante
- mostrar local exato da falha

## 📅 NeoEve / Sistema de Agenda

### ⛔ GPT NUNCA deve decidir:
- disponibilidade
- conflito
- duração
- criação de evento

### ✅ GPT deve atuar apenas em:
- interpretação de linguagem
- extração de intenção
- humanização de mensagens

### 🔑 Toda lógica crítica deve permanecer **determinística**.

### ❌ Regra de Ouro da Agenda

- **Nunca criar um segundo fluxo de agendamento.**
- **Nunca criar um segundo mecanismo de confirmação.**
- **Nunca criar uma segunda fonte de verdade** para:
  - eventos
  - profissionais
  - serviços
  - disponibilidade

Antes de alterar o sistema de agenda, **mapear o fluxo atual completo**.

## 📋 Processo Obrigatório

Antes de qualquer implementação responder:

1. ✅ **Arquivos encontrados** — listar candidatos existentes
2. ✅ **Fluxo atual identificado** — mapear entrada → processamento → saída
3. ✅ **Funções existentes reutilizáveis** — listar funções já disponíveis
4. ✅ **Menor alteração possível** — descrever mudança mínima
5. ✅ **Riscos identificados** — sinalizar impactos potenciais
6. ✅ **Diff proposto** — mostrar código antes/depois

**Somente depois gerar a alteração.**

---

**Última atualização:** 2026-06-02
