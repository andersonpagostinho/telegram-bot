# services/normalizacao_service.py

import difflib
from services.firebase_service_async import buscar_subcolecao

async def encontrar_servico_mais_proximo(texto_usuario: str, user_id: str) -> str | None:
    """
    Recebe um texto do usuário e tenta encontrar o serviço mais próximo
    baseado nos serviços cadastrados dos profissionais do cliente.
    """
    texto_usuario = texto_usuario.lower().strip()

    profissionais = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais") or {}

    # Extrai todos os serviços possíveis
    todos_servicos = set()
    for dados in profissionais.values():
        servs = dados.get("servicos", [])
        todos_servicos.update([s.lower() for s in servs])

    # Usa matching aproximado
    candidatos = list(todos_servicos)
    mais_proximo = difflib.get_close_matches(texto_usuario, candidatos, n=1, cutoff=0.6)

    return mais_proximo[0] if mais_proximo else None
