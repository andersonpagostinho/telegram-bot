# utils/whatsapp_utils.py
"""
Exportações públicas de WhatsApp.
A implementação real está em services/whatsapp_service.py.
"""

from services.whatsapp_service import enviar_mensagem_whatsapp

__all__ = ["enviar_mensagem_whatsapp"]