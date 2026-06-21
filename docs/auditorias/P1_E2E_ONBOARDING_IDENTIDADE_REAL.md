# P1 E2E — ONBOARDING + IDENTIDADE REAL

**Data:** 2026-06-21  
**Status:** 🔄 BATERIA DISPONÍVEL PARA EXECUÇÃO  
**Saída:** tests/resultado_p1_e2e_onboarding_identidade.json  
**Critério:** 15/15 PASS para certificação

---

## 📋 ESCOPO

Validar ponta a ponta fluxo completo de **Identidade por Canal + Onboarding Automático**:

```
dono primeiro acesso
  → onboarding automático
  → cadastro profissional por canal
  → profissional reconhecido
  → cliente automático
  → agendamento
  → confirmação
  → notificação
  → cancelamento/reagendamento
  → multi-tenant
```

---

## 🎯 CENÁRIOS OBRIGATÓRIOS (15 Total)

### CENÁRIO 1: Primeiro acesso do dono

**Entrada:** Dono envia primeira mensagem

**Esperado:**
- actor_id normalizado: `whatsapp:11999999999`
- tipo_usuario = `dono`
- tenant_id criado/resolvido
- onboarding iniciado
- estado_fluxo = `onboarding_dono`
- ✅ **Não cai no fluxo P0 de agendamento**

**Validações:**
- `actor_id_normalizado` ✅
- `ator_criado` ✅
- `tipo_usuario_correto` ✅

---

### CENÁRIO 2: Onboarding mínimo completo

**Entrada:** Dono completa onboarding com dados:
- nome_negocio ✅
- segmento ✅
- endereco ✅
- agenda_padrao ✅
- primeiro_profissional ✅
- canal_primeiro_profissional ✅
- primeiro_servico ✅
- duracao_primeiro_servico ✅

**Esperado:**
- onboarding_status = `completo`
- Configuracao/dados_negocio preenchido
- Profissionais/{profissional} criado
- ServicosNegocio/{servico} criado
- Atores/{actor_id_profissional} criado
- ✅ **Sessoes guarda apenas estado/draft**
- ✅ **Catálogo NÃO é salvo em sessão**

**Validações:**
- `configuracao_preenchida` ✅
- `profissional_criado` ✅
- `servico_criado` ✅
- `ator_profissional_criado` ✅
- `onboarding_status_completo` ✅

---

### CENÁRIO 3: Profissional cadastrado entra em contato

**Entrada:** Carla usa canal cadastrado pelo dono

**Esperado:**
- resolve como tipo_usuario = `profissional`
- profissional_id = `carla`
- ✅ **Não cria cliente duplicado**
- permissões operacionais aplicadas

**Validações:**
- `ator_existe` ✅
- `tipo_usuario_profissional` ✅
- `profissional_id_correto` ✅

---

### CENÁRIO 4: Cliente novo entra em contato

**Esperado:**
- cria Clientes/{tenant_id}/Clientes/{actor_id}
- tipo_usuario = `cliente`
- ✅ **Não vira dono**
- ✅ **Não vira profissional**
- segue fluxo P0 normal

**Validações:**
- `ator_criado` ✅
- `tipo_usuario_cliente` ✅
- `nao_e_dono` ✅
- `nao_e_profissional` ✅
- `cliente_criado` ✅

---

### CENÁRIO 5: Cliente agenda com profissional cadastrado

**Entrada:** Cliente pede serviço cadastrado no onboarding

**Esperado:**
- serviço reconhecido
- profissional reconhecido
- duração correta
- conflito validado
- confirmação pendente criada
- evento criado após confirmação

**Validações:**
- `servico_reconhecido` ✅
- `profissional_reconhecido` ✅
- `duracao_correta` ✅
- `preco_correto` ✅

---

### CENÁRIO 6: Profissional consulta agenda própria

**Esperado:**
- vê apenas eventos dela
- ✅ **Não vê agenda de outro profissional**
- usa tenant_id correto

**Validações:**
- `evento_existe` ✅
- `profissional_correto` ✅
- `usa_tenant_correto` ✅

