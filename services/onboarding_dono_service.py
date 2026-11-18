# Serviço de Onboarding do Dono
# Responsabilidade: Guiar dono através de onboarding conversacional
# Sem salvar catálogo/agenda na sessão - apenas estado de progresso
# Dados permanentes salvos em Firestore em Configuracao/negocio

import asyncio
from datetime import datetime, timedelta
import pytz
import hashlib
import json
import uuid
import time
from services.identidade_service import criar_ator_dono, normalizar_actor_id
from services.firestore_client import get_db
from services.cadastro_inicial_service import salvar_profissional

# Estados do onboarding
ETAPAS_ONBOARDING = [
    "nome_negocio",
    "segmento",
    "endereco",
    "agenda_padrao",
    "primeiro_profissional",
    "canal_primeiro_profissional",
    "jornada_primeiro_profissional",  # FASE 2: perguntar jornada individual
    "primeiro_servico",
    "duracao_primeiro_servico",
    "confirmacao_dados",
    "teste_agendamento",
    "completo"
]

INDICE_ETAPAS = {etapa: idx for idx, etapa in enumerate(ETAPAS_ONBOARDING)}

# Constants for idempotent operations
OPERATION_LEASE_SECONDS = 300  # 5 minutes
MAX_ATTEMPT_COUNT = 3
BACKOFF_MULTIPLIER = 100  # milliseconds


def _calcular_draft_hash_sha256(draft_data: dict) -> str:
    """
    Calcula hash SHA-256 determinístico do draft com JSON canônico.

    Args:
        draft_data: Dict com dados do draft

    Returns:
        String hexadecimal do hash SHA-256
    """
    # Extrair campos relevantes em ordem determinística
    dados_hash = {
        "dias": sorted(draft_data.get("dias", [])),
        "horarios": draft_data.get("horarios", {}),
        "agenda_estruturada": draft_data.get("agenda_estruturada", {})
    }

    # JSON canônico: sort_keys + compact separators
    json_str = json.dumps(dados_hash, sort_keys=True, separators=(',', ':'), ensure_ascii=True)

    # SHA-256
    hash_obj = hashlib.sha256(json_str.encode('utf-8'))
    return hash_obj.hexdigest()


def _gerar_operation_owner_id() -> str:
    """Gera ID único para esta execução (UUID)."""
    return str(uuid.uuid4())


def _calcular_lease_expiracao() -> str:
    """Calcula timestamp de expiração do lease (5 minutos no futuro)."""
    expiracao = datetime.now(pytz.UTC) + timedelta(seconds=OPERATION_LEASE_SECONDS)
    return expiracao.isoformat()


async def _criar_agenda_funcionamento_firestore(tenant_id: str, agenda_padrao_str: str = None, agenda_padrao_dict: dict = None) -> None:
    """
    Cria documento de configuração de agenda_funcionamento no Firestore.

    Suporta dois formatos:
    1. agenda_padrao_dict: Estrutura completa com horários por dia
       {"0": {"aberto": True, "inicio": "09:00", "fim": "18:00"}, ...}
    2. agenda_padrao_str: String simples "inicio-fim" (compatibilidade legada)

    Args:
        tenant_id: ID do tenant
        agenda_padrao_str: String formato "inicio-fim", ex: "9:00-18:00" (opcional)
        agenda_padrao_dict: Dict com estrutura completa (opcional)

    Raises:
        ValueError: Se formato inválido ou Firestore falhar
    """
    try:
        if agenda_padrao_dict:
            # Novo formato: estrutura completa
            if not isinstance(agenda_padrao_dict, dict):
                raise ValueError("agenda_padrao_dict deve ser um dict")

            # Validar que tem dias
            if not any(agenda_padrao_dict.get(str(i), {}).get("aberto") for i in range(7)):
                raise ValueError("Nenhum dia aberto configurado")

            agenda_config = {
                "agenda_padrao": agenda_padrao_dict,
                "excecoes_data": {}
            }

            print(f"[OK] Agenda funcionamento criada para tenant {tenant_id} (from dict)", flush=True)

        elif agenda_padrao_str:
            # Formato legado: string simples
            partes = agenda_padrao_str.split("-")
            if len(partes) != 2:
                raise ValueError(f"Formato inválido: esperado 'inicio-fim', recebido '{agenda_padrao_str}'")

            inicio_str = partes[0].strip()
            fim_str = partes[1].strip()

            # Normalizar para HH:MM
            if inicio_str.count(":") == 0:
                inicio_str = f"{inicio_str}:00"
            if fim_str.count(":") == 0:
                fim_str = f"{fim_str}:00"

            # Validar formato básico
            if not _validar_formato_hora(inicio_str) or not _validar_formato_hora(fim_str):
                raise ValueError(f"Horários inválidos: inicio='{inicio_str}', fim='{fim_str}'")

            # Normalizar para HH:MM (com zero à esquerda)
            inicio_str = _normalizar_hora(inicio_str)
            fim_str = _normalizar_hora(fim_str)

            # Criar configuração com padrão: seg-sáb aberto, domingo fechado
            agenda_config = {
                "agenda_padrao": {
                    "0": {"aberto": True, "inicio": inicio_str, "fim": fim_str},   # segunda
                    "1": {"aberto": True, "inicio": inicio_str, "fim": fim_str},   # terça
                    "2": {"aberto": True, "inicio": inicio_str, "fim": fim_str},   # quarta
                    "3": {"aberto": True, "inicio": inicio_str, "fim": fim_str},   # quinta
                    "4": {"aberto": True, "inicio": inicio_str, "fim": fim_str},   # sexta
                    "5": {"aberto": True, "inicio": inicio_str, "fim": fim_str},   # sábado
                    "6": {"aberto": False}                                         # domingo
                },
                "excecoes_data": {}
            }

            print(f"[OK] Agenda funcionamento criada para tenant {tenant_id}: {inicio_str}-{fim_str}", flush=True)
        else:
            raise ValueError("agenda_padrao_str ou agenda_padrao_dict obrigatório")

        def salvar():
            config_ref = get_db().collection("Clientes").document(tenant_id)\
                .collection("configuracao").document("agenda_funcionamento")
            config_ref.set(agenda_config)

        await asyncio.to_thread(salvar)

    except Exception as e:
        print(f"[ERRO] Criar agenda_funcionamento: {e}", flush=True)
        raise


