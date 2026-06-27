# SEG-05B — MEC-03: Ativação Controlada de Whitelist Classe A

**Status**: ✅ IMPLEMENTAÇÃO CONCLUÍDA  
**Data**: 2026-06-23  
**Escopo**: Ativação de responder_automaticamente com verificação de Whitelist Classe A (A-01 a A-06)  
**Critério de Aprovação**: G1 + G2 + P1 E2E (42/42) + P0 (174/174)

---

## Sumário Executivo

**Objetivo**: Ativar MEC-03 (responder_automaticamente) permitindo que o bot responda automaticamente apenas a mensagens na Whitelist Classe A quando `responder_automaticamente=False`.

**Implementação**:
- ✅ Serviço de whitelist (`whitelist_service.py`)
- ✅ Integração em `bot.py::tratar_mensagens_gerais()`
- ✅ Testes G1 (Override Manual) e G2 (Whitelist Classe A)
- ⏳ Validação: P1 E2E + P0 Regressão (pendente)

---

## Arquivos Alterados

### Novos Arquivos

| Arquivo | Responsabilidade |
|---------|------------------|
| `services/whitelist_service.py` | Classificação e verificação de Whitelist Classe A |
| `tests/test_seg_05b_mec03.py` | Testes G1 e G2 |

### Arquivos Modificados

| Arquivo | Linhas | Mudança |
|---------|--------|---------|
| `handlers/bot.py` | +1 import, +27 linhas | Importar whitelist_service e adicionar verificação MEC-03 |

---

## Detalhes Técnicos

### 1. whitelist_service.py

**Funções principais**:

#### `classificar_com_whitelist(mensagem: str, actor_id: str) -> Tuple[bool, str, str]`
Classifica se mensagem está em Whitelist Classe A.

```python
# Exemplo
esta_na_whitelist, categoria, nome = classificar_com_whitelist("sim", "user123")
# → (True, "A-01", "Confirmação Positiva")
```

**Categorias Whitelist**:
- **A-01**: Confirmação Positiva (sim, ok, certo, confirmo, ...)
- **A-02**: Confirmação Negativa (não, nao, no, nope, ...)
- **A-03**: Cancelamento (cancelar, para, stop, ...)
- **A-04**: Refinamento de Cancelamento (cancelar agendamento, desmarcar, ...)
- **A-05**: Onboarding (olá, oi, tudo bem, ...)
- **A-06**: Comandos Administrativos (/help, /pausar, /retomar, ...)

#### `verificar_com_whitelist(mensagem, actor_id, tenant_id, registrar_bloqueio) -> Tuple[bool, Dict]`

Verifica se mensagem pode ser respondida automaticamente.

**Fluxo**:
1. Carregar `responder_automaticamente` de Governanca
2. Se `True`: permitir qualquer mensagem (Override Manual)
3. Se `False`: verificar Whitelist Classe A
   - Se em whitelist: permitir
   - Se fora: bloquear + registrar auditoria

```python
# Exemplo
permitida, detalhes = await verificar_com_whitelist(
    mensagem="qual é o seu nome?",
    actor_id="user123",
    tenant_id="tenant_abc",
    registrar_bloqueio=True
)
# → (False, {"motivo": "...", "categoria_esperada": "Whitelist Classe A", ...})
```

### 2. Integração em bot.py

**Local**: `handlers/bot.py::tratar_mensagens_gerais()` linha ~135

**Lógica**:
```python
# Após obter tenant_id
permitida, detalhes_bloqueio = await verificar_com_whitelist(
    mensagem=msg_text,
    actor_id=user_id,
    tenant_id=tenant_id,
    registrar_bloqueio=True
)

if not permitida and detalhes_bloqueio:
    # Responder com mensagem padrão
    await update.message.reply_text(
        "⏸️ Bot em modo resposta manual.\n\n"
        "Esperando confirmações, cancelamentos ou comandos administrativos."
    )
    raise ApplicationHandlerStop
```

**Comportamento**:
- ✅ Se `responder_automaticamente=True`: todas as mensagens passam
- ✅ Se `responder_automaticamente=False`: apenas Whitelist A-01 a A-06 passam
- ✅ Mensagens bloqueadas recebem resposta padronizada
- ✅ Bloqueios são auditados em `AuditoriaGovernanca`

---

## Testes Implementados

### G1: Override Manual

**Objetivo**: Validar que `responder_automaticamente=True` permite qualquer mensagem.

