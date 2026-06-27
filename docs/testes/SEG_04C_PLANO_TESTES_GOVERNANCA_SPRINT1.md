# SEG-04C — PLANO DE TESTES DA GOVERNANÇA
## Sprint 1: MEC-03 + MEC-04

**Status:** Especificação de Testes (Sem Implementação)  
**Data:** 2026-06-23  
**Baseline:** 216/216 PASS (Congelado)  
**Total de Testes Planejados:** 28  
**Referência:** SEG-04, SEG-04A, SEG-04B  

---

## RESUMO EXECUTIVO

### Estrutura de Testes

| Grupo | Nome | Qtd | Escopo |
|-------|------|-----|--------|
| **G1** | Override Manual | 4 | MEC-03 (pausa) |
| **G2** | Whitelist | 5 | Operações protegidas |
| **G3** | Fluxo Ativo | 4 | Continuidade de fluxo |
| **G4** | Modo Dono | 5 | MEC-04 (3 modos) |
| **G5** | Persistência | 4 | Governanca + Auditoria |
| **G6** | Multi-tenant | 2 | Isolamento de tenants |
| **G7** | Regressão | 4 | P1 E2E + P0 |
| | | **28** | |

---

## FIXTURE COMPARTILHADA

### Setup Base para Todos os Testes

```python
# tenant_id configurado em environment
TENANT_ID = os.getenv("TENANT_ID", "audit_cenario_05_gpt")

# Ator principal
ACTOR_ID = "whatsapp:5511999005"
DONO_ID = "whatsapp:5511888888"

# Firestore client
db = firestore_client.get_db()

async def setup_test():
    """Limpar e preparar Firestore para teste"""
    # Limpar documentos de teste anteriores
    await salvar_dado_em_path(
        path=f"Clientes/{TENANT_ID}/Governanca/{ACTOR_ID}",
        data={},  # Vazio = sem governo ativa
        delete=True
    )
    await salvar_dado_em_path(
        path=f"Clientes/{TENANT_ID}/Sessoes/{ACTOR_ID}",
        data={"estado_fluxo": "vazio"},
        tenant_id=TENANT_ID
    )

async def teardown_test():
    """Limpar após teste"""
    await salvar_dado_em_path(
        path=f"Clientes/{TENANT_ID}/Governanca/{ACTOR_ID}",
        data={},
        delete=True
    )
```

---

## GRUPO G1 — OVERRIDE MANUAL (MEC-03)

### G1.01: Contato Pausado Envia Agendamento Novo

**ID:** G1.01  
**Nome:** Pausa bloqueia agendamento novo  
**Classificação:** Crítica (CA-01)  
**Tempo Estimado:** 30s  

#### Pré-condições

```
- ACTOR_ID sem Governanca anterior
- estado_fluxo = "vazio"
- Firestore limpo
```

#### Dados de Entrada

```python
governanca = {
    "responder_automaticamente": False,
    "bloqueado_ate": None,
    "modo_dono": "normal",
    "atualizado_em": datetime.now(timezone.utc).isoformat(),
    "_tenant_id_guard": TENANT_ID,
}

mensagem = "Agende corte com Bruna amanhã às 15h"
```

#### Passos

```
1. Salvar Governanca com responder_automaticamente = false
2. Chamar verificar_governanca(ACTOR_ID, DONO_ID, ctx)
3. Registrar resultado
```

#### Resultado Esperado

```python
{
    "bloqueado": True,
    "motivo": "MEC-03-OVERRIDE-MANUAL",
    "resposta": "Estou pausado no momento."
}
```

#### Critério de Aprovação

- ✅ governanca.responder_automaticamente = false
- ✅ verificar_governanca retorna bloqueado=True
- ✅ Mensagem retornada é "Estou pausado"
- ✅ Nenhuma resposta IA é gerada
- ✅ Nenhum agendamento é criado

#### Risco de Bloqueio

✅ BAIXO — Comportamento esperado

---

### G1.02: Contato Pausado Envia Consulta Disponibilidade

**ID:** G1.02  
**Nome:** Pausa bloqueia consulta disponibilidade  
**Classificação:** Crítica (CA-01)  
**Tempo Estimado:** 30s  

#### Pré-condições

```
- Mesmo que G1.01
```

#### Dados de Entrada

```python
governanca = {
    "responder_automaticamente": False,
    ...
}

mensagem = "Quando tem horário disponível?"
```

#### Passos

```
1. Pausado como G1.01
2. Enviar consulta disponibilidade
3. Verificar bloqueio
```

#### Resultado Esperado

```python
{
    "bloqueado": True,
    "motivo": "MEC-03-OVERRIDE-MANUAL",
    "resposta": "Estou pausado no momento."
}
```

#### Critério de Aprovação

- ✅ Bloqueado
- ✅ Sem resposta IA
- ✅ Sem consulta a disponibilidade

