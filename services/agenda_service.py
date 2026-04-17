# services/agenda_service.py

from __future__ import annotations

from datetime import datetime, timedelta, date
from typing import Any
from services.event_service_async import verificar_conflito_e_sugestoes_profissional

from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path, salvar_dado_em_path

def _normalizar_data_iso(data_iso: str) -> str:
    """
    Garante YYYY-MM-DD.
    Aceita:
    - YYYY-MM-DD
    - YYYY-MM-DDTHH:MM:SS
    """
    if not data_iso:
        raise ValueError("data_iso vazio")

    if "T" in data_iso:
        return datetime.fromisoformat(data_iso).strftime("%Y-%m-%d")

    return datetime.fromisoformat(f"{data_iso}T00:00:00").strftime("%Y-%m-%d")

def normalizar_lista_datas(datas: list[str] | None) -> list[str]:
    if not datas:
        return []

    return sorted({_normalizar_data_iso(d) for d in datas if d})


def _to_date(data_iso: str) -> date:
    return datetime.fromisoformat(f"{_normalizar_data_iso(data_iso)}T00:00:00").date()

def _minutos_para_hora(total_min: int) -> str:
    hh = total_min // 60
    mm = total_min % 60
    return f"{hh:02d}:{mm:02d}"

def _hora_para_minutos(hora_str: str | None) -> int | None:
    if not hora_str:
        return None

    try:
        hh, mm = map(int, str(hora_str).split(":"))

        if not (0 <= hh < 24 and 0 <= mm < 60):
            return None

        return hh * 60 + mm
    except Exception:
        return None


def horario_dentro_do_expediente(hora: str, inicio: str | None, fim: str | None) -> bool:
    """
    Retorna True se a hora estiver dentro do expediente.
    Considera faixa [inicio, fim), isto é:
    - 08:00 entra
    - 18:00 não entra se fim=18:00
    """
    h = _hora_para_minutos(hora)
    hi = _hora_para_minutos(inicio)
    hf = _hora_para_minutos(fim)

    if h is None or hi is None or hf is None:
        return False

    return hi <= h < hf


def intervalo_dentro_do_expediente(
    hora_inicio: str,
    duracao_min: int,
    inicio: str | None,
    fim: str | None
) -> bool:
    """
    Valida o intervalo inteiro, não só o horário inicial.
    """
    hi = _hora_para_minutos(hora_inicio)
    exp_ini = _hora_para_minutos(inicio)
    exp_fim = _hora_para_minutos(fim)

    if hi is None or exp_ini is None or exp_fim is None:
        return False

    hora_fim = hi + int(duracao_min or 0)

    return exp_ini <= hi and hora_fim <= exp_fim


async def obter_config_agenda(user_id: str) -> dict[str, Any]:
    """
    Busca configuração de agenda do tenant no caminho real do Firestore:
    Clientes/{user_id}/configuracao/agenda_funcionamento
    """
    path = f"Clientes/{user_id}/configuracao/agenda_funcionamento"
    doc = await buscar_dado_em_path(path) or {}

    agenda_padrao = doc.get("agenda_padrao") or {}
    excecoes_data = doc.get("excecoes_data") or {}

    print("🧪 CONFIG RAW:", doc, flush=True)
    print("🧪 CONFIG agenda_padrao:", agenda_padrao, flush=True)
    print("🧪 CONFIG excecoes_data:", excecoes_data, flush=True)

    return {
        "agenda_padrao": agenda_padrao,
        "excecoes_data": excecoes_data,
    }

