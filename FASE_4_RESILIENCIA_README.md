# 🚀 FASE 4 — RESILIÊNCIA OPERACIONAL REAL

**Status:** Iniciando (2026-06-19)

---

## 📋 Arquivos Criados

1. **`tests/runner_p0_resiliencia_operacional_real.py`**
   - Suite completa com 12 testes (RO-01 a RO-12)
   - Fixtures Firestore para testes reais
   - Simuladores de falha (GPT timeout, mensagem, etc)

2. **`tests/resultado_p0_resiliencia_operacional_real.json`**
   - Template de resultados
   - Rastreia 3 execuções consecutivas
   - Registra bugs e achados

3. **`docs/auditorias/MATRIZ_P0_RESILIENCIA_OPERACIONAL_REAL.md`**
   - Documentação completa de cada teste
   - Critérios aprovação
   - Infraestrutura e dados de teste

---

## ✅ Testes Implementados

| ID | Nome | Tipo | P0/P1 |
|----|------|------|-------|
| RO-01 | Restart com confirmação pendente | Restart | P0 |
| RO-02 | Restart após sugestão de horário | Restart | P0 |
| RO-03 | Restart após salvar contexto | Restart | P0 |
| RO-04 | Restart durante criação de evento | Restart | P0 |
| RO-05 | Lock órfão expira ou é recuperável | Lock | P0 |
| RO-06 | Webhook retry após evento criado | Idempotência | P0 |
| RO-07 | Timeout/erro de envio após criar | Idempotência | P0 |
| RO-08 | Scheduler reiniciado não duplica | Scheduler | P1 |
| RO-09 | Notificação atrasada expira | Notificação | P1 |
| RO-10 | Firestore indisponível temporariamente | Falha externa | P0 |
| RO-11 | GPT timeout durante interpretação | Falha externa | P0 |
| RO-12 | Telegram/WhatsApp update duplicado | Idempotência | P0 |

---

## 🎯 Critério Aprovação

**Obrigatório:**
- ✅ 12/12 testes passando
- ✅ 3 execuções consecutivas
- ✅ Firestore real (não mock)
- ✅ Sem locks órfãos
- ✅ Sem duplicação de eventos

**Se falhar:** Documentar bug, criar patch mínimo, reexecutar.

---

## 🧪 Como Executar

### Pré-requisitos

```bash
# Verificar estrutura
ls -la tests/runner_p0_resiliencia_operacional_real.py
ls -la docs/auditorias/MATRIZ_P0_RESILIENCIA_OPERACIONAL_REAL.md
```

### Execução 1 (Baseline)

```bash
cd "C:\Users\ANDERSON\iCloudDrive\Projeto Mercado Digital\Agente Bot\NeoEve - Empresarial"

# Executar testes
python tests/runner_p0_resiliencia_operacional_real.py 2>&1 | tee logs/RO_exec1_$(date +%s).log

# Salvar resultado
python tests/runner_p0_resiliencia_operacional_real.py > logs/resultado_exec1.json 2>&1
```

### Execução 2 e 3

Repetir o comando acima sem modificar código:

```bash
python tests/runner_p0_resiliencia_operacional_real.py 2>&1 | tee logs/RO_exec2_$(date +%s).log
python tests/runner_p0_resiliencia_operacional_real.py 2>&1 | tee logs/RO_exec3_$(date +%s).log
```

### Analisar Resultados

```bash
# Grep para passou/falhou
grep "PASSOU\|FALHOU\|BUG" logs/RO_exec*.log

# JSON final
cat logs/resultado_exec1.json | jq '.resumo'
```

---

## 🔍 Validar Após Execução

### Checklist por Teste

**RO-01 a RO-03, RO-06, RO-07, RO-12** (Idempotência)
- [ ] Contexto preservado após restart?
- [ ] Evento criado apenas 1 vez?
- [ ] Duplicação evitada?