#### Risco de Bloqueio

✅ BAIXO — Comportamento esperado

---

### G1.03: Contato Retomado Envia Agendamento Novo

**ID:** G1.03  
**Nome:** Retomada permite agendamento novo  
**Classificação:** Crítica (CA-02)  
**Tempo Estimado:** 1m  

#### Pré-condições

```
- ACTOR_ID com responder_automaticamente = false
- Executar /retomar primeiro
```

#### Dados de Entrada

```python
# Passo 1: Verificar que está pausado
governanca_antes = {
    "responder_automaticamente": False,
    ...
}

# Passo 2: Executar /retomar
comando = "/retomar"

# Passo 3: Verificar que está retomado
governanca_depois = {
    "responder_automaticamente": True,
    "bloqueado_ate": None,
    ...
}

mensagem = "Agende corte com Bruna amanhã"
```

#### Passos

```
1. Confirmar ACTOR_ID pausado (G1.01)
2. Enviar /retomar
3. Verificar Governanca atualizado
4. Enviar agendamento novo
5. Verificar que permite
```

#### Resultado Esperado

```
1. /retomar processa com sucesso
2. responder_automaticamente = true
3. Agendamento é processado
4. Retorna fluxo normal
```

#### Critério de Aprovação

- ✅ Governanca.responder_automaticamente = true
- ✅ Próxima mensagem não é bloqueada
- ✅ Fluxo de agendamento inicia
- ✅ AuditoriaGovernanca evento criado para /retomar

#### Risco de Bloqueio

✅ BAIXO — Teste sequencial de G1.01

---

### G1.04: Contato Pausado Envia Mensagem Pessoal

**ID:** G1.04  
**Nome:** Pausa bloqueia mensagem comum  
**Classificação:** Média  
**Tempo Estimado:** 30s  

#### Pré-condições

```
- Mesmo que G1.01
```

#### Dados de Entrada

```python
governanca = {
    "responder_automaticamente": False,
    ...
}

mensagem = "Como você está?"
```

#### Passos

```
1. Pausado como G1.01
2. Enviar mensagem pessoal
3. Verificar bloqueio
```

#### Resultado Esperado

```python
{
    "bloqueado": True,
    "motivo": "MEC-03-OVERRIDE-MANUAL",
    "resposta": "Estou pausado no momento."
}
```

#### Critério de Aprovação

- ✅ Bloqueado (mesmo mensagem pessoal)
- ✅ Sem resposta IA
- ✅ Classificador não é chamado

#### Risco de Bloqueio

✅ BAIXO — Bloqueio anterior ao classificador

---

## GRUPO G2 — WHITELIST (CLASSE A)

### G2.01: Contato Pausado Confirma "sim"

**ID:** G2.01  
**Nome:** Whitelist confirmação positiva  
**Classificação:** Crítica (CA-01, A-01)  
**Tempo Estimado:** 1m  

#### Pré-condições

```
- ACTOR_ID pausado (responder_automaticamente = false)
- estado_fluxo = "aguardando_confirmacao"
- Sistema aguardando resposta sim/não
```

#### Dados de Entrada

```python
governanca = {
    "responder_automaticamente": False,
    ...
}

sessao = {
    "estado_fluxo": "aguardando_confirmacao",
    "proposta_agendamento": {
        "profissional": "Bruna",
        "horario": "2026-06-24T15:00:00Z"
    }
}

mensagem = "sim"
```

#### Passos

```
1. Criar fluxo ativo com proposta de agendamento
2. Pausar ACTOR_ID
3. Enviar "sim"
4. Verificar processamento
```

#### Resultado Esperado

```
1. Mensagem "sim" é processada
2. Agendamento é confirmado
3. estado_fluxo muda de "aguardando_confirmacao"
4. Sem mensagem de bloqueio
```

#### Critério de Aprovação

- ✅ estado_fluxo != "aguardando_confirmacao" após teste
- ✅ Agendamento confirmado (confirmacao_pendente = false)
- ✅ AuditoriaGovernanca NÃO registra bloquei (é whitelist)
- ✅ Não retorna "Estou pausado"

#### Risco de Bloqueio

🔴 CRÍTICO — Se bloquear, agendamento fica travado

---

### G2.02: Contato Pausado Confirma "não"

**ID:** G2.02  
**Nome:** Whitelist confirmação negativa  
**Classificação:** Crítica (CA-01, A-02)  
**Tempo Estimado:** 1m  

#### Pré-condições

```
- Mesmo que G2.01
```

#### Dados de Entrada

```python
# Mesmo setup que G2.01, mas:
mensagem = "não"
```

#### Passos

```
1. Mesmo que G2.01, mas enviar "não"
```

#### Resultado Esperado

```
1. Mensagem "não" é processada
2. Agendamento é cancelado/recusado
3. estado_fluxo muda
4. Sem mensagem de bloqueio
```