**Testes**:
- `test_g1_qualquer_mensagem_permitida`: Mensagens aleatórias (fora de whitelist) são permitidas
- `test_g1_responder_automaticamente_default_true`: Sem governanca, padrão é True

**Casos testados**:
- "opa tudo bem?" → ✅ Permitida
- "qual é o seu nome?" → ✅ Permitida
- "como você funciona?" → ✅ Permitida

### G2: Whitelist Classe A

**Objetivo**: Validar que `responder_automaticamente=False` permite apenas A-01 a A-06.

**Testes**:
- `test_g2_a01_confirmacao_positiva`: Confirmações ("sim", "ok", "certo", ...)
- `test_g2_a02_confirmacao_negativa`: Negações ("não", "nao", "no", ...)
- `test_g2_a03_cancelamento`: Cancelamentos ("cancelar", "para", "stop", ...)
- `test_g2_a05_onboarding`: Saudações ("olá", "oi", "tudo bem", ...)
- `test_g2_a06_comandos_admin`: Comandos ("/help", "/pausar", "/retomar", ...)
- `test_g2_mensagens_fora_whitelist_bloqueadas`: Mensagens fora da whitelist são bloqueadas

**Casos testados (Permitidos)**:
- "sim" → ✅ A-01
- "não" → ✅ A-02
- "cancelar" → ✅ A-03
- "oi" → ✅ A-05
- "/help" → ✅ A-06

**Casos testados (Bloqueados)**:
- "qual é o seu nome?" → ❌ Bloqueado
- "como você funciona?" → ❌ Bloqueado
- "me avisa quando terminar" → ❌ Bloqueado

---

## Escopo Respeitado

### Permitido ✅

- ✅ Verificação de `responder_automaticamente` de Governanca
- ✅ Whitelist Classe A (A-01 a A-06)
- ✅ Auditoria de bloqueios
- ✅ Testes G1 e G2

### Não Implementado ❌

- ❌ MEC-04 (contato desconhecido)
- ❌ MEC-05 (modo silencioso)
- ❌ Modo dono
- ❌ Profissional interno
- ❌ Blacklists Classe B
- ❌ Separação de canais
- ❌ Mudanças em notificações
- ❌ Mudanças em lembretes

---

## Critério de Aprovação Local

| Teste | Status | Evidência |
|-------|--------|-----------|
| **G1 — Override Manual** | ⏳ Pendente | tests/test_seg_05b_mec03.py::TestG1OverrideManual |
| **G2 — Whitelist Classe A** | ⏳ Pendente | tests/test_seg_05b_mec03.py::TestG2WhitelistClasseA |
| **Casos críticos** | ⏳ Pendente | sim, não, cancelar, onboarding, comando |

---

## Próximas Etapas

### Fase 2: Validação Completa

```
1. Executar pytest em testes G1 e G2
   → Critério: G1 = 100%, G2 = 100%

2. Validação de regressão:
   → P1 E2E = 42/42 PASS
   → P0 Regressão = 174/174 PASS
   → Total = 216/216 PASS

3. Se alguma regressão aparecer:
   → PARAR IMEDIATAMENTE
   → Produzir auditoria
   → NÃO abrir SEG-05C

4. Se tudo passar:
   → Considerar SEG-05B concluído
```

---

## Notas de Implementação

### Decisões de Design

1. **Whitelist centralizada em um serviço**: Facilita manutenção e testes
2. **Padrões regex para flexibilidade**: Permite variações de digitação
3. **Auditoria automática**: Toda mensagem bloqueada é registrada em `AuditoriaGovernanca`
4. **Mensagem padronizada**: Usuário recebe feedback claro sobre restrição
5. **ApplicationHandlerStop**: Previne processamento downstream quando bloqueado

### Limitações Conhecidas

- Whitelist não considera contexto da conversa (apenas texto da mensagem)
- Padrões regex são case-insensitive, mas desconsideram acentuação
- Bloqueio é imediato (sem fila de tentativas)

---

## Validação Final

**Critério para considera SEG-05B CONCLUÍDO**:

✅ G1 verde (100%)  
✅ G2 verde (100%)  
✅ 216/216 PASS (P1 E2E + P0 Regressão)  
✅ Sem regressões novas  
✅ Documento entregue

---

**Documento preparado para validação**  
**Aguardando execução de testes pytest e regressão completa**  
**Data**: 2026-06-23
