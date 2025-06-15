import asyncio
from scheduler.email_to_event_loop import processar_emails_para_eventos

async def main():
    await processar_emails_para_eventos("7394370553")  # Substitua pelo seu user_id de teste

asyncio.run(main())