#### Critério de Aprovação

- ✅ Negação processada
- ✅ Fluxo termina normalmente
- ✅ Não retorna "Estou pausado"

#### Risco de Bloqueio

🔴 CRÍTICO — Mesmo que G2.01

---

### G2.03: Contato Pausado Cancela Agendamento

**ID:** G2.03  
**Nome:** Whitelist cancelamento  
**Classificação:** Crítica (CA-01, A-03)  
**Tempo Estimado:** 1m  

#### Pré-condições

```
- ACTOR_ID pausado
- Com agendamento anterior confirmado
```

#### Dados de Entrada

```python
governanca = {
    "responder_automaticamente": False,
    ...
}

mensagem = "Cancelar meu horário de amanhã"
```

#### Passos

```
1. Pausar ACTOR_ID
2. Enviar cancelamento
3. Verificar processamento
```

#### Resultado Esperado

```
1. Cancelamento é processado
2. Agendamento é marcado como cancelado
3. Sem mensagem de bloqueio
```

#### Critério de Aprovação

- ✅ Agendamento cancelado
- ✅ Não retorna "Estou pausado"
- ✅ Sistema reconhece cancelamento válido

#### Risco de Bloqueio

🔴 CRÍTICO — Cancelamento é direito inalienável

---

### G2.04: Contato Pausado Refina Cancelamento

**ID:** G2.04  
**Nome:** Whitelist refinamento de cancelamento  
**Classificação:** Média (A-04)  
**Tempo Estimado:** 1m  

#### Pré-condições

```
- ACTOR_ID pausado
- Acaba de executar cancelamento
```

#### Dados de Entrada

```python
governanca = {
    "responder_automaticamente": False,
    ...
}

# Após G2.03
mensagem_refinamento = "Mas deixa marcado próxima semana"
```

#### Passos

```
1. Cancelar (G2.03)
2. Enviar refinamento
3. Verificar processamento
```

#### Resultado Esperado

```
1. Refinamento é processado
2. Novo agendamento criado
3. Sem bloqueio
```

#### Critério de Aprovação

- ✅ Refinamento processado
- ✅ Novo agendamento próxima semana
- ✅ Não retorna "Estou pausado"

#### Risco de Bloqueio

🔴 CRÍTICO — Continuidade de cancelamento

---

### G2.05: Contato Pausado Executa Comando Admin

**ID:** G2.05  
**Nome:** Whitelist comando administrativo  
**Classificação:** Crítica (A-06)  
**Tempo Estimado:** 30s  

#### Pré-condições

```
- ACTOR_ID pausado (responder_automaticamente = false)
```

#### Dados de Entrada

```python
governanca_antes = {
    "responder_automaticamente": False,
    ...
}

comando = "/retomar"
```

#### Passos

```
1. Pausar ACTOR_ID
2. Enviar /retomar
3. Verificar execução
4. Verificar Governanca atualizado
```

#### Resultado Esperado

```
1. Comando é reconhecido
2. Executado sem bloqueio
3. responder_automaticamente = true
4. AuditoriaGovernanca criado
```

#### Critério de Aprovação

- ✅ Comando executado
- ✅ Governanca.responder_automaticamente = true
- ✅ Não bloqueado por pausa
- ✅ Auditoria registrada

#### Risco de Bloqueio

🔴 CRÍTICO — Comando é para desfazer bloqueio

---

## GRUPO G3 — FLUXO ATIVO

### G3.01: Conflito Existente + Escolha de Alternativa

**ID:** G3.01  
**Nome:** Whitelist sugestão de conflito  
**Classificação:** Média (B-06)  
**Tempo Estimado:** 1m  

#### Pré-condições

```
- ACTOR_ID pausado
- estado_fluxo = "processando_agendamento"
- Sistema detectou conflito de horário
```

#### Dados de Entrada

```python
governanca = {
    "responder_automaticamente": False,
    ...
}

sessao = {
    "estado_fluxo": "processando_agendamento",
    "conflito_horario": True,
}

mensagem_sistema = "Bruna não tem 15h, mas Maria tem"

resposta_contato = "Ok, marca com Maria"
```

#### Passos

```
1. Criar fluxo de agendamento com conflito
2. Sistema oferece alternativa
3. Pausar ACTOR_ID
4. Contato escolhe alternativa
5. Verificar continuidade
```

#### Resultado Esperado

```
1. Sistema envia sugestão mesmo pausado
2. Resposta do contato é processada
3. Agendamento continua
```

#### Critério de Aprovação

- ✅ Sugestão enviada (continuidade de fluxo)
- ✅ Resposta processada
- ✅ Agendamento com Maria confirmado
- ✅ Não bloqueado por pausa

#### Risco de Bloqueio

⚠️ MÉDIO — Requer whitelist de continuidade

---

### G3.02: Escolha de Horário Sugerido