async def obter_regra_agenda_da_data(user_id: str, data_iso: str) -> dict[str, Any]:
    """
    Resolve a regra final da agenda para uma data específica.

    Prioridade:
    1. excecao por data
    2. agenda semanal padrao

    Retorno:
    {
      "aberto": bool,
      "inicio": "HH:MM" | None,
      "fim": "HH:MM" | None,
      "origem": "excecao" | "padrao" | "fallback" | "erro",
      "data": "YYYY-MM-DD",
      "weekday": 0..6
    }
    """
    try:
        cfg = await obter_config_agenda(user_id)
        agenda_padrao = cfg.get("agenda_padrao") or {}
        excecoes_data = cfg.get("excecoes_data") or {}

        data_str = _normalizar_data_iso(data_iso)
        dt = _to_date(data_str)

        # Python: 0=segunda ... 6=domingo
        # Firebase do seu projeto: 0=domingo ... 6=sábado
        weekday_idx = (dt.weekday() + 1) % 7
        weekday_str = str(weekday_idx)

        # 1) excecao da data tem prioridade maxima
        if data_str in excecoes_data:
            reg = excecoes_data.get(data_str) or {}
            return {
                "aberto": bool(reg.get("aberto", False)),
                "inicio": reg.get("inicio"),
                "fim": reg.get("fim"),
                "origem": "excecao",
                "data": data_str,
                "weekday": weekday_idx,
            }

        # 2) agenda padrao semanal
        reg = agenda_padrao.get(weekday_str)
        if reg:
            return {
                "aberto": bool(reg.get("aberto", False)),
                "inicio": reg.get("inicio"),
                "fim": reg.get("fim"),
                "origem": "padrao",
                "data": data_str,
                "weekday": weekday_idx,
            }

        # 3) fallback conservador
        return {
            "aberto": False,
            "inicio": None,
            "fim": None,
            "origem": "fallback",
            "data": data_str,
            "weekday": weekday_idx,
        }

    except Exception as e:
        print(f"❌ [agenda_service] erro em obter_regra_agenda_da_data: {e}", flush=True)
        return {
            "aberto": False,
            "inicio": None,
            "fim": None,
            "origem": "erro",
            "data": None,
            "weekday": None,
        }


async def validar_data_funcionamento(user_id: str, data_iso: str) -> dict[str, Any]:
    """
    Valida se a data pode receber agendamento.
    """
    regra = await obter_regra_agenda_da_data(user_id, data_iso)

    if not regra.get("aberto"):
        return {
            "permitido": False,
            "motivo": "fechado_na_data",
            "regra": regra,
        }

    return {
        "permitido": True,
        "motivo": None,
        "regra": regra,
    }


