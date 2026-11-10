# -*- coding: utf-8 -*-
"""
FASE 3: Serviço de Download e Transcrição de Áudio WhatsApp

Responsabilidades:
- Baixar mídia do Meta Graph API
- Validar integridade
- Converter para formato compatível
- Transcrever com Google Speech-to-Text
- Gerenciar arquivos temporários
- Garantir idempotência

Não faz:
- Interpretar intenção (feito pelo router)
- Criar draft ou agendamento
- Alterar disponibilidade/locks
"""

import os
import hashlib
import httpx
import tempfile
import logging
from typing import Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Meta Graph API
META_API_VERSION = os.getenv("META_API_VERSION", "v20.0")
META_GRAPH_API_BASE_URL = os.getenv("META_GRAPH_API_BASE_URL", "https://graph.instagram.com")

# Limites
MAX_AUDIO_SIZE_MB = 16  # Google STT aceita até 15MB
AUDIO_TIMEOUT_SECONDS = 30
TEMP_DIR = tempfile.gettempdir()


async def baixar_midia_whatsapp(
    media_id: str,
    access_token: str,
    tenant_id: str,
    cliente_id: str,
    msg_id: str
) -> Optional[Tuple[str, str]]:
    """
    Download de mídia do WhatsApp com validação e conversão.

    Args:
        media_id: ID da mídia (audio.id do webhook)
        access_token: Bearer token da Meta
        tenant_id: Isolamento multi-tenant
        cliente_id: Isolamento de cliente
        msg_id: Para rastreabilidade

    Returns:
        Tupla (caminho_arquivo, mime_type) ou None se falhar
    """

    if not media_id or not access_token:
        logger.warning(f"[WA-MEDIA] Parâmetros inválidos: media_id={bool(media_id)} token={bool(access_token)}")
        return None

    print(f"[WA-MEDIA-DOWNLOAD] Iniciando download: media_id={media_id} msg_id={msg_id}", flush=True)

    try:
        # 1️⃣ OBTER URL DA MÍDIA (Graph API)
        url_info = f"{META_GRAPH_API_BASE_URL}/{META_API_VERSION}/{media_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        async with httpx.AsyncClient(timeout=AUDIO_TIMEOUT_SECONDS) as client:
            # Requisição 1: Obter URL
            response_info = await client.get(url_info, headers=headers)

            if response_info.status_code != 200:
                logger.error(f"[WA-MEDIA-ERROR] Falha ao obter URL: {response_info.status_code}")
                return None

            data = response_info.json()
            media_url = data.get("url")
            mime_type = data.get("mime_type", "")

            if not media_url:
                logger.error(f"[WA-MEDIA-ERROR] URL não retornada")
                return None

            print(f"[WA-MEDIA-DOWNLOAD] URL obtida: mime_type={mime_type}", flush=True)

            # 2️⃣ VALIDAR MIME TYPE
            if not mime_type.startswith("audio/"):
                logger.error(f"[WA-MEDIA-ERROR] MIME não suportado: {mime_type}")
                return None

            # 3️⃣ BAIXAR ARQUIVO
            response_file = await client.get(media_url, headers=headers)

            if response_file.status_code != 200:
                logger.error(f"[WA-MEDIA-ERROR] Falha ao baixar: {response_file.status_code}")
                return None

            # 4️⃣ VALIDAR TAMANHO
            file_size_mb = len(response_file.content) / (1024 * 1024)
            if file_size_mb > MAX_AUDIO_SIZE_MB:
                logger.error(f"[WA-MEDIA-ERROR] Arquivo muito grande: {file_size_mb:.1f}MB > {MAX_AUDIO_SIZE_MB}MB")
                return None

            if file_size_mb == 0:
                logger.error(f"[WA-MEDIA-ERROR] Arquivo vazio")
                return None

            print(f"[WA-MEDIA-DOWNLOAD] Arquivo baixado: {file_size_mb:.1f}MB", flush=True)

            # 5️⃣ SALVAR TEMPORARIAMENTE
            # Usar tenant_id + cliente_id + msg_id para rastreabilidade
            filename = f"audio_{tenant_id}_{cliente_id}_{msg_id}.tmp"
            temp_path = os.path.join(TEMP_DIR, filename)

            try:
                with open(temp_path, "wb") as f:
                    f.write(response_file.content)

                print(f"[WA-MEDIA-DOWNLOAD] Arquivo salvo: {temp_path}", flush=True)
                return (temp_path, mime_type)

            except Exception as e:
                logger.error(f"[WA-MEDIA-ERROR] Falha ao salvar arquivo: {e}")
                return None

    except httpx.TimeoutException:
        logger.error(f"[WA-MEDIA-ERROR] Timeout no download")
        return None
    except httpx.HTTPError as e:
        logger.error(f"[WA-MEDIA-ERROR] Erro HTTP: {e}")
        return None
    except Exception as e:
        logger.error(f"[WA-MEDIA-ERROR] Erro inesperado: {e}")
        return None


