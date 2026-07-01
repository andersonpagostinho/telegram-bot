# Marco 2A — Ponte WhatsApp Adapter → NeoEve Core

**Data:** 2026-07-01  
**Versão:** 0.2.0  
**Status:** 🚧 Integração com backend implementada  

---

## Objetivo

Conectar o adaptador WhatsApp Web com o núcleo NeoEve para:

1. ✅ Receber mensagem do WhatsApp
2. ✅ Extrair automaticamente `actor_id` do remetente
3. ✅ Enviar para `/whatsapp/incoming` do backend
4. ✅ Backend processa via `roteador_principal`
5. ✅ Resposta retorna ao WhatsApp

**Sem hardcoding** de números ou decisões de lógica.

---

## Arquitetura

```
┌─────────────────────┐
│  WhatsApp Pessoal   │
│  Envia: "oi"        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────────────┐
│ Adapter WhatsApp Web (Node.js)              │
│                                             │
│ 1. Recebe mensagem WhatsApp                │
│ 2. Extrai actor_id: "5519999999999"        │
│ 3. Normaliza: texto, canal, tenant_id      │
│ 4. POST /whatsapp/incoming                 │
│                                             │
│ Payload:                                    │
│ {                                           │
│   "canal": "whatsapp",                     │
│   "tenant_id": "7394370553",               │
│   "neoeve_number": "5519994443694",        │
│   "actor_id": "5519999999999",             │
│   "texto": "oi"                            │
│ }                                           │
└──────────┬──────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────┐
│ Flask Backend (Python)                      │
│ POST /whatsapp/incoming                     │
│                                             │
│ 1. Recebe payload                          │
│ 2. Chama roteador_principal(                │
│      user_id="5519999999999",              │
│      mensagem="oi"                         │
│    )                                        │
│ 3. Roteador identifica automaticamente:     │
│    - Busca Clientes/5519999999999          │
│    - Extrai id_negocio (tenant_id)         │
│    - Determina papel: dono/cliente/prof   │
│ 4. Processa mensagem                       │
│ 5. Retorna resposta                        │
│                                             │
│ Response:                                   │
│ {                                           │
│   "canal": "whatsapp",                     │
│   "actor_id": "5519999999999",             │
│   "tenant_id": "7394370553",               │
│   "resposta": "Oi! Como posso ajudar?"    │
│ }                                           │
└──────────┬──────────────────────────────────┘
           │
           ▼
┌─────────────────────┐
│  Adapter WhatsApp   │
│  POST /whatsapp/... │
│  ← Resposta         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  WhatsApp Pessoal   │
│  Recebe: "Oi!"      │
└─────────────────────┘
```

---

## Configuração

### Variáveis de Ambiente

```bash
# .env ou Render environment

# Número NeoEve (teste: +55 19 99444-3694)
WHATSAPP_NEOEVE_NUMBER=5519994443694

# Tenant para testes
WHATSAPP_TEST_TENANT_ID=7394370553

# Bridge URL (para conectar adapter com backend)
WHATSAPP_BRIDGE_URL=http://localhost:10000/whatsapp/incoming

# Timeout para requisição
WHATSAPP_BRIDGE_TIMEOUT_MS=15000

# Diretório de sessão
WHATSAPP_SESSION_DIR=/var/data/whatsapp-session
NODE_ENV=development
```

### Local Dev

```bash
# Terminal 1: Backend Flask
export FLASK_APP=flask_app.py
export WHATSAPP_BRIDGE_URL=http://localhost:5000/whatsapp/incoming
python flask_app.py

# Terminal 2: Adapter WhatsApp
export WHATSAPP_BRIDGE_URL=http://localhost:5000/whatsapp/incoming
npm run whatsapp:dev
```

### Production (Render)

```bash
# Render Environment Variables:
WHATSAPP_NEOEVE_NUMBER=5519994443694
WHATSAPP_TEST_TENANT_ID=7394370553
WHATSAPP_BRIDGE_URL=https://seu-render-app.onrender.com/whatsapp/incoming
WHATSAPP_SESSION_DIR=/var/data/whatsapp-session
```

---

## Fluxo de Mensagem

### Request: Adapter → Backend

```javascript
// adapters/whatsapp_web_adapter.js

// Quando recebe mensagem:
{
  "canal": "whatsapp",
  "tenant_id": "7394370553",
  "neoeve_number": "5519994443694",
  "actor_id": "5519999999999",   // ← Extraído automaticamente
  "texto": "oi"
}

// HTTP POST
fetch("http://localhost:5000/whatsapp/incoming", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(payload)
})
```

### Handler: Backend recebe

```python
# flask_app.py

@app.route("/whatsapp/incoming", methods=["POST"])
def whatsapp_incoming():
    payload = request.get_json()
    # {
    #   "canal": "whatsapp",
    #   "tenant_id": "7394370553",
    #   "actor_id": "5519999999999",
    #   "texto": "oi"
    # }

    resultado = asyncio.run(processar_mensagem_whatsapp(payload))
    # {
    #   "canal": "whatsapp",
    #   "actor_id": "5519999999999",
    #   "tenant_id": "7394370553",
    #   "resposta": "Oi! Como posso ajudar?"
    # }

    return jsonify(resultado)
```