async def obter_janela_funcionamento(
    user_id: str,
    data_str: str,
    profissional: str | None = None
) -> dict[str, Any]:
    """
    Retorna a janela real de funcionamento considerando:

    1) agenda do salão
    2) exceções do salão
    3) agenda do profissional (se existir)
    4) exceções do profissional (se existir)
    5) fallback automático do profissional para o salão

    Regras:
    - Se o salão estiver fechado, nada abaixo importa.
    - Se houver exceção do salão para a data, ela tem prioridade sobre o padrão do salão.
    - Se houver profissional e ele tiver agenda própria, ela é aplicada.
    - Se o profissional não tiver agenda própria, herda do salão.
    - Se houver exceção do profissional para a data, ela tem prioridade sobre a agenda base dele.
    """

    from datetime import datetime
    from services.firebase_service_async import buscar_dado_em_path, buscar_subcolecao

    # =========================================================
    # 1) LER AGENDA DO SALÃO
    # =========================================================
    path_salao = f"Clientes/{user_id}/configuracao/agenda_funcionamento"
    cfg_salao = await buscar_dado_em_path(path_salao) or {}

    agenda_padrao_salao = cfg_salao.get("agenda_padrao") or {}
    excecoes_salao = cfg_salao.get("excecoes_data") or {}

    print(f"🧪 [JANELA] cfg_salao keys={list(cfg_salao.keys())}", flush=True)
    print(f"🧪 [JANELA] agenda_padrao_salao={agenda_padrao_salao}", flush=True)
    print(f"🧪 [JANELA] excecoes_salao={excecoes_salao}", flush=True)

    # =========================================================
    # 2) DESCOBRIR DIA DA SEMANA DA DATA
    # =========================================================
    # Python weekday(): segunda=0 ... domingo=6
    # Seu Firebase aparentemente usa:
    # 0..5 abertos e 6 fechado
    # Então precisamos respeitar como seu sistema já opera hoje.
    # Se sua agenda atual já funciona, manteremos a mesma convenção abaixo.
    dt = datetime.fromisoformat(data_str)
    weekday_str = str(dt.weekday())

    # =========================================================
    # 3) MONTAR REGRA BASE DO SALÃO
    # =========================================================
    reg_salao = agenda_padrao_salao.get(weekday_str) or {}

    aberto_salao = reg_salao.get("aberto", False)
    inicio_salao = reg_salao.get("inicio")
    fim_salao = reg_salao.get("fim")

    regra_salao_final = {
        "aberto": aberto_salao,
        "inicio": inicio_salao,
        "fim": fim_salao,
        "origem": "agenda_padrao_salao"
    }

    # =========================================================
    # 4) EXCEÇÃO DO SALÃO TEM PRIORIDADE SOBRE O PADRÃO
    # =========================================================
    if data_str in excecoes_salao:
        exc_salao = excecoes_salao.get(data_str) or {}

        regra_salao_final = {
            "aberto": exc_salao.get("aberto", False),
            "inicio": exc_salao.get("inicio"),
            "fim": exc_salao.get("fim"),
            "origem": "excecao_salao",
            "tipo": exc_salao.get("tipo"),
            "motivo": exc_salao.get("motivo")
        }

    print(f"🧪 [JANELA] regra_salao_final={regra_salao_final}", flush=True)

    # =========================================================
    # 5) SE O SALÃO ESTIVER FECHADO, PARA TUDO
    # =========================================================
    if not regra_salao_final.get("aberto"):
        return {
            "aberto": False,
            "inicio": None,
            "fim": None,
            "origem": regra_salao_final.get("origem"),
            "tipo": regra_salao_final.get("tipo"),
            "motivo": regra_salao_final.get("motivo")
        }

    # =========================================================
    # 6) SE NÃO HOUVER PROFISSIONAL, RETORNA REGRA DO SALÃO
    # =========================================================
    if not profissional:
        return {
            "aberto": True,
            "inicio": regra_salao_final.get("inicio"),
            "fim": regra_salao_final.get("fim"),
            "origem": regra_salao_final.get("origem"),
            "tipo": regra_salao_final.get("tipo"),
            "motivo": regra_salao_final.get("motivo")
        }

    # =========================================================
    # 7) LER PROFISSIONAIS
    # =========================================================
    profissionais = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais") or {}

    # tenta chave direta
    dados_prof = profissionais.get(profissional)

    # fallback case-insensitive
    if not dados_prof:
        prof_norm = (profissional or "").strip().lower()
        for nome_prof, dados in profissionais.items():
            if (nome_prof or "").strip().lower() == prof_norm:
                dados_prof = dados
                break

    # se não encontrou profissional, não assume disponibilidade
    if not dados_prof:
        print(f"⚠️ [JANELA] profissional '{profissional}' não encontrado.", flush=True)
        return {
            "aberto": False,
            "inicio": None,
            "fim": None,
            "origem": "profissional_nao_encontrado",
            "tipo": "cadastro_invalido",
            "motivo": "profissional_nao_encontrado"
        }

    # =========================================================
    # 8) AGENDA DO PROFISSIONAL
    # =========================================================
    agenda_prof = dados_prof.get("agenda_funcionamento") or {}
    agenda_padrao_prof = agenda_prof.get("agenda_padrao") or {}

    excecoes_prof = await buscar_subcolecao(
        f"Clientes/{user_id}/Profissionais/{profissional}/AgendaExcecoes"
    ) or {}

    print(f"🧪 [JANELA] profissional={profissional}", flush=True)
    print(f"🧪 [JANELA] agenda_padrao_prof={agenda_padrao_prof}", flush=True)
    print(f"🧪 [JANELA] excecoes_prof={excecoes_prof}", flush=True)

    # se o profissional não tiver agenda própria, herda do salão
    if not agenda_padrao_prof:
        return {
            "aberto": True,
            "inicio": regra_salao_final.get("inicio"),
            "fim": regra_salao_final.get("fim"),
            "origem": "fallback_salao_sem_agenda_profissional",
            "tipo": regra_salao_final.get("tipo"),
            "motivo": regra_salao_final.get("motivo")
        }

    reg_prof = agenda_padrao_prof.get(weekday_str) or {}

    regra_prof_final = {
        "aberto": reg_prof.get("aberto", False),
        "inicio": reg_prof.get("inicio"),
        "fim": reg_prof.get("fim"),
        "origem": "agenda_padrao_profissional"
    }

    # =========================================================
    # 9) EXCEÇÃO DO PROFISSIONAL SOBRESCREVE A BASE DELE
    # =========================================================
    if data_str in excecoes_prof:
        exc_prof = excecoes_prof.get(data_str) or {}

        if exc_prof.get("tipo") == "bloqueado" and exc_prof.get("ativo") is True:
            return {
                "aberto": False,
                "inicio": None,
                "fim": None,
                "origem": "excecao_profissional",
                "tipo": exc_prof.get("tipo"),
                "motivo": exc_prof.get("motivo"),
            }
        else:
            regra_prof_final = {
                "aberto": exc_prof.get("aberto", True),
                "inicio": exc_prof.get("inicio"),
                "fim": exc_prof.get("fim"),
                "origem": "excecao_profissional",
                "tipo": exc_prof.get("tipo"),
                "motivo": exc_prof.get("motivo"),
            }

    print(f"🧪 [JANELA] regra_prof_final={regra_prof_final}", flush=True)

    # =========================================================
    # 10) PROFISSIONAL FECHADO
    # =========================================================
    if not regra_prof_final.get("aberto"):
        return {
            "aberto": False,
            "inicio": None,
            "fim": None,
            "origem": regra_prof_final.get("origem"),
            "tipo": regra_prof_final.get("tipo"),
            "motivo": regra_prof_final.get("motivo")
        }

    # =========================================================
    # 11) INTERSEÇÃO SALÃO x PROFISSIONAL
    # O horário real deve caber nos dois.
    # =========================================================
    inicio_salao = regra_salao_final.get("inicio")
    fim_salao = regra_salao_final.get("fim")
    inicio_prof = regra_prof_final.get("inicio")
    fim_prof = regra_prof_final.get("fim")

    # 🔒 protege contra agenda inválida/incompleta
    if not inicio_salao or not fim_salao:
        return {
            "aberto": False,
            "inicio": None,
            "fim": None,
            "origem": "agenda_salao_invalida",
            "tipo": "sem_janela_valida",
            "motivo": "agenda_salao_incompleta"
        }

    if not inicio_prof or not fim_prof:
        return {
            "aberto": False,
            "inicio": None,
            "fim": None,
            "origem": "agenda_profissional_invalida",
            "tipo": "sem_janela_valida",
            "motivo": "agenda_profissional_incompleta"
        }

    ini_salao_min = _hora_para_minutos(inicio_salao)
    fim_salao_min = _hora_para_minutos(fim_salao)
    ini_prof_min = _hora_para_minutos(inicio_prof)
    fim_prof_min = _hora_para_minutos(fim_prof)

    if None in (ini_salao_min, fim_salao_min, ini_prof_min, fim_prof_min):
        return {
            "aberto": False,
            "inicio": None,
            "fim": None,
            "origem": "horario_invalido",
            "tipo": "sem_janela_valida",
            "motivo": "erro_conversao_horario"
        }

    inicio_final_min = max(ini_salao_min, ini_prof_min)
    fim_final_min = min(fim_salao_min, fim_prof_min)

    # se a interseção ficar inválida, trata como fechado
    if inicio_final_min >= fim_final_min:
        return {
            "aberto": False,
            "inicio": None,
            "fim": None,
            "origem": "intersecao_salao_profissional_vazia",
            "tipo": "sem_janela_valida",
            "motivo": "sem_sobreposicao"
        }

    return {
        "aberto": True,
        "inicio": _minutos_para_hora(inicio_final_min),
        "fim": _minutos_para_hora(fim_final_min),
        "origem": "intersecao_salao_profissional",
        "tipo": None,
        "motivo": None
    }