**ID:** G3.02  
**Nome:** Whitelist escolha de horário  
**Classificação:** Média (B-08)  
**Tempo Estimado:** 1m  

#### Pré-condições

```
- ACTOR_ID pausado
- estado_fluxo = "oferecendo_opcoes"
- Sistema ofereceu múltiplas opções
```

#### Dados de Entrada

```python
governanca = {
    "responder_automaticamente": False,
    ...
}

sessao = {
    "estado_fluxo": "oferecendo_opcoes",
    "opcoes": ["15h", "16h", "17h"]
}

resposta = "Prefiro 16h"
```

#### Passos

```
1. Criar fluxo com opções
2. Pausar ACTOR_ID
3. Enviar escolha
4. Verificar processamento
```

#### Resultado Esperado

```
1. Escolha é processada
2. Horário 16h é selecionado
3. Fluxo continua
```

#### Critério de Aprovação

- ✅ Escolha processada
- ✅ Horário confirmado
- ✅ Não bloqueado por pausa

#### Risco de Bloqueio

⚠️ MÉDIO — Requer whitelist de continuidade

---

### G3.03: Escolha de Profissional Sugerido

**ID:** G3.03  
**Nome:** Whitelist escolha de profissional  
**Classificação:** Média (B-09)  
**Tempo Estimado:** 1m  

#### Pré-condições

```
- ACTOR_ID pausado
- estado_fluxo = "escolhendo_profissional"
- Sistema ofereceu profissionais
```

#### Dados de Entrada

```python
governanca = {
    "responder_automaticamente": False,
    ...
}

sessao = {
    "estado_fluxo": "escolhendo_profissional",
    "profissionais": ["Bruna", "Maria", "Ana"]
}

resposta = "Prefiro Bruna"
```

#### Passos

```
1. Criar fluxo com profissionais
2. Pausar ACTOR_ID
3. Enviar escolha
4. Verificar processamento
```

#### Resultado Esperado

```
1. Escolha é processada
2. Profissional Bruna é selecionado
3. Fluxo continua
```

#### Critério de Aprovação

- ✅ Escolha processada
- ✅ Profissional confirmado
- ✅ Não bloqueado por pausa

#### Risco de Bloqueio

⚠️ MÉDIO — Requer whitelist de continuidade

---

### G3.04: Ajuste Incremental Durante Fluxo Ativo

**ID:** G3.04  
**Nome:** Whitelist ajuste incremental  
**Classificação:** Média (B-05)  
**Tempo Estimado:** 1m  

#### Pré-condições

```
- ACTOR_ID pausado
- estado_fluxo = "agendando"
- Sistema em fluxo de agendamento
```

#### Dados de Entrada

```python
governanca = {
    "responder_automaticamente": False,
    ...
}

sessao = {
    "estado_fluxo": "agendando",
    "proposta": {"horario": "15h", "profissional": "Bruna"}
}

ajuste = "Mas prefiro 16h"
```

#### Passos

```
1. Criar fluxo de agendamento
2. Pausar ACTOR_ID
3. Enviar ajuste
4. Verificar processamento
```

#### Resultado Esperado

```
1. Ajuste é processado
2. Horário atualizado para 16h
3. Fluxo continua
```

#### Critério de Aprovação

- ✅ Ajuste processado
- ✅ Proposta atualizada
- ✅ Não bloqueado por pausa

#### Risco de Bloqueio

⚠️ MÉDIO — Requer whitelist de continuidade

---

## GRUPO G4 — MODO DONO (MEC-04)

### G4.01: Dono em Modo Normal

**ID:** G4.01  
**Nome:** Dono modo normal = comportamento atual  
**Classificação:** Crítica (CA-05)  
**Tempo Estimado:** 30s  

#### Pré-condições

```
- DONO_ID sem Governanca anterior
- modo_dono = "normal" (default)
```

#### Dados de Entrada

```python
governanca = {
    "modo_dono": "normal",  # Default ou explícito
    ...
}

mensagem = "Agende corte"
```

#### Passos

```
1. Verificar Governanca com modo_dono = normal
2. Enviar mensagem
3. Verificar que não bloqueia
```

#### Resultado Esperado

```
1. Mensagem processada normalmente
2. Fluxo cliente completo
3. Sem bloqueio
```

#### Critério de Aprovação

- ✅ Modo normal = sem bloqueio
- ✅ Comportamento idêntico a baseline
- ✅ Fluxo cliente executa

#### Risco de Bloqueio

✅ BAIXO — Modo padrão

---

### G4.02: Dono Silencioso Envia Intenção Operacional

**ID:** G4.02  
**Nome:** Silencioso bloqueia operação  
**Classificação:** Crítica (CA-03)  
**Tempo Estimado:** 30s  

#### Pré-condições

```
- DONO_ID com modo_dono = "silencioso"
- user_id == dono_id (é o dono)
```

