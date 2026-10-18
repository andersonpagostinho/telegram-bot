# 🎯 PLANO DE VALIDAÇÃO — P0 174 TESTES COMPLETOS

**Data**: 2026-10-18  
**Status**: ⏳ EXECUÇÃO EM BACKGROUND  
**Regra de Ouro**: Todos os testes devem validar até Firestore (não apenas resposta)

---

## 📋 ESTRATÉGIA DE TESTE

### Nível 1: Criação Real de Evento
```python
✅ Evento criado em Firestore
   - Clientes/{tenant_id}/Eventos/{evento_id}
   - Campos: profissional, data, hora, cliente_id, status=confirmado
```

### Nível 2: Persistência Completa
```python
✅ Todos os campos persistidos:
   - Confirmação de agendamento (confirmado=True)
   - Timestamp correto
   - Tenant isolado (não cai em outro tenant)
   - Cliente linkado corretamente
```

### Nível 3: Fluxo Até Confirmação
```python
✅ Sequência completa:
   1. Mensagem WhatsApp entra
   2. Router processa
   3. add_evento_por_gpt() executado
   4. Validação de expediente passou
   5. Evento criado em Firestore
   6. Notificações agendadas
   7. Mensagem de confirmação gerada
   8. Firestore revisitado para validar
```

---

## 📊 ARQUIVOS P0 SENDO TESTADOS

### Categoria 1: Firebase Real Completo
| Arquivo | Testes | Validação |
|---------|--------|-----------|
| `test_p01_firebase_real_simple.py` | **53** | Evento em Firestore |
| `test_p01_confirmacao_firebase_real.py` | **18** | Confirmação salva |
| `test_p01_identidade_contexto.py` | **20** | Actor/Tenant isolado |

### Categoria 2: Fase Execução
| Arquivo | Testes | Validação |
|---------|--------|-----------|
| `test_cenarios_reais_primeira_mensagem_e2e.py` | **7** | E2E completo |
| `test_p02_executor_multicanal.py` | **7** | Multi-canal |
| `test_p0_p1_fixes_implementation.py` | **10** | Fixes implementados |

### Categoria 3: Validação Específica
| Arquivo | Testes | Validação |
|---------|--------|-----------|
| `test_c310_fase1_indice_derivado.py` | **9** | Índice derivado |
| `test_fase_47_alternativas_stale.py` | **10** | Alternativas stale |

---

## ✅ MÉTRICAS DE SUCESSO

### Métrica 1: Taxa de Cobertura
```
Total de testes: 169+
Esperado PASS: 95%+ (testes realmente devem validar)
Tolerância: Máximo 5% FAIL (bugs conhecidos)
```

### Métrica 2: Validação Firestore
```
Cada teste DEVE:
- ✅ Criar evento em Clientes/{tenant_id}/Eventos
- ✅ Validar status=confirmado
- ✅ Confirmar isolamento tenant
- ✅ Verificar timestamp
```

### Métrica 3: Ausência de Regressão
```
Padrão anterior (conhecidos como funcionando):
- Confirmação de agendamento
- Isolamento multi-tenant
- Idempotência de evento
```

---

## 🔍 O QUE NÃO DEVE ACONTECER

### ❌ Erro Tipo 1: Evento criado em Clientes/{user_id}
```
[FAIL] Evento em: Clientes/whatsapp:551991382080/Eventos
Esperado: Clientes/tenant_id/Eventos
```

### ❌ Erro Tipo 2: Notification salva em Clientes/None
```
[FAIL] Notificação em: Clientes/None/NotificacoesAgendadas
Causa: tenant_id não propagado corretamente
```

### ❌ Erro Tipo 3: Event sem confirmação
```
[FAIL] Campo confirmado=False em evento criado
Esperado: confirmado=True após validação
```

### ❌ Erro Tipo 4: Crash em add_evento_por_gpt
```
[FAIL] UnboundLocalError ou AttributeError
Esperado: Fluxo completo sem erro
```

---

## 🎯 VALIDAÇÕES AUTOMÁTICAS A FAZER

Após conclusão dos testes, validar:

### 1. Verificação de Padrões
```bash
# Procurar por padrões de erro
grep -r "Clientes/[^/]*/[^/]*/Eventos" EXECUCAO_P0_174_2026_10_18.json
# Resultado esperado: VAZIO (nenhum evento fora do padrão)
```

### 2. Contagem de Testes
```bash
# Verificar que todos os 169 testes foram coletados
pytest tests/test_p0* --collect-only -q | wc -l
# Resultado esperado: 169+
```

### 3. Taxa de Sucesso
```bash
# Extrair resultados do json
python -c "
import json
with open('EXECUCAO_P0_174_2026_10_18.json') as f:
    data = json.load(f)
print(f'Total: {data[\"total_testes_estimado\"]}')
print(f'Taxa: {data[\"passed\"]}/{data[\"total_testes_estimado\"]}')
"
```

---

## 📈 TEMPO ESTIMADO

| Fase | Duração |
|------|---------|
| **Setup** | ~10s |
| **Testes P0** | ~300-600s (169 testes) |
| **Limpeza** | ~30s |
| **TOTAL** | ~6-12 minutos |

---

## 🚨 AÇÃO SE HOUVER FALHAS

Se taxa de PASS < 95%:

### 1. Coletar Dados
```bash
pytest tests/test_p01_firebase_real_simple.py -v --tb=short
```

### 2. Analisar Erro
- Mensagem de erro?
- Tipo de falha (assertion vs crash)?
- Padrão de falha (mesmo arquivo vs múltiplos)?

### 3. Investigar Causa
- Regressão (foi passando antes)?
- Novo bug descoberto?
- Ambiente (Firestore, variáveis)?

---

## 🎉 PRÓXIMOS PASSOS APÓS SUCESSO

1. **Commit**: Push das mudanças com evidência dos testes
2. **Deploy**: Ir para produção com confiança
3. **Monitor**: Acompanhar em produção real (WhatsApp)

---

## 📝 STATUS ATUAL

✅ **Executor criado**  
⏳ **Testes em execução (background)**  
⏳ **Aguardando conclusão**  

Acompanhamento em: `EXECUCAO_P0_174_2026_10_18.json`