### Processamento: Router identifica contexto

```python
# handlers/whatsapp_bridge_handler.py

async def processar_mensagem_whatsapp(payload):
    # Extrai actor_id e texto
    actor_id = payload["actor_id"]  # "5519999999999"
    texto = payload["texto"]         # "oi"

    # Chama roteador
    resposta = await roteador_principal(
        user_id=actor_id,      # ← Sistema identifica automaticamente
        mensagem=texto,
    )

    # roteador_principal:
    # 1. dono_id = obter_id_dono("5519999999999")
    #    → Se é dono: retorna "5519999999999"
    #    → Se é cliente: retorna id_negocio
    # 2. Processa fluxo normal com tenant isolado
    # 3. Retorna resposta

    return {
        "canal": "whatsapp",
        "actor_id": actor_id,
        "tenant_id": dono_id,  # ← Identificado automaticamente
        "resposta": resposta
    }
```

### Response: Adapter envia ao WhatsApp

```javascript
// Adapter recebe resposta
{
  "canal": "whatsapp",
  "actor_id": "5519999999999",
  "tenant_id": "7394370553",
  "resposta": "Oi! Como posso ajudar?"
}

// Envia de volta
await sock.sendMessage(sender, {
  text: resposta
})

// WhatsApp pessoal recebe:
"Oi! Como posso ajudar?"
```

---

## Extração de actor_id

### Formato do JID (WhatsApp)

```javascript
// JID no WhatsApp Web: "{numero}@s.whatsapp.net"
"5519999999999@s.whatsapp.net"

// Extrair:
const actorId = jid.match(/^(\d+)@/)[1];
// → "5519999999999"
```

### Implementação

```javascript
// adapters/whatsapp_web_adapter.js

function extrair_actor_id(jid) {
  const match = jid.match(/^(\d+)@/);
  return match ? match[1] : jid;
}

// Uso:
const actorId = extrair_actor_id("5519999999999@s.whatsapp.net");
// → "5519999999999"
```

---

## Tratamento de Falhas

### Timeout na ponte

```
Adapter envia POST
    ↓
Backend não responde em 15s
    ↓
Timeout (WHATSAPP_BRIDGE_TIMEOUT_MS)
    ↓
Fallback message enviada:
"Estou com instabilidade agora. Pode tentar novamente em alguns segundos?"
```

### Logs esperados

**Sucesso:**
```
[BRIDGE] Enviando para http://localhost:5000/whatsapp/incoming
{
  "canal": "whatsapp",
  "actor_id": "5519999999999",
  "texto": "oi"
}

[BRIDGE_RESPONSE] Recebida resposta:
{
  "resposta": "Oi! Como posso ajudar?"
}

[MESSAGE_SENT] Resposta do núcleo enviada para 5519999999999@s.whatsapp.net
```

**Falha:**
```
[BRIDGE_ERROR] Falha ao conectar com ponte: ECONNREFUSED
[FALLBACK_SENT] Mensagem de fallback enviada para 5519999999999@s.whatsapp.net
```

---

## Critério de Aceite

### 1. Adapter extrai actor_id automaticamente
```javascript
✅ actor_id = "5519999999999" (extraído de JID)
✅ Log: "[ACTOR_ID] Extraído: 5519999999999"
```

### 2. Backend recebe no formato correto
```json
✅ POST /whatsapp/incoming
✅ {
  "canal": "whatsapp",
  "tenant_id": "7394370553",
  "actor_id": "5519999999999",
  "texto": "oi"
}
```

### 3. Router identifica contexto automaticamente
```python
✅ roteador_principal("5519999999999", "oi")
✅ Sistema busca Clientes/5519999999999
✅ Determina papel: dono/cliente/prof
```

### 4. Resposta retorna ao WhatsApp
```javascript
✅ Backend envia:
{
  "resposta": "<conteúdo>"
}

✅ Adapter recebe e envia:
await sock.sendMessage(sender, { text: resposta })

✅ WhatsApp pessoal recebe a resposta
```

### 5. Nenhuma alteração em agenda/conflito/Firestore crítico
```
✅ Adapter não acessa Firestore
✅ Adapter não calcula disponibilidade
✅ Adapter não cria eventos
✅ Tudo fica no roteador (responsabilidade certa)
```

---

## Definições de Sucesso

✅ Quando número autorizado (dono) envia "oi":
- Adapter extrai actor_id
- Backend recebe com canal=whatsapp
- Router identifica como dono
- Resposta apropriada retorna

✅ Quando número de teste envia "oi":
- Mesmo fluxo
- Router identifica papel
- Resposta apropriada

✅ Nenhuma lógica de negócio no adaptador:
- Não hardcoded números
- Não decisões de contexto
- Não acesso a Firestore
- Tudo no backend

---

## Próximos Marcos

### Marco 2B
- [ ] Validação de tenant_id do remetente
- [ ] Cache de resolução actor_id → tenant_id
- [ ] Logging estruturado com tenant_id

### Marco 3
- [ ] Suporte a comandos de agenda
- [ ] Suporte a confirmação de agendamento
- [ ] Suporte a cancelamento

---

**Branch:** `whatsapp-web-adapter-render`  
**Commit:** Próximo (após validação)
