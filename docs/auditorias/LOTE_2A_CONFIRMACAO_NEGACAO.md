# LOTE 2A — Auditoria: Confirmação e Negação

**Data:** 2026-06-22 00:25  
**Cenários:** 06 (Confirmação), 07 (Negação)  
**Status:** Diagnóstico forense (SEM correções)  

---

## 🔍 CENÁRIO 06 — Confirmação Embutida

### Entrada
```
Mensagem: "Pode deixar. Li tudo. Sim, pode confirmar esse horário. Obrigado!"
Canal: WhatsApp
```

### Estado ANTES da Mensagem (Esperado)
```
confirmacao_pendente: True ✓
draft_confirmacao: {
  'servico': 'corte',
  'profissional': 'Bruna',
  'data': 'amanhã',
  'hora': '14:00'
}
```

**Status:** Draft foi salvo corretamente em Firestore.

---

### Processamento da Mensagem

#### [1] ADMIN Check
```
[ADMIN] entrada | texto='Pode deixar. Li tudo. Sim, pode confirmar esse horário. Obrigado!'
[ADMIN] nenhuma intenção admin detectada ✓
```

#### [2] CLASSIFICADOR CONTEXTO
```
modo_conversa: 'neutro'
confianca: 0
motivo: 'sem_composicao_suficiente'
features: {
  'tem_fluxo_ativo': False        ← Esperado (fluxo dorminhoco)
  'tem_draft': False              ← ❌ PROBLEMA! Draft DEVERIA ser True
  'tem_confirmacao_pendente': False  ← ❌ CRÍTICO! Deveria ser True
  'tem_pergunta': True
  'tem_pedido': True
  ...
}
```

**DIAGNÓSTICO 1:** `tem_confirmacao_pendente = False` quando deveria ser `True`

**Causa:** Contexto não foi carregado corretamente do Firestore

---

#### [3] CONSULTA INFORMATIVA
```
Chamando responder_consulta_informativa com mensagem='...'
Resposta recebida: False | tipo=<class 'NoneType'>
```

**DIAGNÓSTICO 2:** Sistema entrou em modo "consulta informativa" ao invés de "confirmação pendente"

**Causa:** Como `tem_confirmacao_pendente = False`, o sistema tratou como pergunta nova

---

### Estado DEPOIS da Mensagem
```
confirmacao_pendente: False  ← Não foi atualizado para executar ação
draft_confirmacao: Não executado
evento_criado: False
```

---

## 🔍 CENÁRIO 07 — Negação Embutida

### Entrada
```
Mensagem: "Entendi tudo que você explicou, mas não quero mais marcar esse horário."
Canal: WhatsApp
```

### Estado ANTES da Mensagem (Esperado)
```
confirmacao_pendente: True ✓
draft_confirmacao: {
  'servico': 'corte',
  'profissional': 'Bruna',
  'data': 'amanhã',
  'hora': '14:00'
}
```

**Status:** Draft foi salvo corretamente em Firestore.

---

### Processamento da Mensagem

#### [1] ADMIN Check
```
[ADMIN] entrada | texto='Entendi tudo que você explicou, mas não quero mais marcar esse horário.'
[ADMIN] nenhuma intenção admin detectada ✓
```

#### [2] CLASSIFICADOR CONTEXTO
```
modo_conversa: 'neutro'
confianca: 0
motivo: 'sem_composicao_suficiente'
features: {
  'tem_fluxo_ativo': False
  'tem_draft': False              ← ❌ PROBLEMA! Draft DEVERIA ser True
  'tem_confirmacao_pendente': False  ← ❌ CRÍTICO! Deveria ser True
  'tem_pergunta': False
  'tem_tempo': False
  ...
}
```

**DIAGNÓSTICO 1:** Idêntico ao Cenário 06 — contexto não foi carregado

**DIAGNÓSTICO 2:** Negação não foi detectada (não há intenção de cancelamento)

---

### Estado DEPOIS da Mensagem
```
confirmacao_pendente: True (preservado, não processado)
draft_confirmacao: Preservado (não foi cancelado)
evento_criado: False
ação_cancelamento: Não foi executada
```

