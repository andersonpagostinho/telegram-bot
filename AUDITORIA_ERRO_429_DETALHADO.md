# 🔴 AUDITORIA: Diagnóstico Detalhado de Erro 429

**Objetivo:** Coletar informações precisas sobre qual tipo de rate limit está ocorrendo
**Data:** 2026-06-02
**Método:** Logs estruturados de erro sem alterar lógica

---

## O que Está Sendo Capturado

### Logs adicionados em 2 locais:

1. **Chamada 1 (linha ~1056)** — except ao chamar OpenAI
2. **Geral (linha ~3137)** — except que pega erros de Chamada 2 e outros

### Informações coletadas por erro:

```
[OPENAI_ERROR_TYPE]     → Tipo da exceção (RateLimitError, APIError, etc)
[OPENAI_ERROR_REPR]     → Representação completa do erro
[OPENAI_ERROR_STATUS]   → Código HTTP (429, 401, 500, etc)
[OPENAI_ERROR_BODY]     → Corpo completo da resposta de erro
[OPENAI_ERROR_CODE]     → Código de erro da API OpenAI
[OPENAI_ERROR_MESSAGE]  → Mensagem de erro estruturada
```

---

## Códigos de Rate Limit Possíveis

### OpenAI Rate Limit Types:

```
insufficient_quota
  → Créditos/saldo esgotado
  → HTTP 401 ou 403
  → Billing problem

rate_limit_exceeded
  → Requests per minute (RPM) atingido
  → Tokens per minute (TPM) atingido
  → HTTP 429
  → Temporary, pode recuperar com retry

project_rate_limit_exceeded
  → Limite específico do projeto
  → HTTP 429
  → Org-level limit

billing_hard_limit_exceeded
  → Limite de spending atingido
  → HTTP 429
  → Account issue

tokens_per_min_limit_exceeded
  → TPM limit específico
  → HTTP 429
  → Model-specific

requests_per_min_limit_exceeded
  → RPM limit específico
  → HTTP 429
  → Model-specific
```

---

## Estrutura Esperada de Logs (se 429 ocorrer)

```
❌ Erro ao chamar OpenAI: RateLimitError: Error code: 429
🧪 [OPENAI_ERROR_TYPE] RateLimitError
🧪 [OPENAI_ERROR_REPR] RateLimitError('...')
🧪 [OPENAI_ERROR_STATUS] 429
🧪 [OPENAI_ERROR_BODY] {
  "error": {
    "message": "Rate limit exceeded for model `gpt-4o` in organization `org-xxx` on tokens per min. Limit: 2M, Used: 2.04M, Requested: 1.3k",
    "type": "tokens_per_min_limit_exceeded",
    "param": null,
    "code": "rate_limit_exceeded"
  }
}
🧪 [OPENAI_ERROR_CODE] rate_limit_exceeded
```

---

## Interpretação dos Possíveis Resultados

### Cenário A: TPM Limit Exceeded
```
"tokens_per_min_limit_exceeded"
  ↓
Significado: Enviou muitos tokens em 1 minuto
Causa: 2 chamadas GPT em rápida sucessão × múltiplos usuários
Impacto: Estrutural, problema real
Solução: Reduzir duplic…ção ou usar modelo mais leve
```

### Cenário B: RPM Limit Exceeded
```
"requests_per_min_limit_exceeded"
  ↓
Significado: Mais de N requisições por minuto
Causa: Muitos usuários agendando simultaneamente
Impacto: Concorrência, problema real
Solução: Adicionar debounce ou queue
```

### Cenário C: Insufficient Quota
```
"insufficient_quota"
  ↓
Significado: Sem saldo/créditos
Causa: Billing, não técnico
Impacto: Operacional
Solução: Adicionar créditos na conta OpenAI
```

### Cenário D: Billing Hard Limit
```
"billing_hard_limit_exceeded"
  ↓
Significado: Spending limit atingido
Causa: Billing, não técnico
Impacto: Operacional
Solução: Ajustar limite de spending
```

---

## Hipóteses a Validar

### H1: Chamadas dobradas (estrutural)
```
Se vemos 429 + [PROMPT_SIZE] similar em Chamada 1 e 2:
→ Duplicação confirmada
→ Causa técnica, pode ser otimizada
```

### H2: Tráfego pico (concorrência)
```
Se vemos 429 + RPM_LIMIT:
→ Múltiplos usuários simultâneos
→ Pode ser mitigado com debounce
```

### H3: Modelo pesado (custo)
```
Se vemos 429 + TPM_LIMIT:
→ gpt-4o consome muito
→ Fallback para gpt-4-turbo possível
```

### H4: Problema não técnico (operacional)
```
Se vemos insufficient_quota ou billing:
→ Não há bug de código
→ Resolver com adm OpenAI
```

---

## Checklist de Coleta

Se 429 ocorrer, verificar:

- [ ] `[OPENAI_ERROR_TYPE]` foi capturado?
- [ ] `[OPENAI_ERROR_STATUS]` é 429?
- [ ] `[OPENAI_ERROR_BODY]` contém "type"?
- [ ] Qual "type" específico aparece?
  - [ ] `insufficient_quota`
  - [ ] `rate_limit_exceeded`
  - [ ] `tokens_per_min_limit_exceeded`
  - [ ] `requests_per_min_limit_exceeded`
  - [ ] `billing_hard_limit_exceeded`
  - [ ] Outro?
- [ ] Mensagem de erro é clara?

---

## Teste Esperado

### Sem 429:
```
[PROMPT_SIZE] chars=4378 msgs=3
[PROMPT_TOKENS_EST] 1095
[resposta do GPT...]
[GPT_ROUTE] CALL_1_RETURN
```

### Com 429 (estrutural):
```
[PROMPT_SIZE] chars=4378 msgs=3
[OPENAI_ERROR_TYPE] RateLimitError
[OPENAI_ERROR_STATUS] 429
[OPENAI_ERROR_BODY] tokens_per_min_limit_exceeded
```

### Com 429 (operacional):
```
[OPENAI_ERROR_TYPE] AuthenticationError ou similar
[OPENAI_ERROR_STATUS] 401 ou 403
[OPENAI_ERROR_BODY] insufficient_quota
```

---

**Status:** Instrumentação de diagnóstico de erro completa. Pronto para teste.