def _normalizar_hora(hora_str: str) -> str:
    """
    Normaliza hora para formato HH:MM.

    Args:
        hora_str: String como "9:00" ou "09:00"

    Returns:
        String normalizada como "09:00"
    """
    partes = hora_str.split(":")
    horas = partes[0].zfill(2)
    minutos = partes[1].zfill(2)
    return f"{horas}:{minutos}"


def _validar_formato_hora(hora_str: str) -> bool:
    """
    Valida se string está em formato H:MM ou HH:MM (sem espaços).

    Rejeita:
    - None ou tipos não-string
    - Espaços externos ou internos
    - Componentes não-numéricos
    - Horas fora de 00-23
    - Minutos fora de 00-59
    - Componentes com menos de 1 ou mais de 2 dígitos

    Args:
        hora_str: String como "9:00", "09:00" ou "18:30"

    Returns:
        True se válido (formato H:MM ou HH:MM), False caso contrário
    """
    # Rejeitar tipos não-string
    if not isinstance(hora_str, str):
        return False

    # Rejeitar strings vazias
    if not hora_str:
        return False

    # Rejeitar espaços externos
    if hora_str != hora_str.strip():
        return False

    try:
        partes = hora_str.split(":")

        # Deve ter exatamente 2 partes
        if len(partes) != 2:
            return False

        hora_part = partes[0].strip()  # Remove espaços internos
        minuto_part = partes[1].strip()

        # Rejeitar se strip removeu caracteres (espaços internos)
        if hora_part != partes[0] or minuto_part != partes[1]:
            return False

        # Componentes não podem estar vazios
        if not hora_part or not minuto_part:
            return False

        # Hora: 1-2 dígitos, Minuto: EXATAMENTE 2 dígitos (MM)
        if len(hora_part) > 2 or len(minuto_part) != 2:
            return False

        # Converter para int (rejeita não-numéricos)
        horas = int(hora_part)
        minutos = int(minuto_part)

        # Validar intervalos
        return 0 <= horas <= 23 and 0 <= minutos <= 59
    except (ValueError, IndexError, AttributeError):
        return False


def _parsear_dias_semana(texto: str) -> list:
    """
    Parseia dias da semana de texto natural.

    Suporta:
    - "segunda a sexta" → [0,1,2,3,4]
    - "seg-sex" → [0,1,2,3,4]
    - "segunda, quarta, sexta" → [0,2,4]
    - etc

    Returns:
        Lista de índices de dias (0-6, onde 0=segunda, 6=domingo)
    """
    t = texto.lower().strip()

    dias_mapa = {
        "segunda": 0, "seg": 0, "segunda-feira": 0,
        "terça": 1, "ter": 1, "terça-feira": 1,
        "quarta": 2, "qua": 2, "quarta-feira": 2,
        "quinta": 3, "qui": 3, "quinta-feira": 3,
        "sexta": 4, "sex": 4, "sexta-feira": 4,
        "sábado": 5, "sabado": 5, "sab": 5,
        "domingo": 6, "dom": 6
    }

    dias = set()

    # Padrão: "X a Y" ou "X-Y"
    import re
    match_range = re.search(r'(\w+)\s+a\s+(\w+)|(\w+)-(\w+)', t)
    if match_range:
        inicio_txt = match_range.group(1) or match_range.group(3)
        fim_txt = match_range.group(2) or match_range.group(4)
        inicio = dias_mapa.get(inicio_txt.strip())
        fim = dias_mapa.get(fim_txt.strip())

        if inicio is not None and fim is not None:
            if inicio <= fim:
                dias.update(range(inicio, fim+1))
            else:
                dias.update(range(inicio, 7))
                dias.update(range(0, fim+1))
            return sorted(list(dias))

    # Padrão: "segunda, quarta, sexta"
    for palavra in re.split(r'[,\s]+', t):
        if palavra in dias_mapa:
            dias.add(dias_mapa[palavra])

    # Padrão: "todos os dias" ou "todo dia" (incluindo domingo)
    if "todos" in t or ("todo" in t and "dia" in t):
        return [0,1,2,3,4,5,6]

    # Padrão: "segunda a sexta" (exceto domingo)
    if ("segunda" in t or "seg" in t) and ("sexta" in t or "sex" in t):
        return [0,1,2,3,4]

    return sorted(list(dias)) if dias else []


def _parsear_horarios(texto: str) -> dict:
    """
    Parseia horários de texto natural.

    Suporta:
    - "9h às 18h" → {"inicio": "09:00", "fim": "18:00"}
    - "das 9:00 até 18:00" → {"inicio": "09:00", "fim": "18:00"}
    - etc

    Returns:
        {"inicio": "HH:MM", "fim": "HH:MM"} ou {}
    """
    import re
    t = texto.lower()

    # Padrão: HH:MM, H:MM, Hh, ou HHh
    horas = re.findall(r'(\d{1,2})(?::(\d{2}))?h?', t)

    if len(horas) >= 2:
        inicio_h = horas[0][0].zfill(2)
        inicio_m = horas[0][1] or "00"
        fim_h = horas[1][0].zfill(2)
        fim_m = horas[1][1] or "00"

        return {
            "inicio": f"{inicio_h}:{inicio_m}",
            "fim": f"{fim_h}:{fim_m}"
        }

    return {}


def validar_integridade_agenda(agenda_dict: dict) -> tuple[bool, str]:
    """
    Valida integridade de agenda_padrao antes de persistir.

    Verifica:
    - Formato HH:MM para horários
    - Hora 00-23, Minuto 00-59
    - Para dia aberto: fim > inicio
    - Sem meia-noite atravessada

    Args:
        agenda_dict: {"0": {"aberto": bool, "inicio": "HH:MM", "fim": "HH:MM"}, ...}

    Returns:
        (válido: bool, mensagem: str)
    """
    dias_semana = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]

    for dia_str in ["0", "1", "2", "3", "4", "5", "6"]:
        dia_config = agenda_dict.get(dia_str, {})

        # Dias fechados não precisam de horários
        if not dia_config.get("aberto"):
            continue

        # Dias abertos precisam de inicio e fim
        inicio = dia_config.get("inicio")
        fim = dia_config.get("fim")

        if not inicio or not fim:
            return False, f"Dia {dias_semana[int(dia_str)]}: falta horário de início ou fim."

        # Validar formato HH:MM
        if not _validar_formato_hora(inicio):
            return False, f"Dia {dias_semana[int(dia_str)]}: horário de início '{inicio}' inválido (use HH:MM)."

        if not _validar_formato_hora(fim):
            return False, f"Dia {dias_semana[int(dia_str)]}: horário de fim '{fim}' inválido (use HH:MM)."

        # Validar que fim > inicio
        inicio_minutos = int(inicio.split(":")[0]) * 60 + int(inicio.split(":")[1])
        fim_minutos = int(fim.split(":")[0]) * 60 + int(fim.split(":")[1])

        if fim_minutos <= inicio_minutos:
            return False, f"Dia {dias_semana[int(dia_str)]}: horário de fim ({fim}) deve ser posterior ao início ({inicio})."

    return True, ""


