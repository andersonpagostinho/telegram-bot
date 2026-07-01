#!/usr/bin/env node

import makeWASocket, {
  DisconnectReason,
  useMultiFileAuthState,
  fetchLatestBaileysVersion,
} from "baileys";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import pino from "pino";
import pretty from "pino-pretty";
import { existsSync, mkdirSync } from "fs";
import qrcode from "qrcode-terminal";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// ============================================================================
// CONFIGURAÇÃO
// ============================================================================

// Determinar diretório de sessão a partir de env ou fallback
const SESSION_DIR = process.env.WHATSAPP_SESSION_DIR || resolve(__dirname, "../data/whatsapp-session");

// Configuração da ponte com NeoEve
const WHATSAPP_NEOEVE_NUMBER = process.env.WHATSAPP_NEOEVE_NUMBER || "5519994443694";
const WHATSAPP_TEST_TENANT_ID = process.env.WHATSAPP_TEST_TENANT_ID || "7394370553";
const WHATSAPP_BRIDGE_URL = process.env.WHATSAPP_BRIDGE_URL || "http://localhost:10000/whatsapp/incoming";
const WHATSAPP_BRIDGE_TIMEOUT_MS = parseInt(process.env.WHATSAPP_BRIDGE_TIMEOUT_MS || "15000", 10);

// Logger com pino-pretty
const logger = pino(
  {
    transport: {
      target: "pino-pretty",
      options: {
        colorize: true,
        translateTime: "SYS:standard",
        ignore: "pid,hostname",
      },
    },
  }
);

const log = logger.child({ module: "whatsapp-adapter" });

// ============================================================================
// FUNÇÕES AUXILIARES
// ============================================================================

/**
 * Extrair número de telefone do JID do WhatsApp
 * Formato: 551999444369@s.whatsapp.net → 551999444369
 */
function extrair_actor_id(jid) {
  const match = jid.match(/^(\d+)@/);
  return match ? match[1] : jid;
}

/**
 * Enviar mensagem para ponte NeoEve
 */