---

## 🎯 DIAGNÓSTICO RESUMIDO

| Aspecto | Cenário 06 | Cenário 07 | Causa Raiz |
|---------|---|---|---|
| **Confirmação detectada?** | ❌ NÃO | N/A | Contexto não carregado |
| **Negação detectada?** | N/A | ❌ NÃO | Contexto não carregado |
| **Draft carregado?** | ❌ NÃO | ❌ NÃO | `tem_draft = False` |
| **confirmacao_pendente carregado?** | ❌ NÃO | ❌ NÃO | `tem_confirmacao_pendente = False` |
| **Fluxo executado?** | ❌ NÃO | ❌ NÃO | Tratados como consulta nova |

---

## 🔎 INVESTIGAÇÃO: Por Que Contexto Não Carrega?

### Funções Envolvidas

**Principal:**
- `carregar_contexto_temporario()` - carrega dados do Firestore
- `classificador_contexto()` - usa dados para classificar features

**Locations:**
- Dados salvos em: `Clientes/{tenant_id}/Sessoes/{actor_id}` ✓ (confirmado em logs)
- Dados lidos em: `classificador_contexto()` deve chamar `carregar_contexto_temporario()`

### Hipóteses Investigadas

#### H1: Contexto não está sendo carregado
**Status:** Verificando logs para see if `carregar_contexto_temporario()` foi chamado
**Evidência:** `tem_confirmacao_pendente = False` quando deveria ser `True`

#### H2: Contexto está sendo descartado por guard_tenant
**Status:** Verificar guard_validacao em logs
**Próximo:** Procurar por `[CTX_LEGADO_TENANT_MISMATCH]` ou guard validation errors

#### H3: Contexto existe em Firestore mas não é lido
**Status:** Logs mostram draft foi SALVO (linha 447-449 do cenário 06)
**Mas:** `tem_draft = False` durante classificação
**Conclusão:** Problema está no carregamento, não na persistência

---

## 📍 Funções Responsáveis (Sem Linha Exata)

### Confirmação Não Detectada
```
Responsável: classificador_contexto() 
Localização: principal_router.py
Problema: Não lê confirmacao_pendente do contexto
Evidence: tem_confirmacao_pendente = False
Quando deveria: True
```

### Negação Não Detectada
```
Responsável: Detector de negação (eh_negacao_pendente ou similar)
Localização: principal_router.py
Problema: Nunca é acionado porque contexto não está carregado
Evidence: Sem tentativa de processar negação
Quando deveria: Detectar "não quero mais"
```

---

## 🧠 Recomendação de Patch

**PADRÃO:**
```
cenário | função responsável | causa raiz | evidência | patch recomendado
```

| Cenário | Função | Causa | Evidência | Patch |
|---------|--------|-------|-----------|-------|
| **06** | `classificador_contexto()` | Contexto não carregado | `tem_confirmacao_pendente = False` quando salvo `True` | Forçar carregamento de contexto antes de classificação |
| **07** | `eh_negacao_pendente()` | Contexto não carregado + Negação não acionada | Contexto ausente + nenhuma tentativa de detectar | Carregamento de contexto + detector de negação |

---

## ⏭️ Próximos Passos

### Imediato (SEM CORRIGIR)
1. Verificar se `carregar_contexto_temporario()` é chamado ANTES de `classificador_contexto()`
2. Verificar guard_validacao para descartes de contexto
3. Procurar por `eh_negacao_pendente()` ou função equivalente

### Após LOTE 2B e 2C
Consolidar insights sobre contexto + confirmação + negação para patch unificado

---

## 📋 Observações

### Crítico
- **Ambos os cenários falham no mesmo ponto:** Carregamento de contexto
- **Não é um problema de detecção:** É um problema de dados não chegarem ao detector
- **Firestore tem os dados:** Logs confirmam salvamento de `confirmacao_pendente: True`
- **Router recebe dados vazios:** `tem_confirmacao_pendente = False` durante processamento

### Integridade
- Draft foi salvo ✓
- confirmacao_pendente foi salvo ✓
- Setup do teste está correto ✓
- Problema está 100% no carregamento/leitura de contexto

