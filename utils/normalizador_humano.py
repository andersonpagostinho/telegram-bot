# utils/normalizador_humano.py

import re
import unicodedata


def _normalizar_texto(texto: str) -> str:
    texto = (texto or "").lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"\s+", " ", texto)
    return texto


def _tem_algum(texto: str, termos: list[str]) -> bool:
    return any(t in texto for t in termos)


def normalizar_intencao_humana(texto: str) -> dict:
    """
    Interpreta sinais humanos/socialmente implícitos.

    Não calcula agenda.
    Não verifica disponibilidade.
    Não escolhe profissional.
    Não cria evento.
    Não executa regra de negócio.

    Apenas retorna flags operacionais para o router/motor determinístico.
    """

    t = _normalizar_texto(texto)

    sinais = {}

    # 1. Cliente aceita qualquer profissional
    if _tem_algum(t, [
        "qualquer um",
        "qualquer uma",
        "quem tiver",
        "quem estiver",
        "qual tiver",
        "tanto faz",
        "pode ser qualquer",
        "o que tiver",
        "a que tiver",
        "o primeiro disponivel",
        "a primeira disponivel",
        "quem puder",
        "quem conseguir",
    ]):
        sinais["profissional_indiferente"] = True

    # 2. Cliente quer algo rápido/simples
    if _tem_algum(t, [
        "algo rapido",
        "coisa rapida",
        "rapidinho",
        "rapido mesmo",
        "bem rapido",
        "coisa simples",
        "algo simples",
        "simples mesmo",
        "so arrumar",
        "so dar um jeito",
        "so ajeitar",
        "so deixar bonito",
        "nada muito demorado",
        "sem demorar",
    ]):
        sinais["preferencia_rapidez"] = True

    # 3. Cliente aceita flexibilidade de horário
    if _tem_algum(t, [
        "mais ou menos",
        "por volta",
        "aproximadamente",
        "perto desse horario",
        "nesse horario mais ou menos",
        "la pelas",
        "tipo umas",
        "umas 10",
        "umas 11",
        "umas 14",
        "umas 15",
        "umas 16",
        "umas 17",
    ]):
        sinais["horario_flexivel"] = True

    # 4. Cliente pede recomendação/ajuda
    if _tem_algum(t, [
        "me ajuda",
        "me indica",
        "me recomenda",
        "o que voce acha",
        "o que vc acha",
        "o que e melhor",
        "qual voce recomenda",
        "qual vc recomenda",
        "qual fica melhor",
        "nao sei o que fazer",
        "nao sei qual",
    ]):
        sinais["pedido_recomendacao"] = True

    # 5. Cliente tem objetivo/evento
    if _tem_algum(t, [
        "casamento",
        "formatura",
        "festa",
        "evento",
        "aniversario",
        "reuniao",
        "entrevista",
        "jantar",
        "encontro",
        "viagem",
        "ensaio",
        "foto",
        "sessao de fotos",
    ]):
        sinais["objetivo_evento"] = True

    return sinais