---

### CENÁRIO 7: Profissional tenta ação de dono

**Entrada:** "Cadastrar profissional Renata"

**Esperado:**
- ✅ **Bloqueado**
- não cria Renata
- ✅ **Não altera Configuracao**
- ✅ **Não altera Profissionais**

**Validações:**
- `profissional_count_nao_mudou` ✅
- `renata_nao_criada` ✅
- `bloqueado_por_permissao` ✅

---

### CENÁRIO 8: Profissional cancela evento próprio

**Esperado:**
- ✅ **Permitido**
- evento correto cancelado
- cancelado_por_tipo = `profissional`
- ✅ **Não cancela evento alheio**

**Validações:**
- `evento_era_profissional` ✅
- `evento_cancelado` ✅
- `cancelado_por_tipo_correto` ✅

---

### CENÁRIO 9: Profissional tenta cancelar evento de outro profissional

**Esperado:**
- ✅ **Bloqueado**
- evento da outra profissional preservado

**Validações:**
- `evento_bruna_existe` ✅
- `status_nao_mudou` ✅
- `ainda_confirmado` ✅
- `bloqueado_por_permissao` ✅

---

### CENÁRIO 10: Dono consulta agenda completa

**Esperado:**
- vê eventos do tenant
- vê eventos de profissionais cadastrados
- ✅ **Não vê eventos de outro tenant**

**Validações:**
- `eventos_encontrados` ✅
- `usa_tenant_correto` ✅
- `nao_vaza_outro_tenant` ✅

---

### CENÁRIO 11: Multi-tenant completo

**Setup:** Criar Tenant A e Tenant B, ambos com profissional "Carla"

**Esperado:**
- ✅ **actor_id/canal resolvido dentro do tenant correto**
- ✅ **agendas isoladas**
- ✅ **clientes isolados**
- ✅ **profissionais isolados**
- ✅ **configurações isoladas**

**Validações:**
- `tenant_a_criado` ✅
- `tenant_b_criado` ✅
- `ator_a_isolado` ✅
- `ator_b_isolado` ✅
- `atores_diferentes` ✅
- `profissionais_diferentes` ✅
- `agendas_isoladas` ✅

---

### CENÁRIO 12: Reinício durante onboarding

**Entrada:** Onboarding iniciado → sessão persistida → recarregar

**Esperado:**
- ✅ **Retoma etapa correta**
- ✅ **Não perde draft**
- ✅ **Não reinicia tenant**
- ✅ **Não cria duplicidade**

**Validações:**
- `sessao_retomada` ✅
- `etapa_preservada` ✅
- `draft_preservado` ✅
- `sem_duplicidade` ✅

---

### CENÁRIO 13: Troca de contexto durante onboarding

**Entrada:** Dono pergunta algo informativo durante onboarding

**Esperado:**
- responde ou ignora conforme regra
- ✅ **Onboarding continua na mesma etapa**
- ✅ **Draft preservado**

**Validações:**
- `estado_fluxo_preservado` ✅
- `draft_preservado` ✅
- `etapa_mesma` ✅

---

### CENÁRIO 14: Cliente não contamina onboarding do dono

**Entrada:** Enquanto dono está em onboarding, cliente novo fala

**Esperado:**
- ✅ **Cliente criado automaticamente**
- ✅ **Sessão do cliente isolada**
- ✅ **Onboarding do dono preservado**

**Validações:**
- `sessao_dono_preservada` ✅
- `estado_dono_correto` ✅
- `sessao_cliente_criada` ✅
- `sessoes_isoladas` ✅

---

### CENÁRIO 15: Regressão P0 após onboarding

**Entrada:** Após onboarding, cliente agenda serviço cadastrado

**Esperado:**
- ✅ **P0 continua funcionando**
- evento criado com dados do catálogo recém-cadastrado
- sem perda de campos
- confirmação funciona

**Validações:**
- `onboarding_completo` ✅
- `profissional_existe` ✅
- `servico_existe` ✅
- `evento_criado` ✅
- `evento_com_dados_corretos` ✅
- `p0_continua_funcionando` ✅

