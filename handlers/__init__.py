# [FIX] Lazy import para quebrar circular dependency
# handlers/bot.py -> router/principal_router.py -> services/gpt_executor.py -> handlers/task_handler.py -> handlers/__init__.py
# Solução: Não importar bot no __init__, deixar cliente importar diretamente de handlers.bot

def __getattr__(name):
    """Lazy loader para manter compatibilidade com: from handlers import register_handlers"""
    if name == 'register_handlers':
        from .bot import register_handlers
        return register_handlers
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
