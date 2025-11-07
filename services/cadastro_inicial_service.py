# services/cadastro_inicial_service.py
from __future__ import annotations

import re
from typing import Dict, List, Tuple, Optional

from services.firebase_service_async import (
    buscar_subcolecao,
    buscar_dado_em_path,
    salvar_dado_em_path,
)

# =========================================================
# ------------------ CONTROLE DE ETAPAS --------------------
# =========================================================

ETAPA_NEGOCIO = "negocio_base"
ETAPA_SERVICOS = "servicos_negocio"
ETAPA_PROFISSIONAIS = "profissionais"
ETAPA_CONCLUIDO = "concluido"

async def _get_config_doc(user_id: str) -> dict:
    doc = await buscar_dado_em_path(f"Clientes/{user_id}/configuracao")
    return doc or {}

async def _set_config_doc(user_id: str, data: dict):
    await salvar_dado_em_path(f"Clientes/{user_id}/configuracao", data)

async def get_etapa_config(user_id: str) -> str:
    doc = await _get_config_doc(user_id)
    return doc.get("etapa") or ETAPA_NEGOCIO

async def set_etapa_config(user_id: str, etapa: str):
    doc = await _get_config_doc(user_id)
    doc["etapa"] = etapa
    await _set_config_doc(user_id, doc)

async def salvar_dados_negocio(user_id: str, *, tipo: str = None, nome: str = None, estilo: str = None):
    doc = await _get_config_doc(user_id)
    if tipo:
        doc["tipo_negocio"] = tipo.strip()
    if nome:
        doc["nome_negocio"] = nome.strip()
    if estilo:
        doc["estilo"] = estilo.strip().lower()
    await _set_config_doc(user_id, doc)

async def get_dados_negocio(user_id: str) -> dict:
    return await _get_config_doc(user_id)

# =========================================================
# ------------------ PARSE / INTERPRETAÇÃO ----------------
# =========================================================

NUM = r"(?:\d+(?:[.,]\d+)?)"  # 50 | 50,00 | 50.00
MIN = r"(?:min|mins|minutos?)"

def _norm(txt: str) -> str:
    return (txt or "").strip()

def _to_float(s: str) -> Optional[float]:
    try:
        return float(s.replace(",", "."))
    except Exception:
        return None

def _to_int(s: str) -> Optional[int]:
    try:
        return int(s)
    except Exception:
        # tenta algo como "30min"
        m = re.search(r"(\d+)\s*(?:min|mins|minutos?)?$", s.strip(), re.I)
        if m:
            return int(m.group(1))
        return None

def _split_itens(servicos_str: str) -> List[str]:
    # separa por vírgula, ponto e vírgula ou " e "
    partes = re.split(r",|;| e ", servicos_str)
    return [p.strip() for p in partes if p.strip()]

def _parse_item_servico(raw: str) -> Tuple[str, Optional[float], Optional[int]]:
    """
    Tenta extrair: nome, preco, duracao (min)
    Aceita formatos:
      - "corte=50/30"
      - "corte = 50 / 30min"
      - "corte 50 30"
      - "corte R$50 30min"
      - "escova=45"
      - "hidratação 55"
      - "unha gel 70/90"
    """
    s = raw.strip()
    # normaliza "R$"
    s = re.sub(r"R\$\s*", "", s, flags=re.I)

    # padrão mais explícito: nome=preco/duracao
    m = re.match(r"^(.+?)\s*=\s*("+NUM+")\s*(?:/|\s)\s*(\d+)\s*"+f"(?:{MIN})?$", s, flags=re.I)
    if m:
        nome = m.group(1).strip()
        preco = _to_float(m.group(2))
        dur = _to_int(m.group(3))
        return nome, preco, dur

    # nome=preco
    m = re.match(r"^(.+?)\s*=\s*("+NUM+")\s*$", s, flags=re.I)
    if m:
        nome = m.group(1).strip()
        preco = _to_float(m.group(2))
        return nome, preco, None

    # nome preco duracao
    m = re.match(r"^(.+?)\s+("+NUM+")\s+(\d+)\s*"+f"(?:{MIN})?$", s, flags=re.I)
    if m:
        nome = m.group(1).strip()
        preco = _to_float(m.group(2))
        dur = _to_int(m.group(3))
        return nome, preco, dur

    # nome preco
    m = re.match(r"^(.+?)\s+("+NUM+")\s*$", s, flags=re.I)
    if m:
        nome = m.group(1).strip()
        preco = _to_float(m.group(2))
        return nome, preco, None

    # nome somente
    return s, None, None

