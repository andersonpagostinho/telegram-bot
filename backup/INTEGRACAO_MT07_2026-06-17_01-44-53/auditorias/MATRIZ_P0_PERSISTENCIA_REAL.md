# Matriz P0-PERSISTENCIA: Testes de Fluxo Real com Firestore

**Data**: 2026-06-16  
**Status**: TEMPLATE (pronto para validação)  
**Objetivo**: Detectar bugs que runners mockados não pegam através de ciclos reais de persistência

---

## 📋 Visão Geral

A bateria P0-PERSISTENCIA valida fluxos reais onde contexto é salvo em Firestore e recarregado entre mensagens. Diferencia-se dos testes tradicionais por:

- ✅ Usa Firestore real (dev environment)
- ✅ Salva e recarrega contexto de verdade
- ✅ Valida `json.dumps()` após reload
- ✅ Testa ciclo completo: msg1 → save → reload → msg2
- ✅ Detecta estruturas não-serializáveis

### Bugs Que Detecta

| Bug | Como Detecta | Exemplo |
|-----|-------------|---------|
| Contexto salvo ≠ contexto em memória | Reload e validar json.dumps | cancelamento_pendente com tuplas |
| Firestore rejeita estrutura | 400 Property contains invalid entity | candidatos: [(eid, ev)] |
| Próxima msg carrega estado errado | Passo 2 usa contexto carregado incorreto | aguardando_confirmacao=False mas deveria ser True |
| Handler errado intercepta | Resposta inesperada após reload | "Pode" volta para "Pode escolher" em vez de confirmar |
| Lixo transitório não limpo | Contexto cresce indefinidamente | motivo_estado ainda existe após profissional escolhido |

---

## 🧪 Testes Obrigatórios

### TESTE 1: Agendamento Completo com Confirmação

**Objetivo**: Validar ciclo básico agendamento → confirmação com recarregamento

**Configuração**:
- User: `USER_ID_TESTE`
- Tenant: `TENANT_ID_TESTE`

**Fluxo**:
```
1. "Quero corte com Bruna amanhã às 10"
   → save context
   → reload
2. "Pode"
   → validar confirmação
```

**Esperado**:
- ✅ Passo 1: resposta contém "corte", "Bruna", "amanhã", "10:00"
- ✅ Passo 1: estado_fluxo = "agendamento_pronto"
- ✅ Passo 1: json.dumps(ctx) funciona (sem tuplas/datetime)
- ✅ Passo 2: "Pode" confirma (resposta contém "confirmado")
- ✅ Passo 2: evento criado em Firestore
- ✅ Passo 2: contexto final limpo (aguardando_confirmacao_agendamento = None)

**Detecção de Bugs**:
- Se reload falhar: Firestore recusando estrutura
- Se "Pode" não confirmar: handler interceptando errado
- Se evento não criar: lógica de confirmação quebrada

---

### TESTE 2: Profissional Incompatível + Escolha + Confirmação

**Objetivo**: Validar transição entre rejeição → escolha → confirmação com reloads intermediários

**Configuração**:
- Contexto inicial pode conter draft antigo: `servico="botox capilar"`

**Fluxo**:
```
1. "Quero corte com Carla amanhã às 10"
   → resposta: Carla não atende corte
   → save context
   → reload

2. "Joana"
   → escolha profissional válido
   → save context
   → reload

3. "Pode"
   → confirmação
```

**Esperado**:
- ✅ Passo 1: resposta contém "Carla", "não atende", "corte"
- ✅ Passo 1: resposta NÃO contém "botox capilar" (nunca menciona draft antigo)
- ✅ Passo 1: estado_fluxo = "aguardando_profissional"
- ✅ Passo 1: motivo_estado = "profissional_nao_atende_servico"
- ✅ Após reload 1: servico = "corte" (não reverteu para botox)
- ✅ Passo 2: "Joana" detectada como profissional válido
- ✅ Após reload 2: motivo_estado = None (foi limpo)
- ✅ Após reload 2: profissional_rejeitado = None
- ✅ Após reload 2: profissionais_validos = None (lixo limpo)
- ✅ Passo 3: "Pode" confirma, NÃO responde "Pode escolher"
- ✅ Passo 3: evento criado com profissional="Joana"

**Detecção de Bugs**:
- Se botox capilar aparece: contexto antigo não foi limpo na rejeição
- Se motivo_estado persiste: limpeza de estado falhou no reload
- Se "Pode" responde "Pode escolher": handler P0 interceptando mesmo após limpeza