#### Dados de Entrada

```python
governanca = {
    "modo_dono": "silencioso",
    ...
}

mensagem = "Agende corte amanhã"
```

#### Passos

```
1. Configurar Governanca com modo_dono = silencioso
2. Enviar operação como dono
3. Verificar bloqueio
```

#### Resultado Esperado

```python
{
    "bloqueado": True,
    "motivo": "MEC-04-DONO-SILENCIOSO",
    "resposta": "Modo silencioso ativado"
}
```

#### Critério de Aprovação

- ✅ Bloqueado
- ✅ Retorna "Modo silencioso"
- ✅ Sem resposta IA

#### Risco de Bloqueio

✅ BAIXO — É a intenção

---

### G4.03: Dono Silencioso Envia Cancelamento

**ID:** G4.03  
**Nome:** Silencioso permite cancelamento  
**Classificação:** Crítica (CA-01 + A-08)  
**Tempo Estimado:** 1m  

#### Pré-condições

```
- DONO_ID em modo_dono = "silencioso"
- Com agendamento anterior
```

#### Dados de Entrada

```python
governanca = {
    "modo_dono": "silencioso",
    ...
}

mensagem = "Cancelar meu horário"
```

#### Passos

```
1. Configurar Governanca silencioso
2. Enviar cancelamento
3. Verificar processamento
```

#### Resultado Esperado

```
1. Cancelamento processado
2. Agendamento cancelado
3. Sem bloqueio
```

#### Critério de Aprovação

- ✅ Cancelamento processado
- ✅ Agendamento cancelado
- ✅ Não bloqueado (A-08 vence modo)

#### Risco de Bloqueio

🔴 CRÍTICO — Cancelamento é direito

---

### G4.04: Dono Admin Executa Comando Admin

**ID:** G4.04  
**Nome:** Admin processa comando admin  
**Classificação:** Crítica (CA-04)  
**Tempo Estimado:** 30s  

#### Pré-condições

```
- DONO_ID com modo_dono = "admin"
```

#### Dados de Entrada

```python
governanca = {
    "modo_dono": "admin",
    ...
}

comando = "/pausar"
```

#### Passos

```
1. Configurar Governanca admin
2. Enviar comando admin
3. Verificar execução
```

#### Resultado Esperado

```
1. Comando executado
2. Governanca atualizado
3. AuditoriaGovernanca criado
```

#### Critério de Aprovação

- ✅ Comando executado
- ✅ Modo admin permite comandos
- ✅ Auditoria registrada

#### Risco de Bloqueio

✅ BAIXO — Comandos são permitidos

---

### G4.05: Dono Admin Envia Agendamento Comum

**ID:** G4.05  
**Nome:** Admin bloqueia operação comum  
**Classificação:** Crítica (CA-04)  
**Tempo Estimado:** 30s  

#### Pré-condições

```
- DONO_ID com modo_dono = "admin"
```

#### Dados de Entrada

```python
governanca = {
    "modo_dono": "admin",
    ...
}

mensagem = "Agende corte amanhã"  # NÃO é comando
```

#### Passos

```
1. Configurar Governanca admin
2. Enviar operação comum (não comando)
3. Verificar bloqueio
```

#### Resultado Esperado

```python
{
    "bloqueado": True,
    "motivo": "MEC-04-DONO-ADMIN",
    "resposta": "Modo admin - apenas comandos"
}
```

#### Critério de Aprovação

- ✅ Bloqueado (não é comando admin)
- ✅ Sem resposta IA

#### Risco de Bloqueio

✅ BAIXO — É a intenção (admin mode)

---

## GRUPO G5 — PERSISTÊNCIA

### G5.01: responder_automaticamente Persiste Reload

**ID:** G5.01  
**Nome:** Pausa sobrevive reload de sessão  
**Classificação:** Crítica (CA-07)  
**Tempo Estimado:** 1m  

#### Pré-condições

```
- ACTOR_ID com responder_automaticamente = false
- Salvo em Governanca/{actor_id}
```

#### Dados de Entrada

```python
governanca_antes = {
    "responder_automaticamente": False,
    "_tenant_id_guard": TENANT_ID,
    ...
}

# Reload de sessão (novo principal_router call)
```

#### Passos

```
1. Salvar Governanca com pausa
2. Simular nova sessão (nova chamada principal_router)
3. Carregar Governanca
4. Verificar que persiste
```

#### Resultado Esperado

```
1. Governanca carregado corretamente
2. responder_automaticamente = false
3. Pausa continua aplicada
```

#### Critério de Aprovação

- ✅ Governanca carregado em nova sessão
- ✅ responder_automaticamente = false persiste
- ✅ Próxima mensagem é bloqueada

#### Risco de Bloqueio

🔴 CRÍTICO — Se não persistir, pausa desaparece

---

### G5.02: modo_dono Persiste Reload

