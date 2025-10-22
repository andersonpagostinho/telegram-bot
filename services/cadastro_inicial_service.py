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

async def salvar_profissional(user_id: str, nome: str, servicos: Dict[str, Dict[str, float|int]]):
    """
    Salva:
      - servicos (lista)
      - precos (dict)
      - duracoes (dict)      <= NOVO
      - servicos_detalhe (dict completo) <= NOVO
    """
    nome_fmt = nome.strip().title()
    servicos_lista = sorted(set(s.strip().title() for s in servicos.keys()))

    precos = {}
    duracoes = {}
    for s, det in servicos.items():
        if "preco" in det:
            precos[s] = float(det["preco"])
        if "duracao" in det:
            duracoes[s] = int(det["duracao"])

    payload = {
        "nome": nome_fmt,
        "servicos": servicos_lista,              # compat
        "precos": {k: float(v) for k, v in precos.items()} if precos else {},   # compat
        "duracoes": {k: int(v) for k, v in duracoes.items()} if duracoes else {},  # novo
        "servicos_detalhe": servicos,            # novo (fonte da verdade)
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
                ok_preco = "preco" in detalhe[s]
                ok_dur = "duracao" in detalhe[s]
            else:
                ok_preco = s in {k.strip().lower() for k in precos.keys()}
                ok_dur   = s in {k.strip().lower() for k in duracoes.keys()}

            if not ok_preco or not ok_dur:
                problemas.append(f"{nome}: serviço '{s}' sem " +
                                 ("preço e duração." if (not ok_preco and not ok_dur)
                                  else ("preço." if not ok_preco else "duração.")))

    return (len(problemas) == 0), problemas

async def resumo_config(user_id: str) -> str:
    profs = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais") or {}
    if not profs:
        return "Ainda não há profissionais cadastrados."

    linhas = [f"👥 Profissionais: {len(profs)}"]
    for pid, p in profs.items():
        nome = p.get("nome") or pid
        det = p.get("servicos_detalhe") or {}
        if not det:
            # retrocompat.
            servs = p.get("servicos") or []
            precos = p.get("precos") or {}
            durs = p.get("duracoes") or {}
            itens = []
            for s in servs:
                k = s.strip().lower()
                preco = precos.get(k)
                dur = durs.get(k)
                itens.append(f"{s} ({'R$'+str(preco) if preco is not None else 'preço ?'} / {str(dur)+'min' if dur is not None else 'duração ?'})")
            linhas.append(f"• {nome}: " + (", ".join(itens) if itens else "—"))
        else:
            itens = []
            for s, info in det.items():
                preco = info.get("preco")
                dur = info.get("duracao")
                itens.append(f"{s.title()} (R${preco:.2f}/{dur}min)" if (preco is not None and dur is not None)
                            else f"{s.title()} ({'R$'+str(preco) if preco is not None else 'preço ?'} / {str(dur)+'min' if dur is not None else 'duração ?'})")
            linhas.append(f"• {nome}: " + (", ".join(itens) if itens else "—"))
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
    "👋 Bem-vindo! Antes de começar a agendar, precisamos configurar seu negócio.\n\n"
    "Você pode *falar* ou *digitar* no formato abaixo (funciona no WhatsApp e no Telegram):\n\n"
    "• *Cadastrar profissional Carla: corte=50/30, escova=45/40*\n"
    "• *Profissional Larissa faz manicure 30/30, pedicure 30/30, unha gel 70/90*\n\n"
    "_Formato_: `serviço = preço / duração_em_min`  (aceita também `serviço preço duração`)\n"
    "Ex.: `corte=50/30` ou `corte 50 30`.\n\n"
    "Depois, envie *VER CONFIG* para revisar o que já foi salvo."
)

async def precisa_onboarding(user_id: str) -> bool:
    """
    True se não há profissionais ou se há problemas de preço/duração.
    """
    if not await negocio_tem_profissionais(user_id):
        return True
    ok, _ = await validar_configuracao(user_id)
    return not ok

def mensagem_onboarding() -> str:
    return ONBOARDING_INSTRUCOES

# =========================================================
# -------- PROCESSADOR DE TEXTO (TG e WHATSAPP) ----------
# =========================================================

async def processar_texto_cadastro(user_id: str, texto: str) -> Optional[str]:
    """
    Processa mensagens de configuração vindas do WhatsApp ou Telegram.
    Retorna uma resposta textual (para enviar no canal correspondente) ou None se não processar.
    Comandos reconhecidos:
      - "cadastrar profissional ..." / "profissional ..."
      - "ver config"  (mostra resumo)
      - "ajuda config" (mostra instruções)
    """
    if not texto:
        return None

    low = texto.strip().lower()

    # ajuda
    if "ajuda config" in low or low in {"config", "configurar", "configuração", "configuracao"}:
        return mensagem_onboarding()

    # ver resumo
    if "ver config" in low or "ver configuração" in low or "ver configuracao" in low:
        return await resumo_config(user_id)

    # gatilhos de cadastro
    if ("cadastrar profissional" in low) or ("adicionar profissional" in low) or low.startswith("profissional "):
        nome, servs = parse_profissional_frase(texto)
        if not nome:
            return "⚠️ Não entendi o nome do profissional. Ex.: *Cadastrar profissional Carla: corte=50/30, escova=45/40*"
        if not servs:
            return "⚠️ Não encontrei serviços válidos. Use o formato `serviço=preço/duração` (ex.: `corte=50/30`)."

        payload = await salvar_profissional(user_id, nome, servs)

        det = payload.get("servicos_detalhe") or {}
        linhas = [f"✅ Profissional *{payload['nome']}* salvo:"]
        for s, info in det.items():
            preco = info.get("preco")
            dur = info.get("duracao")
            linhas.append(f"• {s.title()} — R${preco:.2f}/{dur}min" if (preco is not None and dur is not None)
                         else f"• {s.title()} — {'R$'+str(preco) if preco is not None else 'preço ?'}/{'{0}min'.format(dur) if dur is not None else 'duração ?'}")

        ok, problemas = await validar_configuracao(user_id)
        if not ok:
            linhas.append("\n⚠️ Falta completar:")
            for p in problemas:
                linhas.append(f"• {p}")
            linhas.append("\nEnvie novos dados no mesmo formato para complementar.")

        linhas.append("\nDigite *VER CONFIG* para revisar tudo.")
        return "\n".join(linhas)

    # se não reconheceu nada específico de configuração
    return None
