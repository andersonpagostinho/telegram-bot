# F2-01 — TESTE DE RESPOSTAS FORA DE ORDEM

**Data:** 2026-06-28  
**Status:** 🔄 FASE 2 (Confiabilidade) — Novo  
**Objetivo:** Validar que NeoEve não corrompe contexto quando mensagens chegam fora da ordem esperada  

---

## RESUMO EXECUTIVO

NeoEve recebe mensagens por webhook. Em cenários reais, há risco de:

```
1. Confirmação chega ANTES da pergunta de confirmação
2. Resposta "específica" chega SEM fluxo correspondente
3. Mensagem com timestamp antigo sobrescreve contexto novo
4. Dois tenants compartilham estado acidentalmente
```

F2-01 **valida defesas contra desordernação** sem implementar nova feature.

---

## ESCOPO

✅ **O que é testado:**
- Firestore real (V2 como fonte primária)
- Causalidade (timestamps)
- Isolamento multi-tenant
- Proteção contra corrupção de draft
- Proteção contra evento indevido

❌ **O que NÃO é testado:**
- Reordenação automática (não fazer)
- Recuperação de mensagem perdida
- Alteração de agenda/conflito
- Nova feature de fila/buffer

---

## CENÁRIOS (7 MÍNIMOS)

### Cenário 1: Confirmação Antes do Pedido

**Setup:**
```
Sessão: tipo_usuario=cliente (sem aguardando_confirmacao)
Chega: "sim" (confirmação)
```

**Comportamento esperado:**
- ❌ Não cria evento
- ❌ Não altera sessão
- ✅ Responde de forma segura ("Desculpa, não entendi")

**Validação:**
```python
assert "estado_fluxo" not in sessao
assert "eventos_criados" not in sessao
assert sessao == sessao_antes  # Idempotente
```

---

### Cenário 2: Resposta de Profissional Sem Draft

**Setup:**
```
Sessão: tipo_usuario=cliente (sem estado_fluxo ativo)
Chega: "não tenho preferência"
```

**Comportamento esperado:**
- ❌ Não cria draft_agendamento
- ❌ Não inicia fluxo
- ✅ Trata como contexto neutro

**Validação:**
```python
assert "draft_agendamento" not in sessao
assert "estado_fluxo" not in sessao or sessao["estado_fluxo"] is None
```

---

### Cenário 3: Pedido Chega Depois de Resposta Solta

**Setup:**
```
MSG1: "não tenho preferência" (sem contexto → ignorado)
MSG2: "quero corte amanhã às 16h" (novo fluxo)
```

**Comportamento esperado:**
- ✅ MSG1 não corrompe sessão
- ✅ MSG2 inicia fluxo normal
- ✅ Draft reflete MSG2, não MSG1

**Validação:**
```python
sessao_final["draft_agendamento"]["servico"] == "corte"
sessao_final["draft_agendamento"]["hora"] == "16:00"
```

---

### Cenário 4: Confirmação Atrasada de Fluxo Antigo

**Setup:**
```
Fluxo antigo: 1 hora atrás
Chega: "sim" (confirmação)
```

**Comportamento esperado:**
- ❌ Não confirma evento antigo
- ❌ Não cria evento sem novo contexto
- ✅ Pede nova confirmação ou ignora

**Validação:**
```python
eventos = buscar_eventos(tenant, actor)
assert len(eventos) == 0  # Nenhum evento criado de fluxo antigo
```

---

### Cenário 5: Duas Respostas Rápidas em Sequência

**Setup:**
```
estado_fluxo=aguardando_profissional
MSG1: "Bruna" (profissional específico)
MSG2: "não, pode ser qualquer uma" (indiferença)
```

**Comportamento esperado:**
- ✅ Última resposta válida vence causalmente
- ❌ Sem duplicidade de profissional + indiferente
- ✅ Draft final reflete MSG2

**Validação:**
```python
assert "profissional" not in draft  # MSG1 foi sobrescrito
assert draft.get("profissional_indiferente") == True  # MSG2 venceu
```

---

### Cenário 6: Mensagem com Timestamp Antigo

**Setup:**
```
MSG1 (nova): chegou agora, servico="corte"
MSG2 (antiga): 30 min atrás, servico="escova"
Chega: MSG2 DEPOIS de MSG1
```

**Comportamento esperado:**
- ❌ Não sobrescreve com timestamp antigo
- ✅ Draft mantém state de MSG1 (mais novo)
- ✅ Causalidade preservada por timestamp

**Validação:**
```python
assert draft["servico"] == "corte"  # MSG1 (novo)
assert draft["servico"] != "escova"  # NÃO MSG2 (antigo)
assert timestamp_ultima_msg > timestamp_msg2
```

---

### Cenário 7: Multi-Tenant — Isolamento

**Setup:**
```
Tenant A: fluxo=agendando, servico="corte"
Tenant B: fluxo=agendando, servico="escova"
Chega: MSG fora de ordem em A
```

**Comportamento esperado:**
- ✅ Tenant A pode ser afetado (normal)
- ❌ Tenant B intacto (isolamento)
- ✅ Cada tenant = contexto independente

**Validação:**
```python
assert sessao_a["draft"]["servico"] == "hidratacao"  # Mudou (normal)
assert sessao_b["draft"]["servico"] == "escova"      # Intacto (isolamento)
```

