"""
FASE 4B.1 — Confirmação Explícita de Agendamento

Revalidação determinística + autorização pendente + confirmação inequívoca.

NÃO cria eventos, locks, ou notificações.
"""

from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
import uuid


@dataclass
class AutorizacaoPendente:
    """Autorização pendente de agendamento (PRÉ-CONFIRMAÇÃO)"""

    autorizacao_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    consulta_id: str = ""
    opcao_id: str = ""
    tenant_id: str = ""
    actor_id: str = ""

    # Dados revalidados
    profissional: str = ""
    data: str = ""
    hora_inicio: str = ""
    hora_fim: str = ""
    servicos: list[str] = field(default_factory=list)
    duracao_total_min: int = 0

    # Timestamps
    criado_em: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expira_em: str = field(default_factory=lambda: (
        datetime.utcnow() + timedelta(hours=1)
    ).isoformat())
    confirmada_em: str = ""

    def esta_expirada(self) -> bool:
        """Verifica se autorização expirou (>1h)"""
        try:
            agora = datetime.utcnow()
            expira = datetime.fromisoformat(self.expira_em)
            return agora > expira
        except:
            return False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AutorizacaoPendente":
        return cls(**data)


# ==============================================================================
# ETAPA A: Autorização para Revalidar
# ==============================================================================

async def autorizar_revalidacao(
    tenant_id: str,
    actor_id: str,
    contexto_resultado = None
) -> dict:
    """
    Etapa A: Revalidar disponibilidade.

    Input: Cliente quer prosseguir com a opção selecionada.

    Fluxo:
    1. Recuperar contexto
    2. Validar tenant, actor, TTL
    3. Recuperar opcao_selecionada_id
    4. Chamar varredura_disponibilidade para revalidar
    5. Retornar resultado + preparar autorização

    Retorna:
    {
        "sucesso": bool,
        "mensagem": str,
        "horario_disponivel": bool,
        "horarios_atualizados": [...],
        "autorizacao": AutorizacaoPendente (se disponível)
    }
    """

    from services.resultado_consulta_service import recuperar_resultado_consulta
    from services.varredura_disponibilidade import varrer_disponibilidade_multisservico
    from schemas.resultado_consulta_schema import ContextoResultadoConsulta

    # 1. Recuperar contexto
    if contexto_resultado is None:
        contexto_resultado = await recuperar_resultado_consulta(tenant_id, actor_id)

    if not contexto_resultado:
        return {
            "sucesso": False,
            "mensagem": "Nenhuma consulta ativa para revalidar",
            "horario_disponivel": False
        }

    # Desserializar se recebido como dict (defensive: principal_router passa dict de Firestore)
    if isinstance(contexto_resultado, dict):
        contexto_resultado = ContextoResultadoConsulta.from_dict(contexto_resultado)

    # 2. Validar tenant, actor, TTL
    if not tenant_id or not actor_id:
        return {
            "sucesso": False,
            "mensagem": "Tenant ou actor inválido",
            "horario_disponivel": False
        }

    if contexto_resultado.esta_expirado():
        return {
            "sucesso": False,
            "mensagem": "Consulta expirada. Faça uma nova busca de disponibilidade.",
            "horario_disponivel": False
        }

    # 3. Recuperar opcao_selecionada_id
    opcao_id = contexto_resultado.opcao_selecionada_id
    if not opcao_id:
        return {
            "sucesso": False,
            "mensagem": "Nenhuma opção selecionada. Escolha um horário primeiro.",
            "horario_disponivel": False
        }

    # Encontrar a opção selecionada
    opcao_encontrada = None
    for opcao in contexto_resultado.opcoes:
        if opcao.opcao_id == opcao_id:
            opcao_encontrada = opcao
            break

    if not opcao_encontrada:
        return {
            "sucesso": False,
            "mensagem": f"Opção {opcao_id} não encontrada no contexto",
            "horario_disponivel": False
        }

    # 4. Chamar varredura para revalidar
    resultado_varredura = await varrer_disponibilidade_multisservico(
        tenant_id=tenant_id,
        actor_id=actor_id,
        data=contexto_resultado.data,
        intervalo_inicio=int(opcao_encontrada.hora_inicio.split(":")[0]),
        intervalo_fim=int(opcao_encontrada.hora_fim.split(":")[0]) + 1,  # Até hora + 1
        profissional_mencionada=opcao_encontrada.profissional_id,
        servicos_multiplos=opcao_encontrada.servicos,
        duracao_total=opcao_encontrada.duracao_total_min,
        dono_id=tenant_id
    )

    # Verificar se horário selecionado ainda está disponível
    horario_disponivel = False
    horarios = resultado_varredura.get("horarios_disponiveis", [])

    for h in horarios:
        if h.get("inicio") == opcao_encontrada.hora_inicio:
            horario_disponivel = True
            break

    if not horario_disponivel:
        # Horário ocupado - retornar alternativas
        return {
            "sucesso": False,
            "mensagem": "Esse horário foi ocupado. Escolha uma alternativa atualizada.",
            "horario_disponivel": False,
            "horarios_atualizados": resultado_varredura.get("horarios_disponiveis", []),
            "alternativas": resultado_varredura.get("alternativas", [])
        }

    # Horário ainda disponível - criar autorização pendente
    autorizacao = AutorizacaoPendente(
        consulta_id=contexto_resultado.consulta_id,
        opcao_id=opcao_id,
        tenant_id=tenant_id,
        actor_id=actor_id,
        profissional=opcao_encontrada.profissional_id,
        data=contexto_resultado.data,
        hora_inicio=opcao_encontrada.hora_inicio,
        hora_fim=opcao_encontrada.hora_fim,
        servicos=opcao_encontrada.servicos,
        duracao_total_min=opcao_encontrada.duracao_total_min
    )

    return {
        "sucesso": True,
        "mensagem": f"Horário revalidado: {opcao_encontrada.hora_inicio} com {opcao_encontrada.profissional_id}",
        "horario_disponivel": True,
        "autorizacao": autorizacao
    }


