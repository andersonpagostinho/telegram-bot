import asyncio
from scheduler.email_to_event_loop import loop_verificacao_emails

if __name__ == "__main__":
    try:
        asyncio.run(loop_verificacao_emails())
    except KeyboardInterrupt:
        print("🛑 Loop encerrado manualmente.")
