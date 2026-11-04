# CHECKLIST — DEPLOY EM PRODUÇÃO
## P0 Humanização da Eve — Commit e48ce5c

**Data**: 2026-11-01  
**Commit**: e48ce5cc2830ec75c7ecf39c92a1b768eed775eb  
**Branch**: main  
**Status**: Pronto para monitoramento pós-deploy

---

## ✅ PRÉ-DEPLOY (CONCLUÍDO)

- [x] Commit e48ce5c em origin/main
- [x] render.yaml configurado
- [x] Nenhum deploy concorrente
- [x] Histórico de commits limpo
- [x] Testes E2E: 4/4 PASSED
- [x] Auditoria READ-ONLY: 10/10 PASSED

---

## 📋 PASSOS PÓS-DEPLOY (A EXECUTAR)

### 1. Acompanhar logs de inicialização do Render

**Ação**:
1. Acessar painel do Render (https://dashboard.render.com)
2. Selecionar serviço "telegram-bot"
3. Abrir aba "Logs"
4. Procurar por:
   - ✅ Build iniciado (timestamp 2026-11-01)
   - ✅ `pip install -r requirements.txt` — sem erros
   - ✅ `python main.py` — iniciado com sucesso
   - ✅ Nenhuma exceção não tratada

**Indicadores de sucesso**:
```
Building (timestamp)
Installing dependencies...
Installation complete ✓
Starting application...
[INFO] Roteador Principal inicializado ✓
[INFO] Webhook WhatsApp ativo ✓
```

**Indicadores de erro**:
- Qualquer traceback Python
- "requirements not met"
- "Module not found"
- "Connection refused" para Firestore/GPT

---

### 2. Executar testes de fumaça no webhook

**Ação**: Enviar mensagens de teste pelo WhatsApp para validar:

#### Teste 1: Saudação inicial (MSG-001)
```
Usuario: Olá
Esperado: "Voltamos! 😊 Como posso ajudar com seu agendamento?"
(não deve exibir "Reiniciamos a conversa 🔄")
```

#### Teste 2: Apresentação (MSG-002)
```
Usuario: Oi
Esperado: "Oi! 👋 Sou a Eve, secretária aqui. Posso ajudar com agendamentos..."
(deve se apresentar como Eve)
```

#### Teste 3: Serviço (MSG-003)
```
Usuario: Quero agendar
Esperado: "Qual serviço você gostaria? Posso ajudar com:"
(não deve dizer "Perfeito. Qual serviço você quer agendar?")
```

#### Teste 4: Cancelamento (MSG-012, MSG-013)
```
Usuario: Cancelar
(após seleção)
Esperado: "Pronto, cancelei. Precisar de algo mais, é só chamar!"
(não deve dizer "Tudo bem! Cancelei o agendamento. Posso ajudar em algo mais?")
```

#### Teste 5: Erro (MSG-014)
```
Usuario: [mensagem incoerente]
Esperado: "Não consegui entender. Pode tentar de novo, com mais detalhes?"
(não deve dizer "Desculpe, não entendi. Pode reformular?")
```

#### Teste 6: MSG-010 preservada (não alterada)
```
Usuario: [após selecionar data/hora/prof]
Esperado: "Só confirmando 😊\n\nVocê quer agendar seu *[servico]* com a *[prof]* para *[data]*?\n\nResponda *sim* para confirmar o agendamento."
(deve conter a instrução "Responda *sim*" — não foi alterada)
```

---

### 3. Validar que a Eve responde normalmente

**Checklist de funcionalidade**:

- [ ] Eve responde a saudações
- [ ] Eve reconhece serviços do catálogo
- [ ] Eve oferece profissionais disponíveis
- [ ] Eve valida datas/horários
- [ ] Eve detecta conflitos de horário
- [ ] Eve permite cancelamento
- [ ] Eve reconhece confirmações ("sim", "pode", "ok")
- [ ] Eve não expõe erros técnicos ao usuário
- [ ] Eve mantém contexto de sessão
- [ ] Nenhuma mensagem duplicada

---

## 📊 MÉTRICAS DE VALIDAÇÃO

### Performance
- [ ] Resposta inicial: < 5s
- [ ] Resposta após validação: < 10s
- [ ] Sem timeout de webhook

### Comportamento
- [ ] 12 mensagens humanizadas ativas
- [ ] MSG-010, MSG-007, MSG-009 preservadas
- [ ] Fluxos silenciosos funcionando
- [ ] Nenhuma chamada GPT extra

### Logs
- [ ] Nenhuma exceção não tratada
- [ ] Nenhum erro de Firestore
- [ ] Contexto salvo e recuperado corretamente

---

## 🔴 ROLLBACK (Se necessário)

**Procedimento**:
1. Acessar Render dashboard
2. Selecionar "Deployments"
3. Selecionar commit anterior (2b4a496)
4. Clicar "Redeploy"
5. Acompanhar logs até inicialização

**Motivos para rollback**:
- Erros críticos em produção
- Testes de fumaça falhando
- Taxa de erro > 5%
- Timeout de webhook

---

## ✅ SUCESSO DO DEPLOY

Se todos os testes de fumaça passarem:

```
✅ DEPLOY CONCLUÍDO COM SUCESSO
- Commit e48ce5c ativo em produção
- 12 mensagens humanizadas validadas
- Testes de fumaça: PASS
- Sem regressão detectada
- Pronto para monitoramento contínuo
```

---

## 📝 NOTAS IMPORTANTES

1. **Os 4 testes E2E não comprovam funcionamento em produção por si só**
   - Testes rodam em ambiente isolado
   - Produção tem variáveis não testadas (latência, concorrência, volume)
   - Validação manual é obrigatória

2. **Monitorar por 24h após deploy**
   - Taxa de erro
   - Latência de resposta
   - Falhas de contexto

3. **Fluxos silenciosos preservados**
   - 27 casos de fluxo sem resposta
   - Verificar se continuam sem resposta

4. **Variáveis dinâmicas ativas**
   - `catalogo_servicos`
   - `profissionais_validos`
   - `data_hora`
   - Validar interpolação em produção

---

**Documento preparado em**: 2026-11-01  
**Status**: Aguardando monitoramento pós-deploy  
**Próximo**: Executar testes de fumaça conforme este checklist

