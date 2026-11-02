import difflib
import unidecode
import re
from services.firebase_service_async import buscar_subcolecao, obter_id_dono

async def encontrar_servicos_candidatos(texto_usuario: str, user_id: str = None, dono_id: str = None, limite: int = 3) -> list[str]:
    """
    P0.6.2: Busca múltiplos serviços candidatos do texto do usuário.

    Diferença de encontrar_servico_mais_proximo():
    - Retorna lista (até `limite` candidatos)
    - Ordena por relevância (substring exata > fuzzy matching)
    - Não seleciona automaticamente

    Args:
        texto_usuario: Texto com possível(is) serviço(s)
        user_id: ID do cliente (para resolução de tenant)
        dono_id: ID do tenant (opcional)
        limite: Máximo de candidatos a retornar (default 3)

    Returns:
        Lista de serviços normalizados (ordenados por relevância)
    """
    texto_normalizado = unidecode.unidecode(
        re.sub(r"[^\w\s]", " ", texto_usuario.lower())
    ).strip()
    texto_normalizado = re.sub(r"\s+", " ", texto_normalizado)

    if not dono_id:
        if user_id:
            try:
                dono_id = await obter_id_dono(user_id)
            except Exception as e:
                print(f"[P0.6.2] encontrar_servicos_candidatos: falha ao resolver tenant ({type(e).__name__})", flush=True)
                dono_id = None
        else:
            print(f"[P0.6.2] encontrar_servicos_candidatos: user_id e dono_id não fornecidos", flush=True)
            return []

    if not dono_id:
        print(f"[P0.6.2] encontrar_servicos_candidatos: tenant não resolvido para user_id={user_id}", flush=True)
        return []

    profissionais = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}

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
    candidatos_ordenados = []

    # 1) Substring direta (maior relevância)
    for candidato in candidatos:
        if candidato in texto_normalizado and candidato not in candidatos_ordenados:
            candidatos_ordenados.append(candidato)
            if len(candidatos_ordenados) >= limite:
                return candidatos_ordenados

    # 2) Fuzzy matching palavra a palavra (com n=3 para múltiplos)
    for palavra in texto_normalizado.split():
        matches = difflib.get_close_matches(palavra, candidatos, n=3, cutoff=0.8)
        for match in matches:
            if match not in candidatos_ordenados:
                candidatos_ordenados.append(match)
                if len(candidatos_ordenados) >= limite:
                    return candidatos_ordenados

    # 3) Fallback: fuzzy matching frase inteira (com n=3, cutoff restritivo para evitar falsos positivos)
    # 🔥 P0 FIX: Aumentado de 0.3 para 0.75 (ainda permissivo para candidatos múltiplos, mas defensável)
    matches = difflib.get_close_matches(texto_normalizado, candidatos, n=3, cutoff=0.75)
    for match in matches:
        if match not in candidatos_ordenados:
            candidatos_ordenados.append(match)
            if len(candidatos_ordenados) >= limite:
                return candidatos_ordenados

    return candidatos_ordenados

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

    # Extrai e normaliza todos os serviços possíveis, mantendo mapeamento para original
    todos_servicos = {}  # mapa: servico_normalizado → servico_original
    for dados in profissionais.values():
        servs = dados.get("servicos", [])
        for s in servs:
            if isinstance(s, str):
                s_original = str(s).strip()
                s_norm = unidecode.unidecode(
                    re.sub(r"[^\w\s]", " ", s_original.lower())
                ).strip()
                s_norm = re.sub(r"\s+", " ", s_norm)
                # Manter o original, não sobrescrever se já existe (unlikely mas seguro)
                if s_norm not in todos_servicos:
                    todos_servicos[s_norm] = s_original

    candidatos_norm = list(todos_servicos.keys())

    # 1) verifica se algum serviço aparece como substring direta
    for candidato_norm in candidatos_norm:
        if candidato_norm in texto_normalizado:
            return todos_servicos[candidato_norm]

    # 2) tenta matching palavra a palavra COM SEMÂNTICA DE PRIMEIRA PALAVRA
    # P0.9.5 FIX: Comparar primeiro palavra do texto contra primeira palavra dos serviços
    # Isso permite "cortar" (verbo) mapear para "corte feminino" (primeira palavra "corte")

    # Mapear: primeira_palavra_normalizada → set de serviços_normalizados únicos que começam com ela
    primeiras_palavras_map = {}  # primeira_palavra → set(servicos_norm completos unicos)
    for servico_norm in candidatos_norm:
        palavras = servico_norm.split()
        if palavras:
            primeira = palavras[0]
            if primeira not in primeiras_palavras_map:
                primeiras_palavras_map[primeira] = set()
            primeiras_palavras_map[primeira].add(servico_norm)

    # Para cada palavra do texto, tentar matching contra primeiras palavras dos serviços
    for palavra in texto_normalizado.split():
        if not palavra:
            continue

        # Comparar contra primeiras palavras com cutoff 0.7 (fuzzy matching)
        # 0.7 permite capturar variações morfológicas como "cortar" (verbo) → "corte" (substantivo)
        # 72.73% similaridade entre "cortar" e "corte" passa em 0.7 mas não em 0.8
        primeiras_palavras_lista = list(primeiras_palavras_map.keys())
        match = difflib.get_close_matches(palavra, primeiras_palavras_lista, n=1, cutoff=0.7)

        if match:
            primeira_matched = match[0]
            servicos_candidatos = list(primeiras_palavras_map[primeira_matched])

            # Se há múltiplos serviços DIFERENTES que começam com a mesma primeira palavra,
            # tentar desambiguar com o restante do texto
            if len(servicos_candidatos) > 1:
                # Procurar se texto contém mais palavras do serviço
                for servico_norm in servicos_candidatos:
                    # Verificar se palavras adicionais do serviço aparecem no texto
                    palavras_servico = servico_norm.split()[1:]  # palavras após a primeira
                    if all(p in texto_normalizado for p in palavras_servico):
                        # Encontrou match com todas as palavras
                        return todos_servicos[servico_norm]

                # Se não conseguiu desambiguar, preservar None (não escolher arbitrariamente)
                # Conforme requisito: "Se não permitir desambiguar, retornar None"
                print(f"[P0.9.5] AMBÍGUO: '{palavra}' corresponde a múltiplos serviços: {servicos_candidatos}. Retornando None.", flush=True)
                return None
            else:
                # Único serviço correspondente
                return todos_servicos[servicos_candidatos[0]]

    # 3) fallback - matching frase toda
    # 🔥 P0 FIX: Aumentado de 0.4 para 0.85 para evitar falsos positivos
    # Ex: "com a bruna" tinha 40% similaridade com "coloracao" (cutoff=0.4)
    # Com 0.85, requer 85% de similaridade (muito mais restritivo)
    match = difflib.get_close_matches(texto_normalizado, candidatos_norm, n=1, cutoff=0.85)
    if match:
        return todos_servicos[match[0]]

    return None