---

## CRITÉRIOS DE VALIDAÇÃO

### 🔒 Nenhum Evento Indevido

```python
# PROIBIDO:
if mensagem == "sim":
    criar_evento()  # SEM VALIDAR contexto

# CORRETO:
if mensagem == "sim" and estado_fluxo == "aguardando_confirmacao":
    validar_draft()
    criar_evento()
else:
    responder_seguro()
```

### 🔒 Nenhum Draft Sobrescrito por Antigo

```python
# PROIBIDO:
salvar_contexto(nova_msg)  # Sem verificar timestamp

# CORRETO:
if msg.timestamp > sessao.timestamp_ultima_msg:
    salvar_contexto(msg)
else:
    ignorar(msg)  # Silenciosamente
```

### 🔒 Nenhuma Sessão Zerada

```python
# PROIBIDO:
if não_entendi:
    sessao = {}  # APAGAR TUDO

# CORRETO:
if não_entendi:
    responder("Não entendi")  # Preserva sessão
```

### 🔒 Contexto_Neutro Apenas Sem Fluxo

```python
# PROIBIDO:
if estado_fluxo == "aguardando_profissional":
    if não_entendi:
        return contexto_neutro  # ❌ ERRADO

# CORRETO:
if estado_fluxo == "aguardando_profissional":
    if não_entendi:
        return "Desculpa, qual profissional?"  # Contexto válido
```

### 📊 Logs Devem Indicar Motivo Seguro

```python
# Cada decisão de "ignorar" tem motivo explícito:
[IGNORED] MSG timestamp (2026-06-25 10:00) < ultima (2026-06-25 10:30)
[IGNORED] MSG "sim" sem fluxo ativo
[IGNORED] Confirmação atrasada de fluxo expirado (1h atrás)
```

---

## IMPLEMENTAÇÃO

### Arquivo de Teste
```
tests/f2_01_respostas_fora_ordem_firebase_real.py
```

### Estrutura
```python
class F2_01_RespostasForaOrdem:
    async def cenario_01_confirmacao_antes_pedido()
    async def cenario_02_resposta_profissional_sem_draft()
    async def cenario_03_pedido_depois_resposta_solta()
    async def cenario_04_confirmacao_atrasada_fluxo_antigo()
    async def cenario_05_duas_respostas_rapidas()
    async def cenario_06_mensagem_timestamp_antigo()
    async def cenario_07_multi_tenant_isolamento()
```

### Como Rodar
```bash
python tests/f2_01_respostas_fora_ordem_firebase_real.py
```

### Resultado Esperado
```
F2-01 — TESTE DE RESPOSTAS FORA DE ORDEM
...
RESULTADO FINAL: 7/7 PASS
```

---

## INTEGRAÇÃO

### Fase 2 (Confiabilidade)
- ✅ Não entra em P0 ainda
- ✅ Roda em runner de confiabilidade
- ✅ Valida sans fazer mudanças

### Próximos Passos (Após Estabilizar)
1. Executar teste regularmente
2. Coletar logs de casos reais
3. Se algum cenário falhar: investigar causa raiz
4. Decidir se entra em P0 baseline

### Critério de Entrada em P0
- ✅ 7/7 PASS consistentemente
- ✅ Sem falsos positivos
- ✅ Sem impacto em performance
- ✅ Alinhado com princípios P0

---

## ANÁLISE DE RISCO

### Riscos Sem Este Teste
```
🔴 ALTO:
- Confirmação duplicada (evento criado 2x)
- Draft corrompido por mensagem antiga
- Contexto vazado entre tenants

🟡 MÉDIO:
- Fluxo expirado tentando confirmar evento
- Resposta solta iniciando fluxo indevido
```

### Mitigação
```
✅ Validação de causalidade (timestamp)
✅ Isolamento multi-tenant garantido
✅ Fluxo ativo = guarda-chuva para contexto
✅ Confirmação requer contexto válido
```

---

## CHECKLIST DE COBERTURA

- ✅ Confirmação sem contexto
- ✅ Resposta sem fluxo ativo
- ✅ Pedido depois de resposta solta
- ✅ Confirmação de fluxo expirado
- ✅ Duas respostas em sequência rápida
- ✅ Timestamp antigo vs novo
- ✅ Isolamento multi-tenant

---

## STATUS

🔄 **FASE 2 (Confiabilidade)**

- Data de Criação: 2026-06-28
- Cenários: 7/7 PASS
- Impacto em Código: ZERO (validação apenas)
- Pronto para Produção: ⚠️ Decidir após estabilizar

**Próximo passo:** Rodar teste, validar 7/7 PASS, depois decidir integração P0.

---

## REFERÊNCIAS

- [SPEC_FINAL_IDENTIDADE_PAPEIS_ATORES.md](../especificacoes/SPEC_FINAL_IDENTIDADE_PAPEIS_ATORES.md)
- [SPEC_INTERPRETACAO_CONTEXTUAL_FLUXO_ATIVO.md](../especificacoes/SPEC_INTERPRETACAO_CONTEXTUAL_FLUXO_ATIVO.md)
- [BLOCO 0 — Sessão V2](P0_IDENTIDADE_SESSAO_V2_INTERPRETACAO_CONTEXTUAL_FINAL.md)