def parse_servico_falado(frase: str) -> Optional[dict]:
    """
    Entende frases do dono, do tipo:
      - "corte feminino 60 reais 40 minutos"
      - "escova 50 60"
      - "botox capilar 250 90 minutos"
    Retorna dict com nome, preco, duracao_min ou None.
    """
    if not frase:
        return None

    txt = frase.lower().strip()
    # remove palavras que não mudam nada
    txt = txt.replace("reais", "").replace("real", "").replace("r$", "")
    txt = txt.replace("minutos", "").replace("minuto", "").replace("min", "")

    # pega todos os números
    nums = re.findall(r"\d+(?:[.,]\d+)?", txt)
    if not nums:
        # tenta o formato mais técnico
        nome, preco, dur = _parse_item_servico(frase)
        return {
            "nome": nome,
            "preco": preco,
            "duracao_min": dur or 30,
        }

    # primeiro número = preço
    preco_txt = nums[0].replace(",", ".")
    try:
        preco = float(preco_txt)
    except Exception:
        preco = None

    duracao = None
    if len(nums) >= 2:
        try:
            duracao = int(float(nums[1]))
        except Exception:
            duracao = None

    # remove os números do texto pra sobrar o nome
    nome = txt
    for n in nums:
        nome = nome.replace(n, "")
    nome = " ".join(nome.split())

    if not nome:
        nome = "serviço"

    return {
        "nome": nome,
        "preco": preco,
        "duracao_min": duracao or 30,
    }

def parse_profissional_frase(frase: str) -> Tuple[str, Dict[str, Dict[str, float|int]]]:
    """
    Entrada:
      "cadastrar profissional Carla: corte=50/30, escova=45/40"
      "profissional Larissa faz manicure 30/30, pedicure 30/30, unha gel 70/90"
    Saída:
      nome = "Carla"
      servicos = { "corte": {"preco": 50.0, "duracao": 30}, "escova": {"preco":45.0, "duracao":40} }
    """
    txt = (frase or "").strip()

    # nome do profissional
    m_nome = re.search(
        r"(?:cadastrar|adicionar)?\s*profissional\s+([a-zA-ZÀ-ú ]+?)(?::|\s+faz\b|\s+servi[çc]os\b|$)",
        txt, re.I
    )
    nome = _norm(m_nome.group(1)) if m_nome else ""

    # trecho dos serviços
    m_serv_bloc = re.search(r"(?:faz|servi[çc]os|:)\s*(.+)$", txt, re.I)
    bloco = _norm(m_serv_bloc.group(1)) if m_serv_bloc else ""

    servicos: Dict[str, Dict[str, float|int]] = {}
    if bloco:
        # corta qualquer "preços:" legado (vamos parsear item a item)
        bloco = re.split(r"\bpre[çc]os?\s*:", bloco, flags=re.I)[0].strip()
        itens = _split_itens(bloco)
        for it in itens:
            nome_item, preco, dur = _parse_item_servico(it)
            if not nome_item:
                continue
            nome_norm = nome_item.strip().lower()
            if nome_norm not in servicos:
                servicos[nome_norm] = {}
            if preco is not None:
                servicos[nome_norm]["preco"] = float(preco)
            if dur is not None:
                servicos[nome_norm]["duracao"] = int(dur)

    return nome, servicos

# =========================================================
# --------------------- PERSISTÊNCIA ----------------------
# =========================================================

async def salvar_servico_negocio(user_id: str, nome: str, preco: Optional[float], duracao: Optional[int]):
    """
    Catálogo do negócio.
    Path: Clientes/{user_id}/ServicosNegocio/{Nome}
    """
    nome_fmt = nome.strip().title()
    payload = {
        "nome": nome_fmt,
        "preco": float(preco) if preco is not None else None,
        "duracao": int(duracao) if duracao is not None else None,
    }
    await salvar_dado_em_path(f"Clientes/{user_id}/ServicosNegocio/{nome_fmt}", payload)
    return payload

async def listar_servicos_negocio(user_id: str) -> dict:
    return await buscar_subcolecao(f"Clientes/{user_id}/ServicosNegocio") or {}