async def validar_horario_funcionamento(
    user_id: str,
    data_iso: str,
    hora_inicio: str,
    duracao_min: int,
    profissional: str | None = None
) -> dict[str, Any]:
    """
    Valida se o horário e o intervalo cabem na janela real da data.

    A validação considera:
    1) agenda e exceções do salão
    2) agenda e exceções do profissional
    3) interseção final entre salão e profissional
    """

    regra = await obter_janela_funcionamento(
        user_id=user_id,
        data_str=data_iso,
        profissional=profissional
    )
    print("🧪 AGENDA JANELA REAL:", regra, flush=True)

    if not regra.get("aberto"):
        return {
            "permitido": False,
            "motivo": "fechado_na_data",
            "regra": regra,
        }

    inicio = regra.get("inicio")
    fim = regra.get("fim")

    if not intervalo_dentro_do_expediente(hora_inicio, duracao_min, inicio, fim):
        return {
            "permitido": False,
            "motivo": "fora_do_expediente",
            "regra": regra,
        }

    return {
        "permitido": True,
        "motivo": None,
        "regra": regra,
    }

async def proxima_data_permitida(
    user_id: str,
    data_iso: str,
    profissional: str | None = None,
    limite_dias: int = 30
) -> str | None:
    """
    Retorna a próxima data aberta, respeitando exceções e agenda semanal.
    """
    try:
        base = _to_date(data_iso)

        for i in range(1, limite_dias + 1):
            candidato = base + timedelta(days=i)
            data_str = candidato.strftime("%Y-%m-%d")

            janela = await obter_janela_funcionamento(
                user_id=user_id,
                data_str=data_str,
                profissional=profissional
            )
            if janela.get("aberto"):
                return data_str

        return None

    except Exception as e:
        print(f"❌ [agenda_service] erro em proxima_data_permitida: {e}", flush=True)
        return None