---

## ✅ VALIDAÇÕES OBRIGATÓRIAS

Para cada cenário são registrados:

```
✅ tenant_id
✅ actor_id
✅ tipo_usuario
✅ canal
✅ mensagem
✅ resposta enviada
✅ sessão antes/depois
✅ Configuracao antes/depois
✅ Profissionais antes/depois
✅ ServicosNegocio antes/depois
✅ Atores antes/depois
✅ Clientes antes/depois
✅ Eventos antes/depois
✅ Notificações antes/depois (quando aplicável)
✅ PASS/FAIL
✅ motivo_falha
```

---

## 🎖️ CRITÉRIO DE CERTIFICAÇÃO

**Obrigatório: 15/15 PASS**

Se qualquer cenário falhar → **NÃO CERTIFICADO**

### Garantias Entregues

- ✅ **Nenhum tenant vaza**
- ✅ **Cliente não vira dono**
- ✅ **Cliente não vira profissional**
- ✅ **Profissional não vira cliente duplicado**
- ✅ **Profissional não executa ação de dono**
- ✅ **Onboarding não salva catálogo em sessão**
- ✅ **P0 continua funcionando após onboarding**
- ✅ **Sem UnicodeEncodeError**
- ✅ **Sem escrita em path legado**

---

## 🚀 COMO EXECUTAR

### Pré-requisitos

```bash
# Firestore real deve estar acessível
# Nenhum mock ativado
# Router real deve ser importável
```

### Executar Bateria

```bash
cd "C:\Users\ANDERSON\iCloudDrive\Projeto Mercado Digital\Agente Bot\NeoEve - Empresarial"
python tests/p1_e2e_onboarding_identidade_real.py
```

### Resultado

```
✅ tests/resultado_p1_e2e_onboarding_identidade.json (gerado automaticamente)
📊 Sumário:
   - Total: 15 cenários
   - PASS: X/15
   - FAIL: Y/15
   - Taxa Sucesso: Z%
   - Certificado: [SIM/NÃO]
```

---

## 📊 VALIDAÇÃO FINAL

Após execução:

### 1. P1 E2E ✅
```bash
python tests/p1_e2e_onboarding_identidade_real.py
# Esperado: 15/15 PASS
```

### 2. P1 Identidade Isolado ✅
```bash
python -m pytest tests/runner_p1_identidade_canal_onboarding.py -v
# Esperado: 9/9 PASS
```

### 3. P0 Regressão ✅
```bash
python tests/runner_p0_regressao_completa.py
# Esperado: 174/174 PASS
```

---

## 🔴 IMPORTANTE

**Não alterar produção inicialmente.**

Se algum cenário falhar:
1. ✅ Documentar bug real
2. ✅ **NÃO mascarar como PASS**
3. ✅ Propor patch mínimo
4. ✅ Reexecutar P1 E2E + P0

---

## 📝 RESULTADO ESPERADO

```json
{
  "data": "2026-06-21T...",
  "total_cenarios": 15,
  "pass": 15,
  "fail": 0,
  "taxa_sucesso": "100.0%",
  "certificado": true,
  "cenarios": [
    {
      "numero": 1,
      "nome": "Primeiro acesso do dono",
      "status": "PASS",
      "motivo": "Primeiro acesso do dono validado com sucesso",
      "validacoes": {...}
    },
    ...
  ]
}
```

---

## 🎯 PRÓXIMAS ETAPAS

1. ✅ Executar P1 E2E
2. ✅ Validar todos os 15 cenários
3. ✅ Executar P1 isolado (9/9)
4. ✅ Executar P0 regressão (174/174)
5. ✅ Se tudo PASS → Bateria certificada
6. ✅ Documentar resultados em JSON + Markdown

---

**Bateria P1 E2E:** Pronta para execução  
**Status:** 🟢 DISPONÍVEL  
**Referência:** tests/p1_e2e_onboarding_identidade_real.py  
**Saída:** tests/resultado_p1_e2e_onboarding_identidade.json + este documento