async def salvar_profissional(user_id: str, nome: str, servicos: Dict[str, Dict[str, float|int]]):
    """
    Salva:
      - servicos (lista)
      - precos (dict)
      - duracoes (dict)
      - servicos_detalhe (dict completo)
    """
    nome_fmt = nome.strip().title()
    servicos_lista = sorted(set(s.strip().title() for s in servicos.keys()))

    precos = {}
    duracoes = {}
    for s, det in servicos.items():
        if "preco" in det and det["preco"] is not None:
            precos[s] = float(det["preco"])
        if "duracao" in det and det["duracao"] is not None:
            duracoes[s] = int(det["duracao"])

    payload = {
        "nome": nome_fmt,
        "servicos": servicos_lista,
        "precos": {k: float(v) for k, v in precos.items()} if precos else {},
        "duracoes": {k: int(v) for k, v in duracoes.items()} if duracoes else {},
        "servicos_detalhe": servicos,
    }
    await salvar_dado_em_path(f"Clientes/{user_id}/Profissionais/{nome_fmt}", payload)
    return payload

# =========================================================
# -------------------- VALIDAÇÃO/RESUMO -------------------
# =========================================================

async def negocio_tem_profissionais(user_id: str) -> bool:
    profs = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais") or {}
    return len(profs) > 0

async def validar_configuracao(user_id: str) -> Tuple[bool, List[str]]:
    """
    Valida se TODOS os serviços de cada profissional têm PREÇO e DURAÇÃO.
    Retorna (ok, lista_de_problemas).
    """
    problemas: List[str] = []
    profs = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais") or {}
    if not profs:
        problemas.append("Nenhum profissional cadastrado.")
        return False, problemas

    for pid, p in profs.items():
        nome = p.get("nome") or pid
        servicos = p.get("servicos") or []
        precos = p.get("precos") or {}
        duracoes = p.get("duracoes") or {}
        detalhe = p.get("servicos_detalhe") or {}

        if not servicos and not detalhe:
            problemas.append(f"{nome}: sem serviços cadastrados.")
            continue

        # preferimos o detalhe; senão, validamos pelo par (servicos, precos, duracoes)
        base = set(detalhe.keys()) if detalhe else set(s.strip().lower() for s in servicos)

        for s in base:
            ok_preco = False
            ok_dur = False
            if detalhe and s in detalhe:
                ok_preco = "preco" in detalhe[s] and detalhe[s]["preco"] is not None
                ok_dur = "duracao" in detalhe[s] and detalhe[s]["duracao"] is not None
            else:
                ok_preco = s in {k.strip().lower() for k in precos.keys()}
                ok_dur   = s in {k.strip().lower() for k in duracoes.keys()}

            if not ok_preco or not ok_dur:
                problemas.append(f"{nome}: serviço '{s}' sem " +
                                 ("preço e duração." if (not ok_preco and not ok_dur)
                                  else ("preço." if not ok_preco else "duração.")))

    return (len(problemas) == 0), problemas

async def resumo_config(user_id: str) -> str:
    dados = await get_dados_negocio(user_id)
    servs = await listar_servicos_negocio(user_id)
    profs = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais") or {}

    linhas = ["🧭 *Resumo da configuração*"]
    linhas.append(f"• Etapa atual: {await get_etapa_config(user_id)}")

    # negócio
    linhas.append("\n🏪 Negócio:")
    linhas.append(f"• Tipo: {dados.get('tipo_negocio') or '—'}")
    linhas.append(f"• Nome: {dados.get('nome_negocio') or '—'}")
    linhas.append(f"• Estilo: {dados.get('estilo') or '—'}")

    # serviços
    linhas.append("\n💇 Serviços do negócio:")
    if servs:
        for sid, s in servs.items():
            nome = s.get("nome") or sid
            preco = s.get("preco")
            dur = s.get("duracao")
            linhas.append(
                f"• {nome} — "
                f"{('R$ {:.2f}'.format(preco)) if preco is not None else 'preço ?'} / "
                f"{str(dur)+'min' if dur is not None else 'duração ?'}"
            )
    else:
        linhas.append("• Nenhum serviço cadastrado ainda.")

    # profissionais
    linhas.append("\n👥 Profissionais:")
    if not profs:
        linhas.append("• Nenhum profissional cadastrado.")
    else:
        linhas.append(f"• Total: {len(profs)}")
        for pid, p in profs.items():
            nome = p.get("nome") or pid
            det = p.get("servicos_detalhe") or {}
            if not det:
                servs_p = p.get("servicos") or []
                linhas.append(f"• {nome}: {', '.join(servs_p) if servs_p else '—'}")
            else:
                itens = []
                for s, info in det.items():
                    preco = info.get("preco")
                    dur = info.get("duracao")
                    itens.append(
                        f"{s.title()} (R${preco:.2f}/{dur}min)" if (preco is not None and dur is not None)
                        else f"{s.title()} (completar dados)"
                    )
                linhas.append(f"• {nome}: " + ", ".join(itens))

    # validação geral
    ok, problemas = await validar_configuracao(user_id)
    if not ok:
        linhas.append("\n⚠️ Ajustes pendentes:")
        for p in problemas:
            linhas.append(f"• {p}")
    else:
        linhas.append("\n✅ Configuração completa para agendar com preços e durações.")

    return "\n".join(linhas)