async def proximo_horario_valido_no_dia(
    user_id: str,
    data_iso: str,
    duracao_min: int,
    profissional: str | None = None,
    grade_minutos: int = 10
) -> str | None:
    """
    Procura o primeiro horário válido dentro do expediente.
    Não verifica conflito com eventos; só expediente.
    """
    try:
        regra = await obter_janela_funcionamento(
            user_id=user_id,
            data_str=data_iso,
            profissional=profissional
        )
        if not regra.get("aberto"):
            return None

        inicio = regra.get("inicio")
        fim = regra.get("fim")

        min_ini = _hora_para_minutos(inicio)
        min_fim = _hora_para_minutos(fim)

        if min_ini is None or min_fim is None:
            return None

        atual = min_ini
        while atual + duracao_min <= min_fim:
            hh = atual // 60
            mm = atual % 60
            hora = f"{hh:02d}:{mm:02d}"

            if intervalo_dentro_do_expediente(hora, duracao_min, inicio, fim):
                return hora

            atual += grade_minutos

        return None

    except Exception as e:
        print(f"❌ [agenda_service] erro em proximo_horario_valido_no_dia: {e}", flush=True)
        return None

async def resolver_fora_do_expediente(
    user_id: str,
    data_iso: str,
    hora_inicio: str,
    duracao_min: int,
    servico: str,
    profissional: str | None = None,
    grade_minutos: int = 10,
) -> dict[str, Any]:
    """
    Resolve apenas o caso em que o horário pedido está fora do expediente.
    """
    try:
        print(
            f"🧪 [FORA_EXP] entrada | user_id={user_id} | data_iso={data_iso} | "
            f"hora_inicio={hora_inicio} | duracao_min={duracao_min} | "
            f"servico={servico} | profissional={profissional}",
            flush=True
        )

        regra = await obter_janela_funcionamento(
            user_id=user_id,
            data_str=data_iso,
            profissional=profissional
        )
        print(f"🧪 [FORA_EXP] regra={regra}", flush=True)

        if not regra.get("aberto"):
            print("⚠️ [FORA_EXP] dia fechado", flush=True)
            return {
                "ok": False,
                "tipo": "sem_opcao",
                "horario": None,
                "data_hora": None,
                "mensagem": None,
            }

        inicio = regra.get("inicio")
        fim = regra.get("fim")

        min_ini = _hora_para_minutos(inicio)
        min_fim = _hora_para_minutos(fim)
        min_ref = _hora_para_minutos(hora_inicio)

        print(
            f"🧪 [FORA_EXP] min_ini={min_ini} | min_fim={min_fim} | min_ref={min_ref}",
            flush=True
        )

        if min_ini is None or min_fim is None or min_ref is None:
            print("⚠️ [FORA_EXP] erro na conversão de horários", flush=True)
            return {
                "ok": False,
                "tipo": "sem_opcao",
                "horario": None,
                "data_hora": None,
                "mensagem": None,
            }

        candidatos = []
        atual = min_ini

        while atual + duracao_min <= min_fim:
            hh = atual // 60
            mm = atual % 60
            hora = f"{hh:02d}:{mm:02d}"

            print(
                f"🧪 [FORA_EXP LOOP] hora={hora} | valido={intervalo_dentro_do_expediente(hora, duracao_min, inicio, fim)}",
                flush=True
            )

            if intervalo_dentro_do_expediente(hora, duracao_min, inicio, fim):
                distancia = abs(atual - min_ref)
                candidatos.append((distancia, atual, hora))

            atual += grade_minutos

        print(f"🧪 [FORA_EXP] candidatos={candidatos[:10]}", flush=True)

        if not candidatos:
            print("⚠️ [FORA_EXP] nenhum candidato gerado", flush=True)
            return {
                "ok": False,
                "tipo": "sem_opcao",
                "horario": None,
                "data_hora": None,
                "mensagem": None,
            }

        candidatos.sort(key=lambda x: (x[0], x[1]))

        for _, _, hora_candidata in candidatos:
            print(
                f"🧪 [FORA_EXP] testando hora={hora_candidata} | profissional={profissional}",
                flush=True
            )

            # sem profissional ainda → retorna direto o mais próximo
            if not (profissional or "").strip():
                print(
                    f"✅ [FORA_EXP] sugerindo (sem profissional) {hora_candidata}",
                    flush=True
                )
                return {
                    "ok": True,
                    "tipo": "horario_sugerido",
                    "horario": hora_candidata,
                    "data_hora": f"{data_iso}T{hora_candidata}:00",
                    "mensagem": None,
                }

            resultado = await verificar_conflito_e_sugestoes_profissional(
                user_id=user_id,
                data=data_iso,
                hora_inicio=hora_candidata,
                duracao_min=duracao_min,
                profissional=profissional,
                servico=servico,
            )

            print(f"🧪 [FORA_EXP] resultado_conflito={resultado}", flush=True)

            if not resultado.get("conflito"):
                print(
                    f"✅ [FORA_EXP] sugerindo (livre) {hora_candidata}",
                    flush=True
                )
                return {
                    "ok": True,
                    "tipo": "horario_sugerido",
                    "horario": hora_candidata,
                    "data_hora": f"{data_iso}T{hora_candidata}:00",
                    "mensagem": None,
                }

        print("⚠️ [FORA_EXP] nenhum horário passou na validação final", flush=True)

        return {
            "ok": False,
            "tipo": "sem_opcao",
            "horario": None,
            "data_hora": None,
            "mensagem": None,
        }

    except Exception as e:
        print(f"❌ [agenda_service] erro em resolver_fora_do_expediente: {e}", flush=True)
        return {
            "ok": False,
            "tipo": "sem_opcao",
            "horario": None,
            "data_hora": None,
            "mensagem": None,
        }

