# WhatsApp Web Adapter — Teste Primeiro Marco

**Data:** 2026-07-01  
**Versão:** 0.1.0  
**Status:** 🚧 MVP — Isolado, sem integração com principal_router  

---

## Objetivo

Implementar primeiro marco do WhatsApp Web Adapter:
- ✅ Rodar no mesmo Render atual
- ✅ Conectar via QR Code (Baileys)
- ✅ Receber mensagem de texto
- ✅ Responder fixo: "Oi, sou a NeoEve."
- ❌ Sem integração com router ainda
- ❌ Sem GPT, agenda, conflito, Firestore crítico

---

## Instalação (Dev Local)

### Pré-requisitos

```bash
node --version  # >= 18.0.0
npm --version   # >= 9.0.0
```

### Setup

```bash
# 1. Navegar para projeto
cd "C:\Users\ANDERSON\iCloudDrive\Projeto Mercado Digital\Agente Bot\NeoEve - Empresarial"

# 2. Instalar dependências
npm install

# 3. Criar diretório de sessão (se não existir)
mkdir -p data/whatsapp-session
```

---

## Configuração

### Variáveis de Ambiente

```bash
# .env (opcional)
WHATSAPP_SESSION_DIR=/var/data/whatsapp-session
NODE_ENV=development
```

**Fallback:**
- Se `WHATSAPP_SESSION_DIR` não definida: `./data/whatsapp-session`
- Em Render: definir como `/var/data/whatsapp-session` (persistente)

### .gitignore

Adicionar (se não existir):

```gitignore
# WhatsApp Web Session
data/
node_modules/
.env.local
```

---

## Execução

### Development Local

```bash
npm run whatsapp:dev
```

**Saída esperada:**
```
[12:34:56] ℹ whatsapp-adapter: [STARTUP] NeoEve WhatsApp Web Adapter v0.1.0
[12:34:56] ℹ whatsapp-adapter: [CONFIG] Sessão salvará em: ./data/whatsapp-session
[12:34:57] ℹ whatsapp-adapter: [BAILEYS] Versão: 6.5.0 (Latest: true)
[12:34:58] ⚠ [QR_CODE] Escaneie o código acima para autenticar
    ▄▄▄▄▄▄▄ ▄▄▄ ▄▄▄ ▄▄▄▄▄▄▄
    █ ▄▄▄ █ ▀▀▄ ▀█▀ █ ▄▄▄ █
    █ ███ █ ▀▄▀▀ ▀█▄ █ ███ █
    █▄▄▄▄▄█ ▄ ▄ ▄ ▄ ▄█▄▄▄▄▄█
    ▄▄▄▄▄▄▄ ▀▄█▀▀▀▀▀ ▄▄▄▄▄▄▄
    [QR CODE AQUI]

[12:35:10] ℹ whatsapp-adapter: [CONNECTION] Conectando ao WhatsApp...
[12:35:15] ℹ whatsapp-adapter: [CONNECTION] ✅ Conectado ao WhatsApp Web
[12:35:15] ℹ whatsapp-adapter: [STATUS] Pronto para receber mensagens
```

### Production (Render)

```bash
npm run whatsapp:start
```

Ou via Procfile:
```
web: npm run whatsapp:start
```

---

## Critério de Aceite

### ✅ 1. npm install funciona

```bash
npm install
# Esperar: instalação de baileys, pino, pino-pretty
```

### ✅ 2. npm run whatsapp:dev inicia o adaptador

```bash
npm run whatsapp:dev
# Esperado: logs de inicialização
```

### ✅ 3. QR Code aparece no terminal

```
[12:34:58] ⚠ [QR_CODE] Escaneie o código acima para autenticar
    ▄▄▄▄▄▄▄ ▄▄▄ ▄▄▄ ▄▄▄▄▄▄▄
    [QR CODE ASCII]
```

### ✅ 4. Escaneando com chip NeoEve, sessão fica salva

**Verificar:**
```bash
ls -la data/whatsapp-session/
# Esperado: archivos de credentials
```

**Logs esperados:**
```
[12:35:10] ℹ whatsapp-adapter: [CONNECTION] ✅ Conectado ao WhatsApp Web
[12:35:15] ℹ whatsapp-adapter: [STATUS] Pronto para receber mensagens
```

### ✅ 5. Enviar mensagem de WhatsApp pessoal

No seu WhatsApp pessoal (não é grupo):
```
Você: oi
```

**Log esperado:**
```
[12:36:22] ℹ whatsapp-adapter: [MESSAGE_RECEIVED] De: Seu Nome | Texto: "oi"
```

### ✅ 6. Chip NeoEve responde

No seu WhatsApp, você recebe:
```
NeoEve: Oi, sou a NeoEve.
```