def construir_agenda_por_dias(dias_config: dict) -> tuple[dict, bool, str]:
    """
    Constrói agenda_padrao para Firestore com validação.

    Args:
        dias_config: {
            "dias": [0,1,2,3,4],
            "horarios": {
                "0": {"inicio": "09:00", "fim": "18:00"},
                "5": {"inicio": "09:00", "fim": "13:00"}
            }
        }

    Returns:
        (agenda_dict, válido: bool, mensagem_erro: str)
    """
    agenda = {}
    horarios = dias_config.get("horarios", {})

    for dia in range(7):
        dia_str = str(dia)
        if dia in dias_config.get("dias", []):
            # Verificar se tem horário específico para este dia
            if dia_str in horarios:
                h = horarios[dia_str]
                agenda[dia_str] = {
                    "aberto": True,
                    "inicio": h.get("inicio", "09:00"),
                    "fim": h.get("fim", "18:00")
                }
            else:
                # Usar primeiro horário como padrão
                primeiro_h = next(iter(horarios.values())) if horarios else {"inicio": "09:00", "fim": "18:00"}
                agenda[dia_str] = {
                    "aberto": True,
                    "inicio": primeiro_h.get("inicio"),
                    "fim": primeiro_h.get("fim")
                }
        else:
            agenda[dia_str] = {"aberto": False}

    # Validar integridade
    valido, erro = validar_integridade_agenda(agenda)
    if not valido:
        return agenda, False, erro

    return agenda, True, ""


async def iniciar_onboarding_dono(tenant_id: str, actor_id: str, dono_nome: str, dono_email: str) -> dict:
    """
    Inicia onboarding do dono.

    Args:
        tenant_id: ID do novo tenant
        actor_id: actor_id do dono (normalizado)
        dono_nome: nome do dono
        dono_email: email do dono

    Returns:
        Estado da sessão onboarding
    """
    if not tenant_id or not actor_id:
        raise ValueError("tenant_id e actor_id são obrigatórios")

    try:
        # Criar configuração inicial
        now = datetime.now(pytz.UTC).isoformat()

        config_data = {
            "tenant_id": tenant_id,
            "onboarding_status": "em_progresso",
            "onboarding_etapa_atual": "nome_negocio",
            "onboarding_indice": 0,
            "criado_em": now,
            "criado_por": actor_id,
            "atualizado_em": now,
            "dono_actor_id": actor_id,
            "dono_nome": dono_nome,
            "dono_email": dono_email
        }

        # Escrever em novo path isolado (source of truth)
        print(f"[ONBOARDING] iniciar_onboarding_dono: salvando em Donos/{actor_id}/onboarding/ativo", flush=True)
        novo_ref = get_db().collection("Clientes").document(tenant_id)\
            .collection("Donos").document(actor_id)\
            .collection("onboarding").document("ativo")

        await asyncio.to_thread(lambda: novo_ref.set(config_data))

        # Legacy para compatibilidade (somente negócio, não estado individual)
        legacy_data = {
            "tenant_id": tenant_id,
            "dono_actor_id": actor_id,
            "criado_em": config_data["criado_em"],
            "criado_por": config_data["criado_por"],
            "atualizado_em": config_data["atualizado_em"]
        }

        legacy_ref = get_db().collection("Clientes").document(tenant_id)\
            .collection("Configuracao").document("negocio")

        # Usar set com merge=True para compatibilidade (não falha se não existe)
        await asyncio.to_thread(lambda: legacy_ref.set(legacy_data, merge=True))

        print(f"[OK] Onboarding iniciado para tenant {tenant_id} | actor {actor_id}", flush=True)

        return {
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "onboarding_status": "em_progresso",
            "etapa_atual": "nome_negocio",
            "proximo_passo": "Qual é o nome do seu negócio?"
        }

    except Exception as e:
        print(f"[ERRO] Iniciar onboarding: {e}")
        raise


async def pegar_etapa_onboarding(tenant_id: str, actor_id: str = None) -> dict:
    """
    Obtém etapa atual do onboarding isolada por ator.

    Prioridade:
    1. Novo path: Clientes/{tenant_id}/Donos/{actor_id}/onboarding/ativo
    2. Fallback legacy: Clientes/{tenant_id}/Configuracao/negocio (com ownership validation)
    3. None se nenhum encontrado

    Args:
        tenant_id: ID do tenant
        actor_id: ID do ator (obrigatório para isolamento)

    Returns:
        {"etapa_atual": str, "indice": int, "status": str, "dados": dict}
        ou None se sem onboarding
    """
    if not tenant_id:
        raise ValueError("tenant_id é obrigatório")

    try:
        # 1. Tentar novo path (isolado por ator)
        if actor_id:
            novo_ref = get_db().collection("Clientes").document(tenant_id)\
                .collection("Donos").document(actor_id)\
                .collection("onboarding").document("ativo")

            novo_doc = await asyncio.to_thread(lambda: novo_ref.get())

            if novo_doc.exists:
                config = novo_doc.to_dict()
                return {
                    "etapa_atual": config.get("onboarding_etapa_atual"),
                    "indice": config.get("onboarding_indice", 0),
                    "status": config.get("onboarding_status"),
                    "dados": config
                }

        # 2. Fallback legacy (com validação de ownership)
        legacy_ref = get_db().collection("Clientes").document(tenant_id)\
            .collection("Configuracao").document("negocio")

        legacy_doc = await asyncio.to_thread(lambda: legacy_ref.get())

        if legacy_doc.exists:
            config = legacy_doc.to_dict()

            # Validar ownership se actor_id foi fornecido
            if actor_id:
                legacy_dono = config.get("dono_actor_id")
                if legacy_dono and legacy_dono != actor_id:
                    # Legacy pertence a outro ator, não retornar
                    print(f"[ONBOARDING] Legacy pertence a outro ator (legacy.dono_actor_id={legacy_dono}, actor_id={actor_id})")
                    return None

            return {
                "etapa_atual": config.get("onboarding_etapa_atual"),
                "indice": config.get("onboarding_indice", 0),
                "status": config.get("onboarding_status"),
                "dados": config
            }

        # 3. Nenhum estado encontrado
        return None

    except Exception as e:
        print(f"[ERRO] Pegar etapa onboarding: {e}")
        return None