async def transcrever_audio_whatsapp(
    media_id: str,
    mime_type: str,
    access_token: str,
    tenant_id: str,
    cliente_id: str,
    msg_id: str
) -> Optional[str]:
    """
    Download, conversão e transcrição de áudio WhatsApp.

    Args:
        media_id: ID da mídia
        mime_type: Tipo MIME (ex: audio/ogg; codecs=opus)
        access_token: Bearer token Meta
        tenant_id: Isolamento
        cliente_id: Isolamento
        msg_id: Rastreabilidade

    Returns:
        Texto transcrito ou None se falhar
    """

    print(f"[WA-AUDIO-TRANSCRIBE] Iniciando: media_id={media_id} msg_id={msg_id}", flush=True)

    # 1️⃣ BAIXAR MÍDIA
    resultado_download = await baixar_midia_whatsapp(
        media_id, access_token, tenant_id, cliente_id, msg_id
    )

    if not resultado_download:
        logger.error(f"[WA-AUDIO-TRANSCRIBE] Download falhou")
        return None

    temp_path, mime_type_obtido = resultado_download

    try:
        # 2️⃣ CONVERTER PARA WAV
        from utils.audio_utils import converter_audio_para_wav, transcrever_audio

        # Para OGG/Opus, precisa converter
        if "ogg" in mime_type_obtido.lower() or "opus" in mime_type_obtido.lower():
            wav_path = temp_path.replace(".tmp", ".wav")

            print(f"[WA-AUDIO-TRANSCRIBE] Convertendo OGG→WAV", flush=True)
            sucesso_conversao = converter_audio_para_wav(temp_path, wav_path)

            if not sucesso_conversao:
                logger.error(f"[WA-AUDIO-TRANSCRIBE] Conversão falhou")
                _limpar_arquivo(temp_path)
                return None

            arquivo_transcrever = wav_path
        else:
            # Outros formatos: assumir já compatível
            arquivo_transcrever = temp_path

        # 3️⃣ TRANSCREVER
        print(f"[WA-AUDIO-TRANSCRIBE] Transcrevendo com Google STT", flush=True)
        texto = transcrever_audio(arquivo_transcrever)

        if not texto:
            logger.error(f"[WA-AUDIO-TRANSCRIBE] Transcrição vazia ou falha")
            _limpar_arquivo(temp_path)
            if arquivo_transcrever != temp_path:
                _limpar_arquivo(arquivo_transcrever)
            return None

        print(f"[WA-AUDIO-TRANSCRIBE] ✅ Transcrição bem-sucedida: {texto[:100]}", flush=True)

        # 4️⃣ LIMPEZA
        _limpar_arquivo(temp_path)
        if arquivo_transcrever != temp_path:
            _limpar_arquivo(arquivo_transcrever)

        return texto

    except Exception as e:
        logger.error(f"[WA-AUDIO-TRANSCRIBE] Erro geral: {e}")
        _limpar_arquivo(temp_path)
        return None


def _limpar_arquivo(caminho: str):
    """Limpar arquivo temporário com segurança."""
    try:
        if os.path.exists(caminho):
            os.remove(caminho)
            logger.debug(f"[WA-MEDIA] Arquivo deletado: {caminho}")
    except Exception as e:
        logger.warning(f"[WA-MEDIA] Falha ao deletar {caminho}: {e}")


# Exportar
__all__ = ["transcrever_audio_whatsapp", "baixar_midia_whatsapp"]
