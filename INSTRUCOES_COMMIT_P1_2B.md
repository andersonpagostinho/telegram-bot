# INSTRUÇÕES PARA COMMIT P1.2B

**Data:** 2026-06-14  
**Status:** ✅ CODE REVIEW APROVADO  
**Próximo Passo:** Commit e Merge  

---

## 📋 FILES PARA STAGE

### Código de Produção (2 arquivos)
```
MODIFICADO:
  router/principal_router_precheck_func.py
    └─ Adicionado P1.2B (linhas 196-220)
    └─ Integração após P1.2A, antes de salvar contexto
    └─ Importa e chama extrair_contexto_motor()

NOVO:
  services/clienteprofile_contexto_service.py
    └─ Serviço de extração de contexto neutro
    └─ Função: extrair_contexto_motor()
    └─ 117 linhas, sem dependências externas
```

### Testes (1 arquivo)
```
NOVO:
  tests/test_p1_2b_contexto_motor.py
    └─ 8 testes unitários obrigatórios
    └─ Testes: sucesso, vazio, campos, proibidos, draft, msg, flags, erro
    └─ Resultado: 8/8 passando
```

### Especificações (3 arquivos — já foram atualizadas em sessão anterior)
```
NOVO/MODIFICADO (sessão anterior):
  docs/specs/SPEC_P1_2B_MOTOR_CONSULTA_CLIENTEPROFILE.md
    └─ Especificação de P1.2B
    └─ Removido vocabulário de sugestão/ação
    └─ Apenas contexto neutro

MODIFICADO (sessão anterior):
  AUDITORIA_P1_2B_VALOR_DE_NEGOCIO.md
    └─ Atualizado: P1.2B vs P1.3 separados
    └─ Campos neutros em P1.2B, sugestão em P1.3+
```

### Documentação de Validação (3 arquivos)
```
NOVO:
  CODE_REVIEW_P1_2B_FINAL.md
    └─ Revisão completa de segurança
    └─ Validação de campos proibidos
    └─ Confirmação de conformidade

  RESULTADO_P1_2B_IMPLEMENTACAO.md
    └─ Resultado detalhado da implementação
    └─ Estrutura de dados criada
    └─ Validação de testes

  VALIDACAO_P1_2B_SPECS.md
    └─ Conformidade com 3 specs obrigatórias
    └─ Checklist de governa nça
    └─ Validação de segurança
```

---

## 🔄 PASSO A PASSO PARA COMMIT

### 1. Adicionar Arquivos ao Stage

```bash
# Código de produção
git add router/principal_router_precheck_func.py
git add services/clienteprofile_contexto_service.py

# Testes
git add tests/test_p1_2b_contexto_motor.py

# Especificações (considere se já foram adicionadas)
git add docs/specs/SPEC_P1_2B_MOTOR_CONSULTA_CLIENTEPROFILE.md
git add AUDITORIA_P1_2B_VALOR_DE_NEGOCIO.md

# Validação (documentação de revisão)
git add CODE_REVIEW_P1_2B_FINAL.md
git add RESULTADO_P1_2B_IMPLEMENTACAO.md
git add VALIDACAO_P1_2B_SPECS.md
```

### 2. Verificar o que foi staged

```bash
git status
# Deve mostrar os arquivos acima como "Changes to be committed"
```

### 3. Criar o Commit

```bash
git commit -m "feat: criar contexto neutro do ClienteProfile para motor

- extrai métricas neutras do ClienteProfile em P1.2B
- cria clienteprofile_contexto_motor sem alterar fluxo
- preserva GPT, draft, confirmação e resposta
- bloqueia vocabulário de sugestão/ação em P1.2B
- adiciona 8 testes de contexto neutro e regressão

Benefícios:
- Motor determinístico pode ler contexto de cliente em P1.3+
- Contexto usado apenas para ENTENDER, não para DECIDIR
- Segurança mantida: \"influencia não decide\"
- Fluxo idêntico: zero impacto em resposta/confirmação

Validação:
- 8/8 testes passando
- Zero campos de sugestão/ação criados
- Compilação OK
- Code review aprovado
- Regressão OK: draft/msg/evento preservados

Refs:
- SPEC_P1_2B_MOTOR_CONSULTA_CLIENTEPROFILE.md
- SPEC_SEGURANCA_CLIENTEPROFILE_NAO_DECIDE.md
- POLITICA_CODE_REVIEW_CLIENTEPROFILE.md"
```

### 4. Verificar o Commit

```bash
git log --oneline -1
# Deve mostrar o commit com mensagem P1.2B
```

---

## ✅ VALIDAÇÃO PRÉ-MERGE

Antes de mergear, rodar estas validações:

### Compilação Rápida
```bash
python -m py_compile \
  services/clienteprofile_contexto_service.py \
  router/principal_router_precheck_func.py \
  tests/test_p1_2b_contexto_motor.py
```

### Testes Unitários
```bash
python tests/test_p1_2b_contexto_motor.py
# Esperado: [PASS] TODOS OS TESTES DE P1.2B PASSARAM
```

### Verificação de Campos Proibidos
```bash
grep -rn "profissional_sugestao.*=" \
  services/clienteprofile_contexto_service.py \
  router/principal_router_precheck_func.py
# Esperado: 0 ocorrências
```

---

## 🚀 PÓS-MERGE

### 1. Atualizar Branch Local
```bash
git pull origin main
```

### 2. Verificar Merge foi OK
```bash
git log --oneline -3
# Deve mostrar: feat: criar contexto neutro...
```

### 3. NÃO Iniciar P1.3
```
⚠️ IMPORTANTE: Não inicie P1.3 imediatamente
→ Próxima frente: Auditoria do módulo de cancelamento P0
→ P1.3 fica em backlog até que P0 esteja auditado
```

---

## 📊 RESUMO PRÉ-MERGE

| Item | Status |
|------|--------|
| Compilação | ✅ OK |
| Testes (8/8) | ✅ PASSING |
| Code Review | ✅ APROVADO |
| Campos Proibidos | ✅ ZERO CRIAÇÕES |
| Segurança | ✅ MANTIDA |
| Conformidade Specs | ✅ 100% |
| Pronto para Merge | ✅ SIM |

---

## 🔒 CHECKLIST FINAL

Antes de clicar "Merge Pull Request":

```
[ ] Code review finalizado e aprovado
[ ] Testes unitários passando (8/8)
[ ] Compilação OK
[ ] Campos proibidos: zero criações confirmadas
[ ] Draft não alterado (TEST 5)
[ ] Msg não alterada (TEST 6)
[ ] Evento não criado
[ ] GPT não recebe contexto_motor
[ ] Especificações linkadas no commit
[ ] Documentação de validação incluída
[ ] Mensagem de commit descritiva
[ ] Branch atualizado com main
```

---

**Data:** 2026-06-14  
**Responsável:** Code Review ✅  
**Próxima:** Merge + Auditoria P0 Cancelamento