**ID:** G5.02  
**Nome:** Modo dono sobrevive reload  
**Classificação:** Crítica (CA-07)  
**Tempo Estimado:** 1m  

#### Pré-condições

```
- DONO_ID com modo_dono = "silencioso"
- Salvo em Governanca/{dono_id}
```

#### Dados de Entrada

```python
governanca_antes = {
    "modo_dono": "silencioso",
    "_tenant_id_guard": TENANT_ID,
    ...
}

# Reload de sessão
```

#### Passos

```
1. Salvar Governanca com modo_dono = silencioso
2. Simular nova sessão
3. Carregar Governanca
4. Verificar que persiste
```

#### Resultado Esperado

```
1. Governanca carregado
2. modo_dono = "silencioso" persiste
3. Modo continua aplicado
```

#### Critério de Aprovação

- ✅ Governanca carregado
- ✅ modo_dono persiste
- ✅ Bloqueios aplicados

#### Risco de Bloqueio

🔴 CRÍTICO — Se não persistir, modo desaparece

---

### G5.03: Auditoria Criada em /pausar

**ID:** G5.03  
**Nome:** Auditoria registra /pausar  
**Classificação:** Crítica (CA-06)  
**Tempo Estimado:** 1m  

#### Pré-condições

```
- ACTOR_ID sem auditoria anterior
- Governanca antes: responder_automaticamente = true
```

#### Dados de Entrada

```python
governanca_antes = {
    "responder_automaticamente": True,
    ...
}

comando = "/pausar"
```

#### Passos

```
1. Carregar Governanca antes
2. Executar /pausar
3. Verificar Governanca depois
4. Verificar AuditoriaGovernanca criado
```

#### Resultado Esperado

```
1. Governanca.responder_automaticamente = false
2. AuditoriaGovernanca documento criado com:
   - comando: "/pausar"
   - campo_alterado: "responder_automaticamente"
   - valor_anterior: true
   - valor_novo: false
   - timestamp: now
   - actor_id_afetado: ACTOR_ID
```

#### Critério de Aprovação

- ✅ Governanca atualizado
- ✅ AuditoriaGovernanca criado
- ✅ Todos os campos preenchidos
- ✅ _tenant_id_guard = TENANT_ID

#### Risco de Bloqueio

🔴 CRÍTICO — Auditoria é obrigatória

---

### G5.04: Auditoria Criada em /retomar

**ID:** G5.04  
**Nome:** Auditoria registra /retomar  
**Classificação:** Crítica (CA-06)  
**Tempo Estimado:** 1m  

#### Pré-condições

```
- ACTOR_ID com responder_automaticamente = false
- De teste anterior (G5.03)
```

#### Dados de Entrada

```python
governanca_antes = {
    "responder_automaticamente": False,
    ...
}

comando = "/retomar"
```

#### Passos

```
1. Carregar Governanca antes (pausado)
2. Executar /retomar
3. Verificar Governanca depois
4. Verificar AuditoriaGovernanca criado
```

#### Resultado Esperado

```
1. Governanca.responder_automaticamente = true
2. AuditoriaGovernanca documento criado com:
   - comando: "/retomar"
   - campo_alterado: "responder_automaticamente"
   - valor_anterior: false
   - valor_novo: true
```

#### Critério de Aprovação

- ✅ Governanca atualizado
- ✅ AuditoriaGovernanca criado
- ✅ Todos os campos preenchidos

#### Risco de Bloqueio

🔴 CRÍTICO — Auditoria é obrigatória

---

## GRUPO G6 — MULTI-TENANT

### G6.01: Pausa em Tenant A Não Afeta Tenant B

**ID:** G6.01  
**Nome:** Isolamento multi-tenant pausa  
**Classificação:** Alta (CA-07)  
**Tempo Estimado:** 2m  

#### Pré-condições

```
- Dois tenants diferentes: TENANT_A, TENANT_B
- ACTOR_ID_A pausado em TENANT_A
- ACTOR_ID_B em TENANT_B
```

#### Dados de Entrada

```python
# Tenant A
governanca_a = {
    "responder_automaticamente": False,
    "_tenant_id_guard": TENANT_A,
    ...
}

# Tenant B
governanca_b = {
    "responder_automaticamente": True,
    "_tenant_id_guard": TENANT_B,
    ...
}

mensagem = "Agende corte"
```

#### Passos

```
1. Pausar ACTOR_ID em TENANT_A
2. Enviar agendamento de ACTOR_ID_A → deve bloquear
3. Enviar agendamento de ACTOR_ID_B em TENANT_B → deve permitir
```

#### Resultado Esperado

```
1. ACTOR_ID_A: Bloqueado (pausado)
2. ACTOR_ID_B: Permitido (não pausado)
```

#### Critério de Aprovação