---

### TESTE 3: Cancelamento com Confirmação

**Objetivo**: Validar ciclo cancelamento → confirmação com recarregamento

**Pré-condição**:
```python
# Criar evento teste antes do fluxo:
evento_teste = {
    "descricao": "TEST_PERSISTENCIA_corte_bruna",
    "profissional": "Bruna",
    "data": "2026-06-17",
    "hora_inicio": "10:00",
    "cliente_id": USER_ID_TESTE,
    "status": "confirmado"
}
```

**Fluxo**:
```
1. "Quero cancelar o corte com a Bruna de amanhã"
   → resposta: "Tem certeza de cancelar...?"
   → save context
   → reload
   → validate json.dumps(ctx["cancelamento_pendente"])

2. "Sim"
   → cancela evento
```

**Esperado**:
- ✅ Passo 1: resposta contém "Tem certeza", "cancelar"
- ✅ Passo 1: estado_fluxo = "aguardando_confirmacao_cancelamento"
- ✅ Passo 1: cancelamento_pendente existe
- ✅ Passo 1: json.dumps(cancelamento_pendente) funciona (sem tuplas)
- ✅ Após reload: cancelamento_pendente carregado corretamente
- ✅ Passo 2: "Sim" cancela evento
- ✅ Passo 2: resposta contém "cancelado"
- ✅ Passo 2: resposta NÃO contém "Qual horário você prefere"
- ✅ Passo 2: resposta NÃO contém "Pode escolher"
- ✅ Passo 2: evento status = "cancelado" em Firestore
- ✅ Passo 2: cancelamento_pendente limpo (None)

**Detecção de Bugs**:
- Se json.dumps falhar no reload: estrutura não-serializável (tuplas, datetime)
- Se "Sim" não cancela: handler não processando após reload
- Se evento não cancela: lógica de cancelamento quebrada

---

### TESTE 4: Confirmação Pendente Vence motivo_estado

**Objetivo**: Validar que confirmação de agendamento tem prioridade sobre rejeição de profissional

**Configuração**:
```python
# Salvar artificialmente contexto com conflito:
ctx_conflito = {
    "aguardando_confirmacao_agendamento": True,
    "dados_confirmacao_agendamento": {
        "servico": "corte",
        "profissional": "Bruna",
        "data_hora": "2026-06-17 10:00"
    },
    "motivo_estado": "profissional_nao_atende_servico",
    "profissional_rejeitado": "Carla",
    "profissionais_validos": ["Bruna", "Gloria", "Joana"]
}
await salvar_contexto_temporario(USER_ID_TESTE, ctx_conflito)
```

**Fluxo**:
```
1. reload contexto
2. "Pode"
```

**Esperado**:
- ✅ Passo 1: contexto carregado com conflito intencional
- ✅ Passo 2: "Pode" confirma agendamento (não lista profissionais)
- ✅ Passo 2: resposta contém "confirmado", "agendado"
- ✅ Passo 2: resposta NÃO contém "Pode escolher"
- ✅ Passo 2: handler de confirmação executou ANTES de handler P0

**Detecção de Bugs**:
- Se "Pode" responde "Pode escolher": handler P0 interceptou antes de handler confirmação
- Se evento não cria: handler confirmação não rodar com prioridade

---

### TESTE 5: Serviço Inexistente após Reload

**Objetivo**: Validar que serviço inválido não contamina contexto

**Fluxo**:
```
1. "Quero massagem com Bruna amanhã às 10"
   → resposta: serviço não existe
   → save context
   → reload
```

**Esperado**:
- ✅ Passo 1: resposta contém "não encontrei", "massagem", "catálogo"
- ✅ Passo 1: resposta NÃO contém "agendado"
- ✅ Passo 1: servico = None (não salvou inválido)
- ✅ Após reload: json.dumps(ctx) funciona
- ✅ Após reload: draft não contém "massagem" como serviço

**Detecção de Bugs**:
- Se serviço="massagem" persiste: validação não rejeitou
- Se json.dumps falha: erro no salvamento do erro

---

### TESTE 6: Interrupção Informativa Preserva Draft

**Objetivo**: Validar que perguntas complementares não limpam agendamento pendente

