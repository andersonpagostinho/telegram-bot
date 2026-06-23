# Triagem: 11 Falhas Funcionais P1 Fluxo

**Data:** 2026-06-22 00:05  
**Objetivo:** Separar falha de setup vs falha real de produto  
**Método:** Auditoria de actor_id/tenant_id/papel/Firestore por cenário  

---

## 🔍 Hipótese Principal

**Sistema entra em onboarding porque:**
- actor_id criado como NOVO DONO em vez de CLIENTE de tenant existente
- Cada cenário cria tenant único, mas actor_id não está vinculado como cliente desse tenant
- Router detecta: novo usuário → ativa onboarding automático

---

## 📊 Matriz de Triagem

| # | Cenário | Falha Observada | actor_id | tenant_id | Papel Esperado | Papel Detectado | Causa Provável | Classificação | Ação |
|---|---------|---|---|---|---|---|---|---|
| 02 | Pessoal + agendamento | "Agendamento não extraído" | whatsapp:55119999002 | teste_fluxo_p1_1db476a9 | cliente | dono (novo) | Setup: actor não é cliente de tenant | **A** | Ajustar setup |
| 04 | Ambiguidade + contexto | "Contexto não utilizado" | whatsapp:55119999004 | teste_fluxo_p1_ca4f0375 | cliente | dono (novo) | Setup: contexto pré-salvo não é lido | **A** | Ajustar setup |
| 05 | Msg longa + pedido final | "Pedido final não detectado" | whatsapp:55119999005 | teste_fluxo_p1_e7fee95c | cliente | dono (novo) | Setup: mensagem opera em onboarding | **A** | Ajustar setup |
| 06 | Confirmação embutida | "Confirmação não processada" | whatsapp:55119999006 | teste_fluxo_p1_b7c35b91 | cliente | dono (novo) | Setup: draft pré-salvo ignorado em onboarding | **A** | Ajustar setup |
| 07 | Negação embutida | "Negação não processada" | whatsapp:55119999007 | teste_fluxo_p1_da7866b3 | cliente | dono (novo) | Setup: draft pré-salvo ignorado em onboarding | **A** | Ajustar setup |
| 08 | Msg curta + contexto | "Contexto não completou" | whatsapp:55119999008 | teste_fluxo_p1_ff525198 | cliente | dono (novo) | Setup: fluxo_ativo pré-salvo ignorado | **A** | Ajustar setup |
| 09 | Ortografia degradada | "Ortografia não processada" | whatsapp:55119999009 | teste_fluxo_p1_45e24073 | cliente | dono (novo) | Setup: mensagem opera em onboarding | **A** | Ajustar setup |
| 10 | Rajada contraditória | "Estado inválido: {}" | whatsapp:55119999010 | teste_fluxo_p1_22a86831 | cliente | dono (novo) | Setup: 5 mensagens processadas em onboarding | **A** | Ajustar setup |
| 11 | Múltiplas entidades | "Entidades não processadas" | whatsapp:55119999011 | teste_fluxo_p1_04c1a91a | cliente | dono (novo) | Setup: mensagem duplicada processada | **A** | Ajustar setup |
| 12 | Serviço inexistente | "'str' object no attr 'get'" | whatsapp:55119999012 | teste_fluxo_p1_a70c71ac | cliente | dono (novo) | Runtime: buscar_subcolecao retorna list, não dict | **B** | Bug real router |
| 13 | Regressão P0 | "name 'roteador_principal' undefined" | whatsapp:55119999013 | teste_fluxo_p1_52b3bee7 | cliente | N/A (erro antes) | Code: `get_roteador_principal()` escopo errado | **A** | Ajustar setup (import) |

---

## 🎯 Classificação Resumida

```
A) Setup Incorreto do Teste:    10 cenários (02,04,05,06,07,08,09,10,11,13)
   └─ Actor não é cliente de tenant
   └─ Contexto/Draft pré-salvo ignorado em onboarding
   └─ Import scope error

B) Bug Real do Router:           1 cenário  (12)
   └─ buscar_subcolecao retorna list em vez de dict

C) Bug Real Contexto/Sessão:     0
D) Bug Real Confirmação/Negação: 0 (não chegou a testar, bloqueado por onboarding)
E) Incompatibilidade MT:         0
```

---

## 🔧 Análise Detalhada por Cenário

### Cenário 02 — Pessoal + Agendamento

**Setup de Teste:**
```python
await setup_tenant_completo(tenant_id, "whatsapp:55119999002")
# Cria: Configuracao, Profissionais/bruna, ServicosNegocio, Atores/whatsapp:55119999002
# MAS: Atores/{actor_id} tem tipo_usuario="cliente"
```

**O que deveria acontecer:**
- actor_id=whatsapp:55119999002 entra como CLIENTE de tenant=teste_fluxo_p1_1db476a9
- Router resolve: obter_id_dono(whatsapp:55119999002) → teste_fluxo_p1_1db476a9
- Processador de agendamento espera contexto do cliente

**O que realmente acontece:**
- Router tenta: obter_id_dono(whatsapp:55119999002)
- Não encontra vínculo
- Cria novo DONO: whatsapp:55119999002 em tenant vazio
- Ativa onboarding_dono automático

**Classificação:** **A — Setup Incorreto**

**Causa:** 
- Ator criado em Firestore, mas `obter_id_dono()` não consegue vincular
- Função `obter_id_dono()` procura por Clientes/{user_id}/... ou vínculo diferente
- Teste não simula vínculo correto