# =========================================================
# --------------------- ONBOARDING FLOW -------------------
# =========================================================

ONBOARDING_INSTRUCOES = (
    "👋 Vamos configurar por etapas.\n\n"
    "1) Me diga o *tipo de negócio* (salão, clínica, estética...)\n"
    "2) Me diga o *nome do negócio*\n"
    "3) Escolha o *estilo* (formal ou casual)\n"
    "4) Depois me mande os *serviços* com preço e tempo, um por vez:\n"
    "   - corte feminino 60 reais 40 minutos\n"
    "   - escova 50 60 minutos\n"
    "5) E por fim os profissionais:\n"
    "   - cadastrar profissional Carla, faz corte feminino e escova\n\n"
    "A qualquer momento, diga *ver config* para eu mostrar o que já está salvo."
)

async def precisa_onboarding(user_id: str) -> bool:
    """
    True se ainda não entrou no fluxo ou se não há profissionais.
    """
    etapa = await get_etapa_config(user_id)
    if etapa != ETAPA_CONCLUIDO:
        return True
    if not await negocio_tem_profissionais(user_id):
        return True
    return False

def mensagem_onboarding() -> str:
    return ONBOARDING_INSTRUCOES

# =========================================================
# -------- PROCESSADOR DE TEXTO (TG e WHATSAPP) ----------
# =========================================================

