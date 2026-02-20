# utils/whatsapp_utils.py

def send_whatsapp_message(msg: str):
    """
    Função simulada para envio de mensagem via WhatsApp.
    Em produção, pode ser integrada ao Twilio, Z-API, etc.
    """
    print(f"📲 (Simulação) Enviando mensagem no WhatsApp: {msg}")

async def enviar_mensagem_whatsapp(user_id: str, mensagem: str):
    # Implementação real de envio via API do WhatsApp
    print(f"📤 Enviando mensagem para WhatsApp de {user_id}: {mensagem}")
    return True