# ==============================================================================
# ETAPA B: Registrar Autorização Pendente
# ==============================================================================

async def registrar_autorizacao_pendente(
    tenant_id: str,
    actor_id: str,
    autorizacao: AutorizacaoPendente
) -> bool:
    """
    Registra autorização pendente em Firestore.

    Path: Clientes/{tenant_id}/Sessoes/{actor_id}
    Campo: autorizacao_pendente

    Retorna: True se sucesso, False se falha.
    """

    from services.firebase_service_async import salvar_dado_em_path

    if not tenant_id or not actor_id:
        print("[AUTORIZACAO_PENDENTE] ❌ Tenant ou actor inválido")
        return False

    path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"

    try:
        resultado = await salvar_dado_em_path(
            path,
            {
                "autorizacao_pendente": autorizacao.to_dict()
            }
        )

        if resultado:
            print(f"[AUTORIZACAO_PENDENTE] ✅ Registrada: {autorizacao.autorizacao_id}")
            return True
        else:
            print("[AUTORIZACAO_PENDENTE] ❌ Falha ao salvar")
            return False

    except Exception as e:
        print(f"[AUTORIZACAO_PENDENTE] ❌ Erro: {str(e)[:100]}")
        return False


# ==============================================================================
# ETAPA C: Invalidar Autorização Anterior
# ==============================================================================

async def invalidar_autorizacao_anterior(
    tenant_id: str,
    actor_id: str
) -> bool:
    """
    Invalida autorização pendente anterior.

    Ocorre quando:
    - Nova consulta
    - Nova seleção
    - Mudança de dados (serviço, profissional, data, horário)
    - Nova intenção incompatível

    Retorna: True se sucesso.
    """

    from services.firebase_service_async import salvar_dado_em_path
    from google.cloud.firestore import DELETE_FIELD

    if not tenant_id or not actor_id:
        return False

    path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"

    try:
        resultado = await salvar_dado_em_path(
            path,
            {
                "autorizacao_pendente": DELETE_FIELD
            }
        )

        if resultado:
            print(f"[AUTORIZACAO_PENDENTE] ✅ Invalidada para {actor_id}")
            return True
        else:
            return False

    except Exception as e:
        print(f"[AUTORIZACAO_PENDENTE] ❌ Erro ao invalidar: {str(e)[:100]}")
        return False