async function enviar_para_ponte(texto, actorId, sock, sender) {
  const payload = {
    canal: "whatsapp",
    tenant_id: WHATSAPP_TEST_TENANT_ID,
    neoeve_number: WHATSAPP_NEOEVE_NUMBER,
    actor_id: actorId,
    texto: texto,
  };

  log.info(`[BRIDGE] Enviando para ${WHATSAPP_BRIDGE_URL}`, payload);

  try {
    const response = await fetch(WHATSAPP_BRIDGE_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
      timeout: WHATSAPP_BRIDGE_TIMEOUT_MS,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    log.info(`[BRIDGE_RESPONSE] Recebida resposta:`, data);

    // Enviar resposta de volta ao WhatsApp
    if (data.resposta) {
      await sock.sendMessage(sender, { text: data.resposta });
      log.info(`[MESSAGE_SENT] Resposta do núcleo enviada para ${sender}`);
    } else {
      log.warn(`[BRIDGE_RESPONSE] Sem campo 'resposta' na resposta`);
    }

    return data;
  } catch (error) {
    log.error(`[BRIDGE_ERROR] Falha ao conectar com ponte: ${error.message}`);

    // Enviar mensagem de fallback ao usuário
    const fallback = "Estou com instabilidade agora. Pode tentar novamente em alguns segundos?";
    try {
      await sock.sendMessage(sender, { text: fallback });
      log.info(`[FALLBACK_SENT] Mensagem de fallback enviada para ${sender}`);
    } catch (sendError) {
      log.error(`[FALLBACK_ERROR] Falha ao enviar fallback: ${sendError.message}`);
    }

    return null;
  }
}

async function connectToWhatsApp() {
  // Garantir que o diretório de sessão existe
  if (!existsSync(SESSION_DIR)) {
    log.info(`[INIT] Criando diretório de sessão: ${SESSION_DIR}`);
    mkdirSync(SESSION_DIR, { recursive: true });
  }

  const { version, isLatest } = await fetchLatestBaileysVersion();
  log.info(`[BAILEYS] Versão: ${version} (Latest: ${isLatest})`);

  const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);

  const sock = makeWASocket({
    version,
    logger: pino({ level: "silent" }),
    auth: state,
    browser: ["Chrome", "latest"],
    syncFullHistory: false,
    shouldIgnoreJid: (jid) => {
      // Ignorar status broadcast
      return jid.includes("status@broadcast");
    },
  });

  // ========================================================================
  // EVENT: Credenciais atualizadas
  // ========================================================================
  sock.ev.on("creds.update", saveCreds);

  // ========================================================================
  // EVENT: Conexão
  // ========================================================================
  sock.ev.on("connection.update", (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      log.warn(`[QR_CODE] Escaneie o QR Code abaixo para autenticar`);
      // Gerar e imprimir QR Code no terminal
      try {
        qrcode.generate(qr, { small: true });
      } catch (error) {
        log.error(`[QR_CODE_ERROR] Erro ao gerar QR Code: ${error.message}`);
      }
    }

    if (connection === "connecting") {
      log.info(`[CONNECTION] Conectando ao WhatsApp...`);
    }

    if (connection === "open") {
      log.info(`[CONNECTION] Conectado ao WhatsApp Web`);
      log.info(`[STATUS] Pronto para receber mensagens`);
    }

    if (connection === "close") {
      if (lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut) {
        // Reconectar se não for logout intencional
        log.info(`[CONNECTION] Reconectando em 3s...`);
        setTimeout(connectToWhatsApp, 3000);
      } else {
        log.warn(`[CONNECTION] Desconectado (logout)`);
      }
    }
  });

  // ========================================================================
  // EVENT: Mensagens
  // ========================================================================
  sock.ev.on("messages.upsert", async (m) => {
    const msg = m.messages[0];

    if (!msg.message) {
      return; // Mensagem vazia
    }

    const isGroup = msg.key.remoteJid.endsWith("@g.us");
    const isSelfMessage = msg.key.fromMe;
    const sender = msg.key.remoteJid;
    const senderName = msg.pushName || sender;

    // ====================================================================
    // FILTRO 1: Ignorar mensagens de grupo
    // ====================================================================
    if (isGroup) {
      log.debug(`[SKIP_GROUP] Ignorando mensagem de grupo: ${sender}`);
      return;
    }

    // ====================================================================
    // FILTRO 2: Ignorar mensagens próprias
    // ====================================================================
    if (isSelfMessage) {
      log.debug(`[SKIP_SELF] Ignorando mensagem própria`);
      return;
    }

    // ====================================================================
    // EXTRAIR TIPO DE MENSAGEM
    // ====================================================================
    const messageType = Object.keys(msg.message)[0];
    let textContent = null;

    if (messageType === "conversation") {
      textContent = msg.message.conversation;
    } else if (messageType === "extendedTextMessage") {
      textContent = msg.message.extendedTextMessage.text;
    } else {
      log.info(`[MESSAGE_RECEIVED] Tipo não-texto de ${senderName}: ${messageType}`);
      log.debug(`[TODO] Implementar suporte para: ${messageType}`);
      return;
    }

    // ====================================================================
    // PROCESSAR MENSAGEM DE TEXTO
    // ====================================================================
    log.info(`[MESSAGE_RECEIVED] De: ${senderName} (${sender}) | Texto: "${textContent}"`);

    // ====================================================================
    // EXTRAIR ACTOR_ID E ENVIAR PARA PONTE
    // ====================================================================
    const actorId = extrair_actor_id(sender);
    log.info(`[ACTOR_ID] Extraído: ${actorId}`);

    // Enviar para ponte NeoEve (não responder fixo)
    await enviar_para_ponte(textContent, actorId, sock, sender);
  });

  // ========================================================================
  // EVENT: Presença (não crítico para Marco 2A — desabilitado)
  // ========================================================================
  // Nota: Evento presence.update não é essencial para funcionalidade de
  // mensagens. Desabilitado para evitar crashes. Pode ser implementado
  // em versões futuras com tratamento defensivo se necessário.

  return sock;
}

// ============================================================================
// INICIALIZAR ADAPTER
// ============================================================================
log.info(`[STARTUP] NeoEve WhatsApp Web Adapter v0.1.0`);
log.info(`[CONFIG] Sessão salvará em: ${SESSION_DIR}`);
log.info(`[CONFIG] Ambiente: ${process.env.NODE_ENV || "development"}`);

connectToWhatsApp().catch((error) => {
  log.error(`[FATAL] Erro ao conectar: ${error.message}`);
  process.exit(1);
});

// Handle graceful shutdown
process.on("SIGINT", () => {
  log.info(`[SHUTDOWN] Recebido SIGINT, encerrando...`);
  process.exit(0);
});

process.on("SIGTERM", () => {
  log.info(`[SHUTDOWN] Recebido SIGTERM, encerrando...`);
  process.exit(0);
});
