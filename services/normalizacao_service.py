import difflib
import unidecode
import re
from services.firebase_service_async import buscar_subcolecao, obter_id_dono

async def encontrar_servico_mais_proximo(texto_usuario: str, user_id: str = None, dono_id: str = None) -> str | None:
    """
    Busca serviço mais próximo do texto do usuário.

    Args:
        texto_usuario: Texto com possível serviço
        user_id: ID do cliente (para resolução de tenant se dono_id não informado)
        dono_id: ID do tenant (opcional). Se não informado, tenta resolver via user_id

    Returns:
        Serviço normalizado ou None se não encontrado

    Flexibilidade: Suporta chamadas como:
        - encontrar_servico_mais_proximo(texto, user_id)  # resolve tenant internamente
        - encontrar_servico_mais_proximo(texto, dono_id=dono_id)  # usa tenant direto
        - encontrar_servico_mais_proximo(texto, user_id, dono_id)  # usa tenant se informado
    """
    # Normaliza o texto do usuário removendo acentos e pontuação
    texto_normalizado = unidecode.unidecode(
        re.sub(r"[^\w\s]", " ", texto_usuario.lower())
    ).strip()
    texto_normalizado = re.sub(r"\s+", " ", texto_normalizado)

    # Se dono_id não foi informado, tentar resolver via user_id
    if not dono_id:
        if user_id:
            try:
                dono_id = await obter_id_dono(user_id)
            except Exception as e:
                print(f"[AVISO] encontrar_servico_mais_proximo: falha ao resolver tenant ({type(e).__name__})", flush=True)
                dono_id = None
        else:
            print(f"[AVISO] encontrar_servico_mais_proximo: user_id e dono_id não fornecidos", flush=True)
            return None

    if not dono_id:
        print(f"[AVISO] encontrar_servico_mais_proximo: tenant não resolvido para user_id={user_id}", flush=True)
        return None

    profissionais = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}

    # Extrai e normaliza todos os serviços possíveis
    todos_servicos = set()
    for dados in profissionais.values():
        servs = dados.get("servicos", [])
        for s in servs:
            if isinstance(s, str):
                s_norm = unidecode.unidecode(
                    re.sub(r"[^\w\s]", " ", s.lower())
                ).strip()
                s_norm = re.sub(r"\s+", " ", s_norm)
                todos_servicos.add(s_norm)

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

    # 3) fallback - matching frase toda
    match = difflib.get_close_matches(texto_normalizado, candidatos, n=1, cutoff=0.4)
    if match:
        return match[0]

    return None