async def avancar_etapa_onboarding(tenant_id: str, actor_id: str, campo: str, valor: str, ctx: dict = None) -> dict:
    """
    Avança para próxima etapa e salva dado da etapa atual (isolado por actor).

    FASE 3: Suporta draft e confirmação para "agenda_padrao".

    Args:
        tenant_id: ID do tenant
        actor_id: ID do ator
        campo: nome do campo (ex: "nome_negocio")
        valor: valor fornecido pelo dono
        ctx: Contexto da sessão (para gerenciar draft de agenda)

    Returns:
        {
            "etapa_atual": str,
            "proximo_passo": str,
            "estado_interno": str (opcional: "aguardando_informacoes", "aguardando_confirmacao", "concluido")
        }
    """
    if not tenant_id or not actor_id or not campo or not valor:
        raise ValueError("tenant_id, actor_id, campo e valor são obrigatórios")

    try:
        # FASE 3: Lógica especial para "agenda_padrao" com draft e confirmação
        if campo == "agenda_padrao":
            # Inicializar draft se não existe
            if "draft_agenda_padrao" not in (ctx or {}):
                ctx = ctx or {}
                ctx["draft_agenda_padrao"] = {
                    "dias": [],
                    "horarios": {},
                    "estado": "aguardando_informacoes"
                }

            # Parsear dados da mensagem
            dias_novos = _parsear_dias_semana(valor)
            horarios_novos = _parsear_horarios(valor)

            # Mesclar com draft anterior
            draft = mesclar_draft_agenda(ctx["draft_agenda_padrao"], dias_novos, horarios_novos)
            ctx["draft_agenda_padrao"] = draft

            # Validar completude
            validacao = validar_completude_agenda(draft)

            if not validacao["completo"]:
                # Ainda faltam dados — pedir próximo sem avançar etapa
                return {
                    "etapa_atual": "agenda_padrao",
                    "estado_interno": "aguardando_informacoes",
                    "proximo_passo": validacao["proximo_passo"],
                    "draft_atualizado": True
                }

            # Agenda completa — validar e pedir confirmação
            agenda_estruturada, valida, erro_msg = construir_agenda_por_dias({
                "dias": draft["dias"],
                "horarios": draft["horarios"]
            })

            if not valida:
                return {
                    "etapa_atual": "agenda_padrao",
                    "estado_interno": "erro_validacao",
                    "proximo_passo": f"❌ {erro_msg}\n\nPor favor, verifique e tente novamente.",
                    "draft_atualizado": False
                }

            resumo = formatar_resumo_agenda(agenda_estruturada)

            ctx["draft_agenda_padrao"]["agenda_estruturada"] = agenda_estruturada
            ctx["draft_agenda_padrao"]["estado"] = "aguardando_confirmacao"

            return {
                "etapa_atual": "agenda_padrao",
                "estado_interno": "aguardando_confirmacao",
                "proximo_passo": f"{resumo}\n\n✅ Confirma? (sim/não)",
                "draft_atualizado": True
            }

        # Novo path isolado por actor (source of truth)
        novo_ref = get_db().collection("Clientes").document(tenant_id)\
            .collection("Donos").document(actor_id)\
            .collection("onboarding").document("ativo")

        def atualizar():
            novo_doc = novo_ref.get()
            if not novo_doc.exists:
                raise ValueError(f"Onboarding não encontrado para actor {actor_id}")

            config = novo_doc.to_dict()
            etapa_atual = config.get("onboarding_etapa_atual")
            indice_atual = INDICE_ETAPAS.get(etapa_atual, 0)

            # Validar e salvar valor
            validacao = validar_campo_onboarding(campo, valor)
            if not validacao["valido"]:
                raise ValueError(f"Validação falhou: {validacao['motivo']}")

            # Atualizar novo path (isolado)
            novo_ref.update({
                campo: valor,
                "atualizado_em": datetime.now(pytz.UTC).isoformat()
            })

            # Avançar para próxima etapa
            proximo_indice = indice_atual + 1
            if proximo_indice < len(ETAPAS_ONBOARDING):
                proxima_etapa = ETAPAS_ONBOARDING[proximo_indice]
                novo_ref.update({
                    "onboarding_etapa_atual": proxima_etapa,
                    "onboarding_indice": proximo_indice
                })
            else:
                # Onboarding completo
                novo_ref.update({
                    "onboarding_status": "completo",
                    "onboarding_etapa_atual": "completo",
                    "onboarding_indice": len(ETAPAS_ONBOARDING)
                })

            return proxima_etapa if proximo_indice < len(ETAPAS_ONBOARDING) else "completo"

        proxima_etapa = await asyncio.to_thread(atualizar)

        # FASE 2: Se jornada_primeiro_profissional, criar profissional com jornada individual
        if campo == "jornada_primeiro_profissional":
            await _criar_profissional_com_jornada(tenant_id, actor_id, valor)

        print(f"[OK] Etapa avançada para: {proxima_etapa} (tenant: {tenant_id})")

        return {
            "etapa_anterior": campo,
            "etapa_atual": proxima_etapa,
            "proximo_passo": obter_pergunta_etapa(proxima_etapa)
        }

    except Exception as e:
        print(f"[ERRO] Avançar etapa onboarding: {e}")
        raise