- ✅ TENANT_A isolado de TENANT_B
- ✅ ACTOR_ID_A bloqueado
- ✅ ACTOR_ID_B permitido
- ✅ _tenant_id_guard validado

#### Risco de Bloqueio

🔴 CRÍTICO — Isolamento multi-tenant

---

### G6.02: Modo Dono em Tenant A Não Afeta Tenant B

**ID:** G6.02  
**Nome:** Isolamento multi-tenant modo dono  
**Classificação:** Alta (CA-07)  
**Tempo Estimado:** 2m  

#### Pré-condições

```
- Dois tenants diferentes: TENANT_A, TENANT_B
- DONO_A em modo silencioso em TENANT_A
- DONO_B em modo normal em TENANT_B
```

#### Dados de Entrada

```python
# Tenant A
governanca_a = {
    "modo_dono": "silencioso",
    "_tenant_id_guard": TENANT_A,
    ...
}

# Tenant B
governanca_b = {
    "modo_dono": "normal",
    "_tenant_id_guard": TENANT_B,
    ...
}

mensagem = "Agende"
```

#### Passos

```
1. Configurar DONO_A silencioso em TENANT_A
2. Configurar DONO_B normal em TENANT_B
3. Enviar agendamento de DONO_A → deve bloquear
4. Enviar agendamento de DONO_B → deve permitir
```

#### Resultado Esperado

```
1. DONO_A: Bloqueado (silencioso)
2. DONO_B: Permitido (normal)
```

#### Critério de Aprovação

- ✅ TENANT_A isolado de TENANT_B
- ✅ Governanca de A não afeta B
- ✅ _tenant_id_guard validado em ambos

#### Risco de Bloqueio

🔴 CRÍTICO — Isolamento multi-tenant

---

## GRUPO G7 — REGRESSÃO

### G7.01: P1 E2E Identidade

**ID:** G7.01  
**Nome:** Regressão P1 E2E Identidade  
**Classificação:** Crítica (CA-08)  
**Tempo Estimado:** 2m  

#### Pré-condições

```
- Baseline P1 E2E está PASS
- Sem Governanca ativa
```

#### Dados de Entrada

```python
# Nenhuma Governanca criada
# Teste executado como baseline
```

#### Passos

```
1. Executar: pytest tests/p1_e2e_onboarding_dono.py -v
2. Executar: pytest tests/p1_e2e_identificacao_cliente.py -v
3. Verificar 100% PASS
```

#### Resultado Esperado

```
P1 E2E Identidade: 100% PASS (antes e depois)
```

#### Critério de Aprovação

- ✅ Todos testes PASS
- ✅ Sem mudança de resultado
- ✅ Comportamento idêntico a baseline

#### Risco de Bloqueio

🔴 CRÍTICO — Regressão quebra Sprint 1

---

### G7.02: P1 E2E Operacional

**ID:** G7.02  
**Nome:** Regressão P1 E2E Operacional  
**Classificação:** Crítica (CA-08)  
**Tempo Estimado:** 3m  

#### Pré-condições

```
- Baseline P1 E2E está PASS
- Sem Governanca ativa
```

#### Dados de Entrada

```python
# Nenhuma Governanca criada
```

#### Passos

```
1. Executar: pytest tests/p1_e2e_agendamento_novo.py -v
2. Executar: pytest tests/p1_e2e_confirmacao.py -v
3. Executar: pytest tests/p1_e2e_cancelamento.py -v
4. Verificar 100% PASS
```

#### Resultado Esperado

```
P1 E2E Operacional: 100% PASS
```

#### Critério de Aprovação

- ✅ Agendamento novo PASS
- ✅ Confirmação PASS
- ✅ Cancelamento PASS
- ✅ 100% de cobertura

#### Risco de Bloqueio

🔴 CRÍTICO — Regressão quebra Sprint 1

---

### G7.03: P1 E2E Individual

**ID:** G7.03  
**Nome:** Regressão P1 E2E Individual  
**Classificação:** Crítica (CA-08)  
**Tempo Estimado:** 2m  

#### Pré-condições

```
- Baseline P1 E2E está PASS
- Sem Governanca ativa
```

#### Dados de Entrada

```python
# Nenhuma Governanca criada
```

#### Passos

```
1. Executar: pytest tests/p1_e2e_*.py -v
2. Contar PASS vs FAIL
3. Comparar com baseline (42/42)
```

#### Resultado Esperado

```
P1 E2E: 42/42 PASS
```

#### Critério de Aprovação

- ✅ 42/42 PASS
- ✅ Nenhuma regressão
- ✅ Comportamento idêntico

#### Risco de Bloqueio

🔴 CRÍTICO — CA-08 obrigatória

---

### G7.04: P0 Regressão Completa

**ID:** G7.04  
**Nome:** Regressão P0 174 testes  
**Classificação:** Crítica (CA-08)  
**Tempo Estimado:** 10m  

#### Pré-condições