# ==============================================================================
# ETAPA D: Validar Confirmação Explícita
# ==============================================================================

def eh_confirmacao_explicita(mensagem: str) -> bool:
    """
    Verifica se mensagem é confirmação inequívoca.

    Aceita:
    - "Sim, pode agendar"
    - "Confirmo o agendamento"
    - "Sim, confirmo"
    - Similar

    Rejeita:
    - "Pode ser"
    - "O primeiro"
    - "Gostei desse"
    - "Quero esse horário"
    - Números puros
    """

    msg_norm = mensagem.lower().strip()

    # Aceitar confirmações explícitas
    confirmacoes_aceitas = [
        "sim, pode agendar",
        "confirmo o agendamento",
        "sim, confirmo",
        "confirmo",
        "pode agendar",
        "sim",
        "confirmar agendamento",
        "agendar"
    ]

    for confirmacao in confirmacoes_aceitas:
        if confirmacao in msg_norm:
            return True

    # Rejeitar confirmações ambíguas
    rejeitar = [
        "pode ser",
        "o primeiro",
        "a primeira",
        "o segundo",
        "a segunda",
        "último",
        "última",
        "quero esse",
        "gostei",
        "esse",
        "opção"
    ]

    for rejeicao in rejeitar:
        if rejeicao in msg_norm:
            return False

    # Rejeitar números puros
    if msg_norm.isdigit():
        return False

    # Padrão: se tiver "sim" ou "confirmar" no começo, provavelmente OK
    if msg_norm.startswith("sim") or msg_norm.startswith("confirmar"):
        return True

    return False


# ==============================================================================
# ETAPA FINAL: Processar Confirmação
# ==============================================================================