async def _criar_profissional_com_jornada(tenant_id: str, actor_id: str, jornada_valor: str) -> None:
    """
    Cria profissional com jornada individual (ou sem, se "igual ao salão").

    Args:
        tenant_id: ID do tenant
        actor_id: ID do ator (dono)
        jornada_valor: Resposta do dono ("igual" ou "HH:MM-HH:MM")

    Busca dados do profissional no onboarding state e cria documento em Firestore.
    """
    try:
        # Buscar dados do profissional coletados nas etapas anteriores
        onboarding_ref = get_db().collection("Clientes").document(tenant_id)\
            .collection("Donos").document(actor_id)\
            .collection("onboarding").document("ativo")

        def buscar():
            doc = onboarding_ref.get()
            if not doc.exists:
                return None
            return doc.to_dict()

        config = await asyncio.to_thread(buscar)
        if not config:
            raise ValueError(f"Onboarding não encontrado para actor {actor_id}")

        nome_prof = config.get("primeiro_profissional")
        servico_nome = config.get("primeiro_servico", "serviço").lower()
        duracao_min = int(config.get("duracao_primeiro_servico", 60))

        if not nome_prof:
            raise ValueError("Nome do profissional não encontrado no onboarding")

        # Preparar serviços dict para salvar_profissional
        servicos_dict = {
            servico_nome: {"preco": None, "duracao": duracao_min}
        }

        # Se resposta é "igual ao salão", não criar agenda individual
        if "igual" in jornada_valor.lower():
            print(f"[ONBOARDING] Profissional {nome_prof} herda agenda do salão", flush=True)
            # Criar profissional SEM agenda individual
            await salvar_profissional(
                user_id=tenant_id,
                nome=nome_prof,
                servicos=servicos_dict,
                agenda_funcionamento=None  # Herda do salão
            )
            return

        # Se tem horário diferente, parsear e criar agenda individual
        jornada_valor_lower = jornada_valor.lower().strip()

        partes = jornada_valor_lower.split("-")
        if len(partes) != 2:
            raise ValueError(f"Formato de jornada inválido: {jornada_valor}")

        inicio_str = partes[0].strip()
        fim_str = partes[1].strip()

        # Normalizar para HH:MM
        if inicio_str.count(":") == 0:
            inicio_str = f"{inicio_str}:00"
        if fim_str.count(":") == 0:
            fim_str = f"{fim_str}:00"

        inicio_str = _normalizar_hora(inicio_str)
        fim_str = _normalizar_hora(fim_str)

        # Criar agenda_funcionamento: seg-sex com mesmo horário, dom fechado
        agenda_funcionamento = {
            "agenda_padrao": {
                "0": {"aberto": True, "inicio": inicio_str, "fim": fim_str},   # segunda
                "1": {"aberto": True, "inicio": inicio_str, "fim": fim_str},   # terça
                "2": {"aberto": True, "inicio": inicio_str, "fim": fim_str},   # quarta
                "3": {"aberto": True, "inicio": inicio_str, "fim": fim_str},   # quinta
                "4": {"aberto": True, "inicio": inicio_str, "fim": fim_str},   # sexta
                "5": {"aberto": True, "inicio": inicio_str, "fim": fim_str},   # sábado
                "6": {"aberto": False}                                         # domingo
            },
            "excecoes_data": {}
        }

        print(f"[ONBOARDING] Profissional {nome_prof} com jornada {inicio_str}-{fim_str}", flush=True)

        # Criar profissional COM agenda individual
        await salvar_profissional(
            user_id=tenant_id,
            nome=nome_prof,
            servicos=servicos_dict,
            agenda_funcionamento=agenda_funcionamento
        )

    except Exception as e:
        print(f"[ERRO] Criar profissional com jornada: {e}", flush=True)
        raise


def _validar_jornada_profissional(valor: str) -> bool:
    """
    Valida jornada do profissional.

    Aceita:
    - "igual" ou "igual ao salão" (herda horário do salão)
    - "HH:MM-HH:MM" (ex: "14:00-17:00")

    Rejeita:
    - Formato inválido
    - Início >= fim
    """
    v = valor.lower().strip()

    # Resposta simples: "igual ao salão"
    if "igual" in v:
        return True

    # Formato HH:MM-HH:MM
    if "-" not in v:
        return False

    try:
        partes = v.split("-")
        if len(partes) != 2:
            return False

        inicio_str = partes[0].strip()
        fim_str = partes[1].strip()

        # Normalizar para HH:MM se necessário
        if inicio_str.count(":") == 0:
            inicio_str = f"{inicio_str}:00"
        if fim_str.count(":") == 0:
            fim_str = f"{fim_str}:00"

        # Validar formato básico
        if not _validar_formato_hora(inicio_str) or not _validar_formato_hora(fim_str):
            return False

        # Validar: início anterior ao fim
        inicio_min = _hora_para_minutos(inicio_str)
        fim_min = _hora_para_minutos(fim_str)

        if inicio_min is None or fim_min is None:
            return False

        return inicio_min < fim_min

    except Exception:
        return False


def _hora_para_minutos(hora_str: str) -> int | None:
    """Converte HH:MM para minutos desde meia-noite."""
    try:
        hh, mm = map(int, hora_str.split(":"))
        if not (0 <= hh < 24 and 0 <= mm < 60):
            return None
        return hh * 60 + mm
    except Exception:
        return None


def validar_campo_onboarding(campo: str, valor: str) -> dict:
    """
    Valida campo do onboarding.

    Args:
        campo: nome do campo
        valor: valor a validar

    Returns:
        {"valido": bool, "motivo": str}
    """
    valor_str = str(valor).strip()

    validacoes = {
        "nome_negocio": lambda v: len(v) > 0 and len(v) < 100,
        "segmento": lambda v: len(v) > 0 and len(v) < 50,
        "endereco": lambda v: len(v) > 0 and len(v) < 200,
        "agenda_padrao": lambda v: ":" in v,  # Formato: "9:00-18:00"
        "primeiro_profissional": lambda v: len(v) > 0 and len(v) < 100,
        "canal_primeiro_profissional": lambda v: len(v) > 0,
        "jornada_primeiro_profissional": _validar_jornada_profissional,  # FASE 2
        "primeiro_servico": lambda v: len(v) > 0 and len(v) < 100,
        "duracao_primeiro_servico": lambda v: v.isdigit() and int(v) > 0 and int(v) <= 480
    }

    if campo not in validacoes:
        return {"valido": False, "motivo": f"Campo desconhecido: {campo}"}

    validador = validacoes[campo]
    if not validador(valor_str):
        return {"valido": False, "motivo": f"Validação falhou para {campo}: {valor_str}"}

    return {"valido": True, "motivo": "OK"}