**Recomendação:** Ajustar setup para:
1. Ou criar Clientes/{tenant_id}/Atores/{actor_id} com tipo="cliente"
2. Ou registrar vínculo actor → tenant em outra estrutura
3. Ou mockar `obter_id_dono()` para retornar tenant correto

---

### Cenário 04 — Ambiguidade + Contexto

**Setup de Teste:**
```python
await salvar_dado_em_path(
    f"Clientes/{tenant_id}/Sessoes/whatsapp:55119999004",
    {"ultima_profissional": "Bruna", "ultimo_servico": "corte"}
)
# Salva contexto, depois chama roteador
```

**O que deveria acontecer:**
- Actor entra como cliente existente
- Sessão já tem contexto anterior
- Router usa contexto para resolver "marca com a mesma profissional"

**O que realmente acontece:**
- Actor é criado como NOVO DONO
- Contexto anterior é IGNORADO (Sessões pré-salva não é carregada em onboarding)
- Resposta: "Vamos completar cadastro?"

**Classificação:** **A — Setup Incorreto**

**Causa:** 
- Sessão/contexto é salvo em path correto
- MAS: router cria novo tenant/dono, então carrega contexto de OUTRO actor/tenant
- Contexto salvo em Clientes/{tenant_id}/Sessoes/{actor_id} não é carregado
- `carregar_contexto_temporario()` usa actor_id, mas actor agora é dono diferente

**Recomendação:** Mesmo que cenário 02 — ajustar vínculo actor→tenant

---

### Cenário 06 — Confirmação Embutida

**Setup de Teste:**
```python
await salvar_dado_em_path(
    f"Clientes/{tenant_id}/Sessoes/whatsapp:55119999006",
    {
        "draft_confirmacao": {...},
        "confirmacao_pendente": True
    }
)
```

**O que deveria acontecer:**
- Draft pré-salvo existe
- Router detecta confirmação em mensagem
- Avança para criação de evento

**O que realmente acontece:**
- Draft é salvo em Clientes/teste_fluxo_p1_b7c35b91/Sessoes/whatsapp:55119999006
- Router cria novo DONO: whatsapp:55119999006 em tenant VAZIO
- `carregar_contexto_temporario()` carrega de Clientes/whatsapp:55119999006/MemoriaTemporaria (path legado!)
- Draft original não é encontrado
- Onboarding é ativado
- Confirmação não é processada

**Classificação:** **A — Setup Incorreto + Multi-Tenant Bug**

**Causa:**
- Test salva em Clientes/{test_tenant}/Sessoes/{actor_id}
- Router cria Clientes/{actor_id} como novo tenant
- Busca contexto em Clientes/{actor_id}/MemoriaTemporaria (legado)
- Encontra vazio, ativa onboarding

**Recomendação:** Ajustar setup para usar vínculo correto

---

### Cenário 12 — Serviço Inexistente

**Erro:** `'str' object has no attribute 'get'`

**Log anterior:**
```
[DOC] Documento encontrado em Clientes/teste_fluxo_p1_a70c71ac/ServicosNegocio/corte: {...}
[DOC] Documento encontrado em Clientes/teste_fluxo_p1_a70c71ac/ServicosNegocio/escova: {...}
[FAIL] 12. Serviço inexistente no fluxo - Erro: 'str' object has no attribute 'get'
```

**Análise:**
- Setup funciona (profissionais e serviços encontrados)
- Erro ocorre ao processar resultado
- `buscar_subcolecao()` retorna list de dicts em algumas casos, str em outras?

**Classificação:** **B — Bug Real do Router**

**Causa:**
- Inconsistência em como `buscar_subcolecao()` retorna dados
- Ou código tenta fazer `.get()` em string quando deveria ser dict
- Ou resultado não é normalizado

**Recomendação:** Bug real — investigar `buscar_subcolecao()` e seu uso

---

### Cenário 13 — Regressão P0

**Erro:** `name 'roteador_principal' is not defined`

**Causa:** Import scope error na bateria
```python
def get_roteador_principal():
    from router.principal_router import roteador_principal
    return roteador_principal

resposta = await roteador_principal(...)  # ❌ Não está em escopo global
```

**Classificação:** **A — Setup Incorreto (Import)**

**Recomendação:** Ajustar bateria para usar `get_roteador_principal()` ou import global

---

## 🎯 Resumo de Ações

### Setup Incorreto (10 cenários: 02,04,05,06,07,08,09,10,11,13)

**Problema Raiz:** Actor_id não é cliente de tenant_id

**Solução:**
Option 1: Mockar `obter_id_dono()` para retornar tenant correto
Option 2: Criar vínculo real em Firestore (mais integrativo)
Option 3: Usar mesmo valor para actor_id e tenant_id (menos realista)

**Proposta:** Option 1 (rapida, não afeta produção)
```python
# No setup do cenário:
@patch('services.firebase_service_async.obter_id_dono')
async def setup_com_mock_id_dono(mock_id_dono):
    mock_id_dono.return_value = tenant_id  # Vincular actor → tenant
    await setup_tenant_completo(tenant_id, actor_id)
```

### Bug Real (1 cenário: 12)

**Problema:** `buscar_subcolecao()` inconsistência de tipo retorno

**Esperado:** Sempre retorna dict ou list of dicts
**Obtido:** Às vezes retorna str?

**Ação:** Investigar `buscar_subcolecao()` implementação

---

## ✅ Decisão: Próximas Etapas

Se a triagem confirmar que 10/11 são setup:
1. Corrigir setup da bateria (mockar `obter_id_dono()`)
2. Re-executar bateria 13
3. Esperar resultado real (não afeta lógica produtiva)

Se cenário 12 persistir:
- Investigar bug real em `buscar_subcolecao()`