**Log esperado:**
```
[12:36:25] ℹ whatsapp-adapter: [MESSAGE_SENT] Para: Seu Nome | Resposta enviada
```

---

## Comportamento Implementado

### Mensagens Processadas

| Tipo | Ação | Log |
|------|------|-----|
| **Texto direto** | Responder fixo | `[MESSAGE_RECEIVED]` + `[MESSAGE_SENT]` |
| **Texto extended** | Responder fixo | `[MESSAGE_RECEIVED]` + `[MESSAGE_SENT]` |
| **Mensagem de grupo** | Ignorar | `[SKIP_GROUP]` |
| **Mensagem própria** | Ignorar | `[SKIP_SELF]` |
| **Mídia (img, áudio)** | Logar tipo | `[MESSAGE_RECEIVED] Tipo não-texto` |

### Filtros

```javascript
// Filtro 1: Ignorar grupos
if (isGroup) return;

// Filtro 2: Ignorar próprias mensagens
if (isSelfMessage) return;

// Filtro 3: Extrair apenas texto
if (!isTextMessage) {
  log.info(`Tipo não-texto: ${type}`);
  return;
}
```

### Resposta Fixa

Qualquer mensagem de texto recebida:
```
→ Resposta: "Oi, sou a NeoEve."
```

---

## Próximos Marcos

### Fase 2 (Não implementado ainda)

- [ ] Integrar com `principal_router.py`
- [ ] Passar mensagem para GPT
- [ ] Processar comandos de agenda
- [ ] Validar conflitos
- [ ] Salvar eventos em Firestore

### Fase 3 (Não implementado ainda)

- [ ] Suporte a mídia (imagens, áudio)
- [ ] Suporte a mensagens de grupo (com prefixo)
- [ ] Webhook para eventos de status
- [ ] Rate limiting

---

## Troubleshooting

### "QR Code não aparece"

1. Verificar Node.js >= 18
2. Verificar terminal tem suporte UTF-8
3. Tentar:
   ```bash
   npm run whatsapp:dev 2>&1 | tee whatsapp.log
   ```

### "Mensagens não são recebidas"

1. Verificar conexão:
   ```
   [CONNECTION] ✅ Conectado ao WhatsApp Web
   ```
2. Se desconectou:
   ```
   [CONNECTION] ❌ Desconectado
   ```
   → Reconectar automaticamente em 3s

3. Verificar se não é mensagem de grupo:
   ```
   [SKIP_GROUP] Ignorando mensagem de grupo
   ```

### "Sessão não foi salva"

```bash
# Verificar diretório
ls -la data/whatsapp-session/

# Esperado:
# - creds.json
# - med_*.json
# - pre-key-*.json
```

Se vazio → Escaneou o QR corretamente? Tentar novamente.

---

## Logs Importantes

| Log | Significado |
|-----|-------------|
| `[STARTUP]` | Inicialização |
| `[QR_CODE]` | QR disponível para escanear |
| `[CONNECTION] ✅` | Conectado |
| `[CONNECTION] ❌` | Desconectado |
| `[MESSAGE_RECEIVED]` | Mensagem de texto recebida |
| `[MESSAGE_SENT]` | Resposta enviada |
| `[SKIP_GROUP]` | Mensagem de grupo ignorada |
| `[SKIP_SELF]` | Mensagem própria ignorada |
| `[ERROR_SEND]` | Falha ao enviar resposta |

---

## Estrutura de Arquivos

```
NeoEve-Empresarial/
├── adapters/
│   └── whatsapp_web_adapter.js    ← Adaptador principal
├── data/
│   └── whatsapp-session/          ← Sessão (não versionada)
├── docs/
│   └── whatsapp/
│       └── WHATSAPP_WEB_ADAPTER_TESTE.md  ← Este arquivo
├── package.json                   ← Dependências Node.js
├── .gitignore                     ← Inclui data/
└── ...
```

---

## Isolamento e Segurança

### ✅ Isolado do Router Python

- Adaptador é **Node.js puro**
- Não importa funções Python
- Não acessa Firestore ainda
- Não chama GPT
- Não mexe em agenda/conflito/disponibilidade

### ✅ Sessão Persistente

- Salva em `WHATSAPP_SESSION_DIR`
- Reutiliza sessão entre restarts
- Não precisa escanear QR toda vez

### ✅ Sem Versionar Sessão

```gitignore
data/
```

---

## Render Deployment

(Próxima fase — não implementado ainda)

```bash
# Em Render, adicionar env:
WHATSAPP_SESSION_DIR=/var/data/whatsapp-session

# E garantir que /var/data é persistente
```

---

**Versão:** 0.1.0  
**Última atualização:** 2026-07-01