def formatar_resumo_agenda(agenda_dict: dict) -> str:
    """
    Formata agenda_padrao para confirmação legível.

    Args:
        agenda_dict: {"0": {"aberto": True, "inicio": "09:00", "fim": "18:00"}, ...}

    Returns:
        String formatada para apresentar ao dono
    """
    nomes_dias = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
    linhas = ["📅 **Sua agenda de funcionamento:**\n"]

    dias_abertos = []
    for dia_num in range(7):
        dia_config = agenda_dict.get(str(dia_num), {})
        if dia_config.get("aberto"):
            inicio = dia_config.get("inicio", "09:00")
            fim = dia_config.get("fim", "18:00")
            dias_abertos.append(f"{nomes_dias[dia_num].capitalize()}: {inicio}-{fim}")

    if dias_abertos:
        linhas.append("\n".join(dias_abertos))
        linhas.append("\nDesde fechado: domingo")
    else:
        linhas.append("⚠️ Nenhum dia aberto configurado")

    return "".join(linhas)


def mesclar_draft_agenda(draft_anterior: dict, dias_novos: list = None, horarios_novos: dict = None) -> dict:
    """
    Mescla informações de agenda entre mensagens.

    Args:
        draft_anterior: Draft anterior {"dias": [...], "horarios": {...}, "estado": ...}
        dias_novos: Lista de dias extraída da nova mensagem (opcional)
        horarios_novos: Horários extraídos da nova mensagem (opcional)

    Returns:
        Draft mesclado
    """
    draft = draft_anterior.copy() if draft_anterior else {"dias": [], "horarios": {}, "estado": "aguardando_informacoes"}

    if dias_novos:
        draft["dias"] = dias_novos

    if horarios_novos:
        draft["horarios"].update(horarios_novos)

    return draft


def validar_completude_agenda(draft: dict) -> dict:
    """
    Valida se agenda está completa.

    Args:
        draft: Draft com {"dias": [...], "horarios": {...}}

    Returns:
        {
            "completo": bool,
            "faltando": [list de campos faltando],
            "proximo_passo": str
        }
    """
    faltando = []

    if not draft.get("dias"):
        faltando.append("dias")

    if not draft.get("horarios"):
        faltando.append("horarios")

    if faltando:
        if "dias" in faltando:
            return {
                "completo": False,
                "faltando": faltando,
                "proximo_passo": "Qual é o dia ou dias da semana? (ex: 'segunda a sexta' ou 'todos os dias')"
            }
        else:
            return {
                "completo": False,
                "faltando": faltando,
                "proximo_passo": "Qual é o horário? (ex: 'das 9h às 18h')"
            }

    return {
        "completo": True,
        "faltando": [],
        "proximo_passo": "Agenda completa - confirma?"
    }


def obter_pergunta_etapa(etapa: str) -> str:
    """
    Retorna pergunta conversacional para etapa.

    Args:
        etapa: nome da etapa

    Returns:
        Pergunta para o dono
    """
    perguntas = {
        "nome_negocio": "Qual é o nome do seu negócio?",
        "segmento": "Que tipo de negócio? (Salão, Spa, Clínica, Barbershop, etc)",
        "endereco": "Qual é o endereço do seu negócio?",
        "agenda_padrao": "Qual é o horário de funcionamento? (ex: 'segunda a sexta, das 9h às 18h')",
        "primeiro_profissional": "Nome do primeiro profissional?",
        "canal_primeiro_profissional": "Qual é o WhatsApp ou contato do(a) [nome]?",
        "jornada_primeiro_profissional": "A profissional trabalha nos mesmos dias e horários do salão, ou tem um horário diferente? (ex: 'igual' ou '14:00-17:00')",
        "primeiro_servico": "Qual é o primeiro serviço que oferece?",
        "duracao_primeiro_servico": "Quanto tempo leva o(a) [serviço]? (em minutos)",
        "confirmacao_dados": "Revise os dados e confirme (sim/não)",
        "teste_agendamento": "Vamos testar um agendamento com seus dados...",
        "completo": "Parabéns! Seu negócio está pronto para receber agendamentos."
    }

    return perguntas.get(etapa, "Próximo passo...")


async def marcar_onboarding_completo(tenant_id: str) -> bool:
    """
    Marca onboarding como completo após validação.

    Args:
        tenant_id: ID do tenant

    Returns:
        True se marcado, False caso contrário
    """
    if not tenant_id:
        return False

    try:
        await asyncio.to_thread(
            lambda: get_db().collection("Clientes").document(tenant_id).collection("Configuracao").document("negocio").update({
                "onboarding_status": "completo",
                "onboarding_etapa_atual": "completo",
                "concluido_em": datetime.now(pytz.UTC).isoformat()
            })
        )

        print(f"[OK] Onboarding marcado como completo (tenant: {tenant_id})")
        return True

    except Exception as e:
        print(f"[ERRO] Marcar onboarding completo: {e}")
        return False


async def processar_confirmacao_agenda_padrao(
    tenant_id: str,
    actor_id: str,
    texto_usuario: str,
    draft_agenda: dict
) -> dict:
    """
    Processa confirmação de agenda durante onboarding com idempotência robusta.

    Arquitetura:
    1. Aquisição atômica com .create()
    2. Hash SHA-256 determinístico do draft
    3. Máquina de estados: em_andamento → falha_recuperavel | completo
    4. Lease + fencing para recuperação distribuída
    5. Transação única para atomicidade (agenda + onboarding + operação)
    6. Retry com backoff exponencial (máx 3 tentativas)

    Args:
        tenant_id: ID do tenant
        actor_id: ID do ator
        texto_usuario: Resposta do dono ("sim", "não", etc)
        draft_agenda: Draft com agenda_estruturada + draft_id

    Returns:
        {
            "confirmado": bool,
            "acao": "gravar" | "rejeitar" | "corrigir" | "erro",
            "proximo_passo": str,
            "proxima_etapa": str (opcional),
            "idempotente": bool (opcional)
        }
    """
    texto_lower = texto_usuario.lower().strip()

    # Confirmação positiva
    if any(palavra in texto_lower for palavra in ["sim", "confirma", "ok", "perfeito", "salva", "pronto"]):
        try:
            agenda_estruturada = draft_agenda.get("agenda_estruturada", {})
            draft_id = draft_agenda.get("draft_id")

            if not draft_id:
                raise ValueError("draft_id não encontrado em draft_agenda")

            # Executar com retries
            resultado = await _executar_confirmacao_com_idempotencia(
                tenant_id=tenant_id,
                actor_id=actor_id,
                draft_id=draft_id,
                draft_agenda=draft_agenda,
                agenda_estruturada=agenda_estruturada
            )

            proxima_etapa = resultado.get("proxima_etapa")

            return {
                "confirmado": True,
                "acao": "gravar",
                "proximo_passo": obter_pergunta_etapa(proxima_etapa),
                "proxima_etapa": proxima_etapa,
                "idempotente": resultado.get("idempotente", False)
            }

        except Exception as e:
            print(f"[ERRO] Gravar agenda com idempotência: {e}", flush=True)
            return {
                "confirmado": False,
                "acao": "erro",
                "proximo_passo": f"Erro ao salvar: {str(e)}"
            }

    # Rejeição
    elif any(palavra in texto_lower for palavra in ["não", "cancela", "volta", "outra"]):
        return {
            "confirmado": False,
            "acao": "rejeitar",
            "proximo_passo": "Tudo bem. Qual é o horário correto? (ex: 'segunda a sexta, 9h às 18h')"
        }

    # Correção
    elif any(palavra in texto_lower for palavra in ["corrige", "muda", "errado", "outra", "diferente"]):
        return {
            "confirmado": False,
            "acao": "corrigir",
            "proximo_passo": "Qual é o horário correto? (ex: 'segunda a sexta, 9h às 18h')"
        }

    # Ambíguo — pedir confirmação explícita
    else:
        return {
            "confirmado": False,
            "acao": "ambiguo",
            "proximo_passo": "Pode confirmar? (sim/não)"
        }