async def processar_texto_cadastro(user_id: str, texto: str) -> Optional[str]:
    """
    Fluxo de configuração por etapas:
    0) negócio (tipo, nome, estilo)
    1) serviços do negócio (catálogo com preço e duração)
    2) profissionais que usam esses serviços
    3) concluído
    """
    if not texto:
        return None

    low = texto.strip().lower()

    # gatilhos para começar do zero
    if low in {
        "config", "configurar", "quero configurar",
        "configuração", "configuracao",
        "configurar meu salão", "configurar meu salao"
    }:
        await set_etapa_config(user_id, ETAPA_NEGOCIO)
        return (
            "🤖 Vou te configurar em etapas.\n\n"
            "1️⃣ Primeiro defino o que o seu negócio faz.\n"
            "2️⃣ Depois cadastramos o que você vende — os serviços com *preço e duração*.\n"
            "3️⃣ Por fim, ligo esses serviços nos profissionais.\n\n"
            "Assim, quando o cliente pedir um horário ou perguntar preço, já está tudo amarrado.\n\n"
            "Vamos começar?\n"
            "👉 Me diga o *tipo de negócio* (ex.: salão, barbearia, clínica, estética...)."
        )

    # ajuda
    if "ajuda config" in low:
        return mensagem_onboarding()

    # ver resumo
    if "ver config" in low or "ver configuração" in low or "ver configuracao" in low:
        return await resumo_config(user_id)

    # etapa atual
    etapa = await get_etapa_config(user_id)

    # =============== ETAPA 0: NEGÓCIO ==================
    if etapa == ETAPA_NEGOCIO:
        dados = await get_dados_negocio(user_id)

        if not dados.get("tipo_negocio"):
            await salvar_dados_negocio(user_id, tipo=texto)
            return (
                "👍 Tipo de negócio salvo.\n"
                "Agora me diga o *nome do negócio* (ex.: Studio da Ana, Clínica Vida...)."
            )

        if not dados.get("nome_negocio"):
            await salvar_dados_negocio(user_id, nome=texto)
            return (
                "✅ Nome salvo.\n"
                "Como você quer que eu fale? Responda com *formal* ou *casual*."
            )

        if not dados.get("estilo"):
            estilo = "casual" if "casual" in low else ("formal" if "formal" in low else texto)
            await salvar_dados_negocio(user_id, estilo=estilo)
            await set_etapa_config(user_id, ETAPA_SERVICOS)
            return (
                "🎯 Ótimo. Agora vamos cadastrar o que você faz.\n"
                "Me mande *um serviço por vez* com nome, preço e tempo.\n"
                "Ex.: `corte feminino 60 reais 40 minutos`.\n"
                "Quando terminar, diga *terminou*."
            )

        # fallback
        await set_etapa_config(user_id, ETAPA_SERVICOS)
        return "Vamos para os serviços. Mande algo como: `escova 50 60 minutos`."

    # =============== ETAPA 1: SERVIÇOS ==================
    if etapa == ETAPA_SERVICOS:
        if low in {"terminou", "acabou", "pode seguir"}:
            servs = await listar_servicos_negocio(user_id)
            if not servs:
                return "⚠️ Ainda não vi nenhum serviço. Manda pelo menos um, tipo: `corte feminino 60 reais 40 minutos`."
            await set_etapa_config(user_id, ETAPA_PROFISSIONAIS)
            return (
                "✅ Serviços salvos.\n"
                "Agora vamos cadastrar *quem atende*.\n"
                "Fale assim: `cadastrar profissional Carla, faz corte feminino e escova`.\n"
                "Pode mandar um por vez."
            )

        serv = parse_servico_falado(texto)
        if not serv:
            return (
                "⚠️ Não entendi o serviço.\n"
                "Manda assim: `corte feminino 60 reais 40 minutos` ou `escova 50 60`."
            )

        await salvar_servico_negocio(user_id, serv["nome"], serv["preco"], serv["duracao_min"])
        return (
            f"✅ Serviço salvo: {serv['nome'].title()} – "
            f"{'R$ {:.2f}'.format(serv['preco']) if serv['preco'] is not None else 'preço ?'} – "
            f"{serv['duracao_min']}min.\n"
            "Manda o próximo ou diga *terminou*."
        )

    # =============== ETAPA 2: PROFISSIONAIS =============
    if etapa == ETAPA_PROFISSIONAIS:
        if low in {"terminou", "acabou", "finalizou", "pode concluir"}:
            await set_etapa_config(user_id, ETAPA_CONCLUIDO)
            return (
                "✅ Profissionais cadastrados.\n"
                "⚙️ Configuração concluída.\n\n"
                "Agora o cliente já pode perguntar:\n"
                "• quanto custa corte feminino?\n"
                "• quem faz escova?\n"
                "• tem horário amanhã?\n\n"
                "Se quiser ver tudo o que está salvo diga: *ver config*."
            )

        nome, servs = parse_profissional_frase(texto)
        if not nome:
            return (
                "⚠️ Não entendi o nome do profissional.\n"
                "Ex.: `cadastrar profissional Carla, faz corte feminino e escova`."
            )

        # amarração com catálogo
        catalogo = await listar_servicos_negocio(user_id)
        catalogo_map = { (c.get("nome") or k).strip().lower(): c for k, c in catalogo.items() }

        servicos_filtrados: Dict[str, Dict[str, float | int]] = {}
        for nome_serv, info in servs.items():
            chave = nome_serv.strip().lower()
            if chave in catalogo_map:
                base = catalogo_map[chave]
                preco = info.get("preco") if info.get("preco") is not None else base.get("preco")
                dur = info.get("duracao") if info.get("duracao") is not None else base.get("duracao")
                servicos_filtrados[chave] = {"preco": preco, "duracao": dur}
            else:
                # serviço não está no catálogo, mas vamos salvar mesmo assim
                servicos_filtrados[chave] = {
                    "preco": info.get("preco"),
                    "duracao": info.get("duracao"),
                }

        payload = await salvar_profissional(user_id, nome, servicos_filtrados)

        det = payload.get("servicos_detalhe") or {}
        linhas = [f"✅ Profissional *{payload['nome']}* salvo:"]
        for s, info in det.items():
            preco = info.get("preco")
            dur = info.get("duracao")
            if preco is not None and dur is not None:
                linhas.append(f"• {s.title()} — R${preco:.2f}/{dur}min")
            else:
                linhas.append(f"• {s.title()} — completar preço/duração")

        linhas.append("\nManda o próximo profissional ou diga *terminou*.")
        return "\n".join(linhas)

    # =============== ETAPA 3: CONCLUÍDO ==================
    if etapa == ETAPA_CONCLUIDO:
        # já configurado, deixa seguir pro roteador
        return None

    return None