**Fluxo**:
```
1. "Quero corte com Bruna amanhã às 10"
   → resposta: "Confirma?"
   → save context
   → reload

2. "Qual o endereço?"
   → resposta: informação sobre endereço
   → save context
   → reload

3. "Pode"
   → confirmação
```

**Esperado**:
- ✅ Passo 1: aguardando_confirmacao_agendamento = True
- ✅ Após reload 1: aguardando_confirmacao_agendamento ainda True
- ✅ Passo 2: resposta contém endereço (informação)
- ✅ Passo 2: estado_fluxo = "agendamento_pronto" (não mudou)
- ✅ Após reload 2: aguardando_confirmacao_agendamento ainda True
- ✅ Passo 3: "Pode" confirma (não foi limpo)
- ✅ Passo 3: evento criado

**Detecção de Bugs**:
- Se aguardando_confirmacao virar False: lógica de perguntas limpou demais
- Se "Pode" não confirma: draft foi perdido

---

## 🔧 Implementação

### Estrutura do Teste

Cada teste segue ciclo:

```python
async def executar_teste(teste: TestCasePersistencia) -> bool:
    # 1. Limpar MemoriaTemporaria
    await limpar_contexto_teste()
    
    for passo in teste.passos:
        # 2. Enviar mensagem (caminho real do bot/router)
        resposta = await roteador_principal(
            user_id=USER_ID_TESTE,
            mensagem=passo.mensagem_usuario
        )
        
        # 3. Salvar (acontece dentro do router)
        # (via salvar_contexto_temporario())
        
        # 4. Recarregar contexto
        ctx = await carregar_contexto_temporario(USER_ID_TESTE)
        
        # 5. Validar serializabilidade
        try:
            json.dumps(ctx, ensure_ascii=False)
            passo.serializavel = True
        except TypeError:
            passo.serializavel = False
            passo.passou = False
        
        # 6. Validações de resposta/contexto
        # (contém/não contém, estado_fluxo esperado, etc)
        
        # 7. Próxima mensagem usa contexto recarregado
        # (ocorre automaticamente no ciclo)
```

### Limpeza

Ao final de cada teste:
```python
# Remover eventos criados com prefixo TEST_PERSISTENCIA_
await remover_eventos_teste()

# Limpar contexto
await limpar_contexto_teste()
```

---

## 📊 Resultado JSON

```json
{
  "suite": "p0_persistencia_real",
  "versao": "1.0",
  "data": "2026-06-16T22:30:00",
  "total_testes": 6,
  "passou": 6,
  "falhou": 0,
  "taxa_sucesso": "100.0%",
  "testes": [
    {
      "id": 1,
      "nome": "Agendamento completo com confirmação",
      "status": "PASSOU",
      "passos": [
        {
          "numero": 1,
          "mensagem_usuario": "Quero corte com Bruna amanhã às 10",
          "resposta_real": "...",
          "serializavel": true,
          "passou": true
        }
      ],
      "eventos_criados": ["evt_123"],
      "passou": true
    }
  ]
}
```

---

## 🚀 Como Rodar

```bash
# Rodar apenas P0-PERSISTENCIA
python tests/runner_p0_persistencia_real.py

# Com verbose
python tests/runner_p0_persistencia_real.py --verbose

# Apenas teste específico
python tests/runner_p0_persistencia_real.py --teste 3

# Não incluir em agregador ainda (3 execuções limpas antes)
# python tests/run_p0_regressions.py  # NÃO inclui persistencia
```

---

## ✅ Critérios de Sucesso

- [ ] Todos 6 testes passando 100%
- [ ] json.dumps funciona em todos os reloads
- [ ] Nenhuma tupla, datetime ou DocumentSnapshot no contexto
- [ ] Eventos criados/cancelados como esperado
- [ ] Respostas corretas após reload
- [ ] Contexto final sem lixo transitório

---

## 📝 Notas

1. **Não alterar produto nesta etapa**: Template apenas
2. **Usar Firestore dev**: Sempre
3. **Prefixo TEST_PERSISTENCIA_**: Para eventos criados
4. **3 execuções limpas antes de agregador**: Validação pré-produção
5. **Cada reload é crítico**: Onde bugs aparecem

---

**Próximos Passos**:
1. ✅ Criar template (feito)
2. ⏳ Implementar chamadas reais ao router/Firestore
3. ⏳ Executar e validar 3x consecutivas
4. ⏳ Incluir em run_p0_regressions.py