async def _executar_confirmacao_com_idempotencia(
    tenant_id: str,
    actor_id: str,
    draft_id: str,
    draft_agenda: dict,
    agenda_estruturada: dict
) -> dict:
    """
    Executa confirmação com retry e recuperação.

    Retries:
    - Máx 3 tentativas totais
    - Backoff exponencial: 100ms, 200ms, 400ms
    - Retry apenas em erros transitórios

    Returns:
        {"proxima_etapa": str, "idempotente": bool}
    """
    tentativa = 0
    operacao_owner_id = _gerar_operation_owner_id()

    while tentativa < MAX_ATTEMPT_COUNT:
        tentativa += 1

        try:
            resultado = await asyncio.to_thread(
                lambda: _confirmar_agenda_transacao_atomica(
                    tenant_id=tenant_id,
                    actor_id=actor_id,
                    draft_id=draft_id,
                    draft_agenda=draft_agenda,
                    agenda_estruturada=agenda_estruturada,
                    operation_owner_id=operacao_owner_id,
                    tentativa_numero=tentativa
                )
            )
            return resultado

        except ValueError as ve:
            # Erro não-recuperável (validação falhou)
            print(f"[ERRO] Validação falhou em tentativa {tentativa}: {ve}", flush=True)
            raise

        except Exception as e:
            # Erro transitório — pode retry
            if tentativa < MAX_ATTEMPT_COUNT:
                backoff_ms = BACKOFF_MULTIPLIER * (2 ** (tentativa - 1))
                print(f"[AVISO] Tentativa {tentativa} falhou, aguardando {backoff_ms}ms: {e}", flush=True)
                await asyncio.sleep(backoff_ms / 1000.0)
                continue
            else:
                # Última tentativa falhou
                raise