```
- Baseline P0 está 174/174 PASS
- Sem Governanca ativa
```

#### Dados de Entrada

```python
# Nenhuma Governanca criada
```

#### Passos

```
1. Executar: pytest tests/p0_*.py -v --tb=short
2. Contar PASS vs FAIL
3. Comparar com baseline (174/174)
4. Gerar relatório
```

#### Resultado Esperado

```
P0: 174/174 PASS
Nenhuma regressão
```

#### Critério de Aprovação

- ✅ 174/174 PASS
- ✅ Zero regressões
- ✅ Baseline mantido

#### Risco de Bloqueio

🔴 CRÍTICO — CA-08 obrigatória

---

## ORDEM DE EXECUÇÃO

### Fase 1: Setup (Sequencial)

```
1. Setup fixture compartilhada
2. Criar dois tenants de teste
3. Carregar dados
```

### Fase 2: MEC-03 (Sequencial)

```
G1.01 → G1.02 → G1.03 → G1.04
```

### Fase 3: Whitelist (Sequencial)

```
G2.01 → G2.02 → G2.03 → G2.04 → G2.05
```

### Fase 4: Fluxo Ativo (Parallelizável)

```
G3.01 ┐
G3.02 ├─ Parallelizar (independentes)
G3.03 ├─
G3.04 ┘
```

### Fase 5: MEC-04 (Sequencial)

```
G4.01 → G4.02 → G4.03 → G4.04 → G4.05
```

### Fase 6: Persistência (Sequencial)

```
G5.01 → G5.02 → G5.03 → G5.04
```

### Fase 7: Multi-tenant (Parallelizável)

```
G6.01 ┐
G6.02 ┘ Parallelizar (mesmo setup)
```

### Fase 8: Regressão (Sequencial)

```
G7.01 → G7.02 → G7.03 → G7.04
```

---

## CRITÉRIOS DE APROVAÇÃO GLOBAIS

### Sprint 1 Passou Se:

```
✅ G1: 100% PASS (MEC-03 funciona)
✅ G2: 100% PASS (Whitelist protege)
✅ G3: 100% PASS (Fluxo ativo preservado)
✅ G4: 100% PASS (MEC-04 funciona)
✅ G5: 100% PASS (Persistência funciona)
✅ G6: 100% PASS (Multi-tenant isolado)
✅ G7: 100% PASS (Baseline mantido)

TOTAL: 28/28 PASS
```

### Sprint 1 Bloqueada Se:

```
❌ Qualquer teste G7 falhar (Regressão)
❌ G5 falhar (Persistência)
❌ G6 falhar (Multi-tenant)
❌ Menos de 100% PASS em qualquer grupo
```

---

## CONFIGURAÇÃO DE AMBIENTE

### Variáveis de Teste

```bash
export TENANT_ID="audit_cenario_05_gpt"
export ACTOR_ID="whatsapp:5511999005"
export DONO_ID="whatsapp:5511888888"
export FIRESTORE_EMULATOR_HOST="localhost:8080"
export OPENAI_API_KEY="${OPENAI_API_KEY}"  # Para testes com GPT
```

### Dados de Teste

```python
# Agendamentos pré-criados
agendamentos_base = {
    "2026-06-24T15:00:00Z": {
        "profissional": "Bruna",
        "cliente": ACTOR_ID,
        "servico": "corte"
    }
}

# Profissionais
profissionais = [
    {"nome": "Bruna", "disponibilidade": "08:00-18:00"},
    {"nome": "Maria", "disponibilidade": "10:00-20:00"},
    {"nome": "Ana", "disponibilidade": "12:00-22:00"}
]
```

---

## TEMPO ESTIMADO TOTAL

```
Fase 1 (Setup):           5m
Fase 2 (G1):             2m
Fase 3 (G2):             3m
Fase 4 (G3):             3m (parallelizável → 1m)
Fase 5 (G4):             2m
Fase 6 (G5):             4m
Fase 7 (G6):             2m (parallelizável → 1m)
Fase 8 (G7):            15m

Sequencial:             36m
Parallelizado:          28m
```

---

## PARECER FINAL

### Plano de Testes Validado

**Status:** ✅ PRONTO PARA IMPLEMENTAÇÃO

**Cobertura:**
- ✅ MEC-03 (4 testes)
- ✅ MEC-04 (5 testes)
- ✅ Whitelist (5 testes)
- ✅ Fluxo ativo (4 testes)
- ✅ Persistência (4 testes)
- ✅ Multi-tenant (2 testes)
- ✅ Regressão (4 testes)

**Total:** 28 testes especificados

**Tempo:** ~30 minutos de execução

**Risco:** Baixo (testes simples e isolados)

---

**Plano:** SEG-04C  
**Status:** ✅ Especificação Completa (Sem Implementação)

**⏹️ PARAR AQUI — Sem código, sem testes, sem patch.**
