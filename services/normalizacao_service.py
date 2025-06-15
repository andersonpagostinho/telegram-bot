import difflib
import unidecode
import re
from services.firebase_service_async import buscar_subcolecao

async def encontrar_servico_mais_proximo(texto_usuario: str, user_id: str) -> str | None:
    # Normaliza o texto do usuário removendo acentos e pontuação
    texto_normalizado = unidecode.unidecode(
        re.sub(r"[^\w\s]", " ", texto_usuario.lower())
    ).strip()
    texto_normalizado = re.sub(r"\s+", " ", texto_normalizado)

    profissionais = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais") or {}

    # Extrai todos os serviços possíveis
    todos_servicos = set()
    for dados in profissionais.values():
        servs = dados.get("servicos", [])
        todos_servicos.update([s.lower() for s in servs])

    candidatos = list(todos_servicos)

    # 1) verifica se algum serviço aparece como substring direta
    for candidato in candidatos:
        if candidato in texto_normalizado:
            return candidato

    # 2) tenta matching palavra a palavra
    for palavra in texto_normalizado.split():
        match = difflib.get_close_matches(palavra, candidatos, n=1, cutoff=0.8)
        if match:
            return match[0]

    # 3) fallback - matching frase toda (cutoff mais baixo)
    match = difflib.get_close_matches(texto_normalizado, candidatos, n=1, cutoff=0.4)
    if match:
        return match[0]

    return None
