# Serviço de Onboarding do Dono
# Responsabilidade: Guiar dono através de onboarding conversacional
# Sem salvar catálogo/agenda na sessão - apenas estado de progresso
# Dados permanentes salvos em Firestore em Configuracao/negocio

import asyncio
from datetime import datetime
import pytz
from services.identidade_service import criar_ator_dono, normalizar_actor_id
from services.firestore_client import get_db

# Estados do onboarding
ETAPAS_ONBOARDING = [
    "nome_negocio",
    "segmento",
    "endereco",
    "agenda_padrao",
    "primeiro_profissional",
    "canal_primeiro_profissional",
    "primeiro_servico",
    "duracao_primeiro_servico",
    "confirmacao_dados",
    "teste_agendamento",
    "completo"
]

INDICE_ETAPAS = {etapa: idx for idx, etapa in enumerate(ETAPAS_ONBOARDING)}


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

        await asyncio.to_thread(
            lambda: get_db().collection("Clientes").document(tenant_id).collection("Configuracao").document("negocio").set(config_data)
        )

        print(f"[OK] Onboarding iniciado para tenant {tenant_id}")

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


async def pegar_etapa_onboarding(tenant_id: str) -> dict:
    """
    Obtém etapa atual do onboarding.

    Args:
        tenant_id: ID do tenant

    Returns:
        {"etapa_atual": str, "indice": int, "status": str}
    """
    if not tenant_id:
        raise ValueError("tenant_id é obrigatório")

    try:
        doc = await asyncio.to_thread(
            lambda: get_db().collection("Clientes").document(tenant_id).collection("Configuracao").document("negocio").get()
        )

        if not doc.exists:
            return None

        config = doc.to_dict()
        return {
            "etapa_atual": config.get("onboarding_etapa_atual"),
            "indice": config.get("onboarding_indice", 0),
            "status": config.get("onboarding_status"),
            "dados": config
        }

    except Exception as e:
        print(f"[ERRO] Pegar etapa onboarding: {e}")
        return None


async def avancar_etapa_onboarding(tenant_id: str, campo: str, valor: str) -> dict:
    """
    Avança para próxima etapa e salva dado da etapa atual.

    IMPORTANTE: Apenas salva em Configuracao/negocio, não na sessão.

    Args:
        tenant_id: ID do tenant
        campo: nome do campo (ex: "nome_negocio")
        valor: valor fornecido pelo dono

    Returns:
        {"etapa_atual": str, "proximo_passo": str}
    """
    if not tenant_id or not campo or not valor:
        raise ValueError("tenant_id, campo e valor são obrigatórios")

    try:
        # Obter configuração atual
        config_ref = get_db().collection("Clientes").document(tenant_id).collection("Configuracao").document("negocio")

        def atualizar():
            config_doc = config_ref.get()
            if not config_doc.exists:
                raise ValueError("Configuração não encontrada")

            config = config_doc.to_dict()
            etapa_atual = config.get("onboarding_etapa_atual")
            indice_atual = INDICE_ETAPAS.get(etapa_atual, 0)

            # Validar e salvar valor
            validacao = validar_campo_onboarding(campo, valor)
            if not validacao["valido"]:
                raise ValueError(f"Validação falhou: {validacao['motivo']}")

            # Salvar campo (apenas em Configuracao, não na sessão)
            config_ref.update({
                campo: valor,
                "atualizado_em": datetime.now(pytz.UTC).isoformat()
            })

            # Avançar para próxima etapa
            proximo_indice = indice_atual + 1
            if proximo_indice < len(ETAPAS_ONBOARDING):
                proxima_etapa = ETAPAS_ONBOARDING[proximo_indice]
                config_ref.update({
                    "onboarding_etapa_atual": proxima_etapa,
                    "onboarding_indice": proximo_indice
                })
            else:
                # Onboarding completo
                config_ref.update({
                    "onboarding_status": "completo",
                    "onboarding_etapa_atual": "completo",
                    "onboarding_indice": len(ETAPAS_ONBOARDING)
                })

            return proxima_etapa if proximo_indice < len(ETAPAS_ONBOARDING) else "completo"

        proxima_etapa = await asyncio.to_thread(atualizar)

        print(f"[OK] Etapa avançada para: {proxima_etapa} (tenant: {tenant_id})")

        return {
            "etapa_anterior": campo,
            "etapa_atual": proxima_etapa,
            "proximo_passo": obter_pergunta_etapa(proxima_etapa)
        }

    except Exception as e:
        print(f"[ERRO] Avançar etapa onboarding: {e}")
        raise


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
        "primeiro_servico": lambda v: len(v) > 0 and len(v) < 100,
        "duracao_primeiro_servico": lambda v: v.isdigit() and int(v) > 0 and int(v) <= 480
    }

    if campo not in validacoes:
        return {"valido": False, "motivo": f"Campo desconhecido: {campo}"}

    validador = validacoes[campo]
    if not validador(valor_str):
        return {"valido": False, "motivo": f"Validação falhou para {campo}: {valor_str}"}

    return {"valido": True, "motivo": "OK"}


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
        "agenda_padrao": "Qual é o horário de funcionamento? (ex: 9:00-18:00)",
        "primeiro_profissional": "Nome do primeiro profissional?",
        "canal_primeiro_profissional": "Qual é o WhatsApp ou contato do(a) [nome]?",
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