def _confirmar_agenda_transacao_atomica(
    tenant_id: str,
    actor_id: str,
    draft_id: str,
    draft_agenda: dict,
    agenda_estruturada: dict,
    operation_owner_id: str,
    tentativa_numero: int
) -> dict:
    """
    Executa a confirmação em transação ÚNICA atomicamente.

    Passos na transação:
    1. Ler documento de operação
    2. Ler documento de onboarding
    3. Validar tenant, hash, proprietário, fencing, status
    4. Gravar agenda
    5. Atualizar onboarding
    6. Marcar operação como completo

    Todas as leituras antes das escritas.
    Todas as escritas na mesma transação.

    Returns:
        {"proxima_etapa": str, "idempotente": bool}

    Raises:
        ValueError: Validação falhou (não retry)
        Exception: Erro transitório (retry)
    """
    db = get_db()

    # Referências de documentos
    operacao_ref = db.collection("Clientes").document(tenant_id)\
        .collection("operacoes_idempotentes").document(f"confirmar_agenda_{draft_id}")

    onboarding_ref = db.collection("Clientes").document(tenant_id)\
        .collection("Donos").document(actor_id)\
        .collection("onboarding").document("ativo")

    agenda_ref = db.collection("Clientes").document(tenant_id)\
        .collection("configuracao").document("agenda_funcionamento")

    # Calcular hash esperado
    draft_hash = _calcular_draft_hash_sha256(draft_agenda)

    # ========== FASE 1: Verificação prévia (fora da transação) ==========

    op_doc = operacao_ref.get()

    if op_doc.exists:
        op_data = op_doc.to_dict()
        status = op_data.get("status")

        # Caso 1: Operação já completa → Idempotência
        if status == "completo":
            resultado_anterior = op_data.get("resultado", {})
            print(f"[IDEMPOTENTE] Operação {draft_id} já completa, retornando resultado anterior", flush=True)
            return {
                "proxima_etapa": resultado_anterior.get("proxima_etapa"),
                "idempotente": True
            }

        # Caso 2: Operação em andamento ou falha recuperável
        if status in ["em_andamento", "falha_recuperavel"]:
            lease_expires = op_data.get("lease_expires_at")
            owner = op_data.get("operation_owner_id")

            # Verificar se lease expirou
            if lease_expires:
                lease_dt = datetime.fromisoformat(lease_expires)
                agora = datetime.now(pytz.UTC)

                if agora >= lease_dt:
                    # Lease expirou → Podemos reclamar
                    print(f"[RECOVERY] Lease expirado para {draft_id}, reclamando propriedade", flush=True)
                    # Continuar com reclaim (new operation_owner_id será usado)
                else:
                    # Lease ainda válido
                    if owner != operation_owner_id:
                        # Outra instância tem propriedade
                        raise Exception(f"Operação {draft_id} em andamento por outro proprietário, lease expires em {lease_expires}")

            # Hash compatível?
            hash_armazenado = op_data.get("draft_hash_sha256")
            if hash_armazenado and hash_armazenado != draft_hash:
                raise ValueError(f"Hash do draft alterado: esperado {hash_armazenado}, obtido {draft_hash}")

    # ========== FASE 2: Aquisição atômica com .create() ==========

    if not op_doc.exists:
        try:
            # Tentar criar atomicamente
            operacao_ref.create({
                "tenant_id": tenant_id,
                "actor_id": actor_id,
                "draft_id": draft_id,
                "operation_owner_id": operation_owner_id,
                "lease_expires_at": _calcular_lease_expiracao(),
                "fencing_version": 1,
                "draft_hash_sha256": draft_hash,
                "status": "em_andamento",
                "tentativas": tentativa_numero,
                "inicio": datetime.now(pytz.UTC).isoformat(),
                "erros": []
            })
            print(f"[OK] Operação {draft_id} criada (tentativa {tentativa_numero})", flush=True)
        except Exception as e:
            # .create() falhou → documento já existe (race condition)
            # Tentar ler resultado anterior
            op_doc = operacao_ref.get()
            if op_doc.exists:
                op_data = op_doc.to_dict()
                if op_data.get("status") == "completo":
                    resultado_anterior = op_data.get("resultado", {})
                    print(f"[IDEMPOTENTE] Race condition resolvida, operação já completa", flush=True)
                    return {
                        "proxima_etapa": resultado_anterior.get("proxima_etapa"),
                        "idempotente": True
                    }
            raise

    # ========== FASE 3: Transação única (leituras + escritas) ==========

    transaction = db.transaction()

    @transaction.transactional
    def executar_transacao():
        # --- Leituras ---

        op_snapshot = transaction.get(operacao_ref)
        if not op_snapshot.exists:
            raise ValueError(f"Operação {draft_id} não encontrada após .create()")

        op_data = op_snapshot.to_dict()

        # Revalidar propriedade e fencing dentro da transação
        owner_atual = op_data.get("operation_owner_id")
        if owner_atual:
            if owner_atual != operation_owner_id:
                raise Exception(f"Propriedade perdida: esperado {operation_owner_id}, encontrado {owner_atual}")

        # Revalidar hash
        hash_atual = op_data.get("draft_hash_sha256")
        if hash_atual != draft_hash:
            raise ValueError(f"Hash alterado na transação: {hash_atual} vs {draft_hash}")

        # Ler onboarding
        onboarding_snapshot = transaction.get(onboarding_ref)
        if not onboarding_snapshot.exists:
            raise ValueError("Onboarding não encontrado")

        config = onboarding_snapshot.to_dict()
        etapa_atual = config.get("onboarding_etapa_atual")
        indice_atual = INDICE_ETAPAS.get(etapa_atual, 0)
        proximo_indice = indice_atual + 1

        # --- Validações ---

        if not agenda_estruturada:
            raise ValueError("Agenda estruturada vazia")

        # 🔥 RE-VALIDAÇÃO P0: Integridade de agenda antes de persistir
        valida, erro_validacao = validar_integridade_agenda(agenda_estruturada)
        if not valida:
            raise ValueError(f"Agenda inválida na persistência: {erro_validacao}")

        # --- Escritas (todas na mesma transação) ---

        # 1. Gravar agenda de funcionamento
        agenda_config = {
            "agenda_padrao": agenda_estruturada,
            "excecoes_data": {},
            "confirmada_em": datetime.now(pytz.UTC).isoformat()
        }
        transaction.set(agenda_ref, agenda_config)

        # 2. Atualizar onboarding (avançar etapa)
        if proximo_indice < len(ETAPAS_ONBOARDING):
            proxima_etapa = ETAPAS_ONBOARDING[proximo_indice]
            transaction.update(onboarding_ref, {
                "onboarding_etapa_atual": proxima_etapa,
                "onboarding_indice": proximo_indice,
                "agenda_padrao": draft_agenda.get("horarios", {}),
                "atualizado_em": datetime.now(pytz.UTC).isoformat()
            })
            resultado_etapa = proxima_etapa
        else:
            transaction.update(onboarding_ref, {
                "onboarding_status": "completo",
                "onboarding_etapa_atual": "completo",
                "atualizado_em": datetime.now(pytz.UTC).isoformat()
            })
            resultado_etapa = "completo"

        # 3. Marcar operação como completo
        transaction.update(operacao_ref, {
            "status": "completo",
            "tentativas": tentativa_numero,
            "fim": datetime.now(pytz.UTC).isoformat(),
            "resultado": {"proxima_etapa": resultado_etapa}
        })

        return resultado_etapa

    try:
        proxima_etapa = executar_transacao()
        print(f"[OK] Transação concluída para {draft_id} (tentativa {tentativa_numero})", flush=True)

        return {
            "proxima_etapa": proxima_etapa,
            "idempotente": False
        }

    except Exception as e:
        # Marcar operação como falha recuperável
        try:
            operacao_ref.update({
                "status": "falha_recuperavel",
                "tentativas": tentativa_numero,
                "erros": [str(e)]
            })
        except Exception as err_update:
            print(f"[AVISO] Falha ao marcar operação como falha_recuperavel: {err_update}", flush=True)

        raise


async def validar_onboarding_minimo(tenant_id: str) -> dict:
    """
    Valida se onboarding mínimo está completo.

    Requisitos mínimos:
    - nome_negocio
    - segmento
    - endereco
    - agenda_padrao
    - primeiro_profissional
    - canal_primeiro_profissional
    - primeiro_servico
    - duracao_primeiro_servico

    Args:
        tenant_id: ID do tenant

    Returns:
        {"valido": bool, "motivo": str, "faltando": []}
    """
    if not tenant_id:
        raise ValueError("tenant_id é obrigatório")

    try:
        doc = await asyncio.to_thread(
            lambda: get_db().collection("Clientes").document(tenant_id).collection("Configuracao").document("negocio").get()
        )

        if not doc.exists:
            return {"valido": False, "motivo": "Configuração não encontrada", "faltando": []}

        config = doc.to_dict()

        campos_obrigatorios = [
            "nome_negocio",
            "segmento",
            "endereco",
            "agenda_padrao",
            "primeiro_profissional",
            "canal_primeiro_profissional",
            "primeiro_servico",
            "duracao_primeiro_servico"
        ]

        faltando = [campo for campo in campos_obrigatorios if not config.get(campo)]

        if faltando:
            return {
                "valido": False,
                "motivo": f"Faltam {len(faltando)} campo(s)",
                "faltando": faltando
            }

        return {
            "valido": True,
            "motivo": "Onboarding mínimo completo",
            "faltando": []
        }

    except Exception as e:
        print(f"[ERRO] Validar onboarding: {e}")
        raise