**RO-04, RO-05** (Locks)
- [ ] Lock não bloqueia indefinidamente?
- [ ] Sistema recupera de lock expirado?
- [ ] Novo evento pode ser criado no mesmo slot?

**RO-08, RO-09** (Scheduler/Notificações)
- [ ] 1 notificação por evento (não duplicada)?
- [ ] Notificações vencidas não são disparadas?

**RO-10, RO-11** (Falhas externas)
- [ ] Nenhum evento parcial criado?
- [ ] Falha retorna erro seguro?

---

## 📊 Registrar Resultados

Após cada execução:

1. **Atualizar JSON**
   ```bash
   # Copiar resultado para template
   cp logs/resultado_exec1.json tests/resultado_p0_resiliencia_operacional_real.json
   ```

2. **Documentar achados**
   - Bugs encontrados → `MATRIZ_P0_RESILIENCIA_OPERACIONAL_REAL.md` (seção "Bugs Encontrados")
   - Observações → JSON (`observacoes_gerais`)

3. **Verificar limpeza Firestore**
   ```bash
   # Confirmar que dados de teste foram removidos
   # (Cada teste deve limpar seus dados ao final)
   ```

---

## 🐛 Se Encontrar Bug

1. **Documentar**
   ```json
   {
     "teste_id": "RO-XX",
     "tipo": "lock_orfo",
     "descricao": "Lock permanece sem evento associado",
     "como_reproduzir": "...",
     "severidade": "P0"
   }
   ```

2. **Não fazer patch YET** — Deixar para depois das 3 execuções

3. **Continuar testes** — Registre como "bug_encontrado" no status do teste

4. **Depois das 3 execuções:**
   - Analisar padrões
   - Criar patch mínimo
   - Reexecutar

---

## 🚀 Próximos Passos

1. **Execução 1**
   - [ ] Executar testes
   - [ ] Registrar resultados
   - [ ] Verificar se 12/12 passaram

2. **Execução 2**
   - [ ] Repetir sem mudanças
   - [ ] Comparar com Exec 1

3. **Execução 3**
   - [ ] Repetir novamente
   - [ ] Aprovar se 12/12 em 3 vezes

4. **Aprovação FASE 4**
   - [ ] 12/12 em 3 execuções? SIM → APROVADO
   - [ ] Bugs encontrados? Registrar e patchar
   - [ ] Atualizar MEMORIA.md

---

## 📞 Referências

- **Documentação completa:** `docs/auditorias/MATRIZ_P0_RESILIENCIA_OPERACIONAL_REAL.md`
- **Código dos testes:** `tests/runner_p0_resiliencia_operacional_real.py`
- **Regras críticas:** `CLAUDE.md` (Regra Zero + 13 regras)
- **Regra de resiliência:** CLAUDE.md § Regressão Obrigatória (Regra 13)

---

## ⚡ Dicas Rápidas

**Log é seu amigo:**
```bash
# Monitorar em tempo real
tail -f logs/RO_exec1.log | grep -i "passou\|falhou\|erro"

# Buscar teste específico
grep "RO-04" logs/RO_exec1.log -A 20
```

**Limpar antes de reexecutar:**
```bash
# Remover dados antigos de testes
rm tests/*.pyc logs/RO_exec*.log 2>/dev/null
```

**Validar estrutura:**
```bash
# Confirmar que todos os arquivos existem
test -f "tests/runner_p0_resiliencia_operacional_real.py" && echo "✅ Runner OK"
test -f "docs/auditorias/MATRIZ_P0_RESILIENCIA_OPERACIONAL_REAL.md" && echo "✅ Matriz OK"
test -f "tests/resultado_p0_resiliencia_operacional_real.json" && echo "✅ Resultado OK"
```

---

**Status:** Aguardando execução  
**Última atualização:** 2026-06-19  
**Crítica:** P0 — Resiliência do sistema em produção