async def processar_confirmacao_agendamento(
    mensagem: str,
    tenant_id: str,
    actor_id: str,
    autorizacao: AutorizacaoPendente = None
) -> dict:
    """
    Processa confirmação final e registra autorização válida.

    Fluxo:
    1. Verificar se é confirmação explícita
    2. Recuperar autorização pendente (se não fornecida)
    3. Validar que autorização é válida (não expirada)
    4. Validar tenant, actor, consulta, opcao
    5. Registrar confirmação (SEM criar evento)

    Retorna:
    {
        "sucesso": bool,
        "mensagem": str,
        "autorizacao_confirmada": AutorizacaoPendente (se sucesso)
    }
    """

    from services.firebase_service_async import buscar_dado_em_path

    # 1. Verificar se é confirmação explícita
    if not eh_confirmacao_explicita(mensagem):
        return {
            "sucesso": False,
            "mensagem": "Confirmação não é clara. Use 'Sim, pode agendar' ou 'Confirmo o agendamento'."
        }

    # 2. Recuperar autorização pendente do Firestore
    if autorizacao is None:
        path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"
        sessao_data = await buscar_dado_em_path(path)

        if not sessao_data or "autorizacao_pendente" not in sessao_data:
            return {
                "sucesso": False,
                "mensagem": "Nenhuma revalidação ativa para confirmar."
            }

        autorizacao = AutorizacaoPendente.from_dict(sessao_data["autorizacao_pendente"])

    # 3. Validar autorização não expirou
    if autorizacao.esta_expirada():
        await invalidar_autorizacao_anterior(tenant_id, actor_id)
        return {
            "sucesso": False,
            "mensagem": "Autorização expirou. Revalide o horário novamente."
        }

    # 4. Validar tenant, actor, consulta
    if (autorizacao.tenant_id != tenant_id or
        autorizacao.actor_id != actor_id):
        return {
            "sucesso": False,
            "mensagem": "Mismatch de tenant/actor"
        }

    # P0-1: RE-VALIDAÇÃO FINAL ANTES DE REGISTRAR CONFIRMAÇÃO
    # Garantir que o horário continua livre e os serviços continuam válidos
    from services.event_service_async import verificar_conflito_e_sugestoes_profissional
    from services.duracao_service import obter_duracao_por_profissional_bridge
    from services.firebase_service_async import buscar_documento

    # Re-validar conflitos
    resultado_motor = await verificar_conflito_e_sugestoes_profissional(
        user_id=actor_id,
        data=autorizacao.data,
        hora_inicio=autorizacao.hora_inicio,
        duracao_min=autorizacao.duracao_total_min,
        profissional=autorizacao.profissional,
        servico=None,
        tenant_id=tenant_id,
        servicos_bloco=autorizacao.servicos
    )

    if resultado_motor.get("conflito"):
        # Horário ficou indisponível
        await invalidar_autorizacao_anterior(tenant_id, actor_id)
        alternativas = resultado_motor.get("alternativas", [])
        return {
            "sucesso": False,
            "mensagem": "O horário ficou indisponível. Escolha outro.",
            "alternativas": alternativas
        }

    # P0-2: VALIDAÇÃO INTEGRAL DE DURAÇÃO DO CATÁLOGO ATUAL
    # Carregar catálogo do tenant e validar todos os serviços
    catalogo_path = f"Clientes/{tenant_id}/Configuracao/Servicos"
    servicos_db = await buscar_documento(catalogo_path) or {}

    # Validar que todos os serviços existem no catálogo
    for servico in autorizacao.servicos:
        if servico not in servicos_db:
            await invalidar_autorizacao_anterior(tenant_id, actor_id)
            return {
                "sucesso": False,
                "mensagem": f"Serviço '{servico}' não está mais disponível no catálogo."
            }

    # Validar que todas as durações são válidas
    duracao_total_recalculada = 0
    for servico in autorizacao.servicos:
        servico_data = servicos_db.get(servico, {})
        duracao = servico_data.get("duracao", None)

        # Validar que duração existe, é número e é positiva
        if duracao is None:
            await invalidar_autorizacao_anterior(tenant_id, actor_id)
            return {
                "sucesso": False,
                "mensagem": f"Serviço '{servico}' sem duração definida no catálogo."
            }

        try:
            duracao = int(duracao)
        except (ValueError, TypeError):
            await invalidar_autorizacao_anterior(tenant_id, actor_id)
            return {
                "sucesso": False,
                "mensagem": f"Duração de '{servico}' é inválida no catálogo."
            }

        if duracao <= 0:
            await invalidar_autorizacao_anterior(tenant_id, actor_id)
            return {
                "sucesso": False,
                "mensagem": f"Duração de '{servico}' deve ser positiva (encontrado: {duracao})."
            }

        duracao_total_recalculada += duracao

    # Verificar se profissional atende todos os serviços
    profissional_path = f"Clientes/{tenant_id}/Profissionais/{autorizacao.profissional}"
    prof_data = await buscar_documento(profissional_path) or {}
    servicos_prof = prof_data.get("servicos", [])

    for servico in autorizacao.servicos:
        if servico not in servicos_prof:
            await invalidar_autorizacao_anterior(tenant_id, actor_id)
            return {
                "sucesso": False,
                "mensagem": f"Profissional não executa '{servico}'."
            }

    # Atualizar duração total com o valor recalculado (catálogo atual prevalece)
    autorizacao.duracao_total_min = duracao_total_recalculada

    # 5. Validações concluídas com sucesso
    # NÃO marcar confirmada_em aqui - será feito DEPOIS da criação do evento (router)
    # Permite recuperação segura se a criação falhar
    autorizacao_validada = autorizacao

    return {
        "sucesso": True,
        "mensagem": f"✅ Agendamento validado para {autorizacao.hora_inicio}",
        "autorizacao_confirmada": autorizacao_validada
    }
