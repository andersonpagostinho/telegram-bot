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

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// ============================================================================
// CONFIGURAÇÃO
// ============================================================================

// Determinar diretório de sessão a partir de env ou fallback
const SESSION_DIR = process.env.WHATSAPP_SESSION_DIR || resolve(__dirname, "../data/whatsapp-session");

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
      log.warn(`[QR_CODE] Escaneie o código acima para autenticar`);
    }

    if (connection === "connecting") {
      log.info(`[CONNECTION] Conectando ao WhatsApp...`);
    }

    if (connection === "open") {
      log.info(`[CONNECTION] ✅ Conectado ao WhatsApp Web`);
      log.info(`[STATUS] Pronto para receber mensagens`);
    }

    if (connection === "close") {
      if (lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut) {
        // Reconectar se não for logout intencional
        setTimeout(connectToWhatsApp, 3000);
      } else {
        log.warn(`[CONNECTION] ❌ Desconectado (logout)`);
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
    log.info(`[MESSAGE_RECEIVED] De: ${senderName} | Texto: "${textContent}"`);

    // ====================================================================
    // RESPONDER COM FIXO POR ENQUANTO
    // ====================================================================
    const responseText = "Oi, sou a NeoEve.";

    try {
      await sock.sendMessage(sender, { text: responseText });
      log.info(`[MESSAGE_SENT] Para: ${senderName} | Resposta enviada`);
    } catch (error) {
      log.error(`[ERROR_SEND] Falha ao enviar para ${senderName}: ${error.message}`);
    }
  });

  // ========================================================================
  // EVENT: Presença
  // ========================================================================
  sock.ev.on("presence.update", (presenceUpdates) => {
    for (const { from, type } of presenceUpdates) {
      log.debug(`[PRESENCE] ${from} está ${type}`);
    }
  });

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