async def bloquear_datas_agenda_salao(
    user_id: str,
    datas: list[str],
    motivo: str = "fechado"
) -> bool:

    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    path = f"Clientes/{user_id}/configuracao/agenda_funcionamento"

    cfg = await buscar_dado_em_path(path) or {}
    excecoes = cfg.get("excecoes_data") or {}

    for data in datas:
        excecoes[data] = {
            "tipo": "bloqueio_total",
            "aberto": False,
            "inicio": None,
            "fim": None,
            "motivo": motivo,
        }

    await atualizar_dado_em_path(path, {"excecoes_data": excecoes})

    return True

async def definir_janela_especial_agenda_salao(
    user_id: str,
    datas: list[str],
    inicio: str,
    fim: str,
    motivo: str = "expediente_reduzido"
) -> bool:

    path = f"Clientes/{user_id}/configuracao/agenda_funcionamento"
    cfg = await buscar_dado_em_path(path) or {}

    excecoes = cfg.get("excecoes_data") or {}

    for data in datas:
        excecoes[data] = {
            "tipo": "janela_especial",
            "aberto": True,
            "inicio": inicio,
            "fim": fim,
            "motivo": motivo,
        }

    await atualizar_dado_em_path(path, {"excecoes_data": excecoes})
    return True

async def bloquear_agenda_profissional(
    user_id: str,
    profissional: str,
    datas: list[str],
    motivo: str = "indisponivel"
) -> bool:
    try:
        datas = normalizar_lista_datas(datas)
        profissional = (profissional or "").strip()

        if not user_id or not profissional or not datas:
            return False

        for data in datas:
            path = f"Clientes/{user_id}/Profissionais/{profissional}/AgendaExcecoes/{data}"
            payload = {
                "data": data,
                "tipo": "bloqueado",
                "motivo": motivo,
                "ativo": True,
                "profissional": profissional,
            }
            await salvar_dado_em_path(path, payload)

        return True

    except Exception as e:
        print(f"❌ [bloquear_agenda_profissional] erro: {e}", flush=True)
        return False

async def definir_janela_especial_profissional(
    user_id: str,
    profissional: str,
    datas: list[str],
    inicio: str,
    fim: str,
    motivo: str = "expediente_reduzido"
) -> bool:
    try:
        datas = normalizar_lista_datas(datas)
        profissional = (profissional or "").strip()
        inicio = (inicio or "").strip()
        fim = (fim or "").strip()

        if not user_id or not profissional or not datas or not inicio or not fim:
            return False

        for data in datas:
            path = f"Clientes/{user_id}/Profissionais/{profissional}/AgendaExcecoes/{data}"
            payload = {
                "data": data,
                "tipo": "janela_especial",
                "inicio": inicio,
                "fim": fim,
                "motivo": motivo,
                "ativo": True,
                "profissional": profissional,
            }
            await salvar_dado_em_path(path, payload)

        return True

    except Exception as e:
        print(f"❌ [definir_janela_especial_profissional] erro: {e}", flush=True)
        return False