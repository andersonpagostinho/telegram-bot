#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LOTE 3A — Investigação P0: CONFIRMAÇÃO/NEGAÇÃO EMBUTIDA

Executa cenários 06 e 07 com instrumentação completa para auditar:
1. Mensagem original e normalizada
2. confirmacao_pendente carregado
3. Ramo de código executado
4. Condição que falhou
5. Função/linha exata
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pytz
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.firestore_client import get_db
from services.firebase_service_async import (
    buscar_dado_em_path,
    salvar_dado_em_path,
    deletar_dado_em_path,
    obter_id_dono,
)
from services.identidade_service import normalizar_actor_id
from unidecode import unidecode


# ============================================================================
# Helpers
# ============================================================================

def normalizar(texto: str) -> str:
    """Match principal_router normalizar()"""
    return unidecode((texto or "").strip().lower())


def eh_confirmacao(txt: str) -> bool:
    """Match principal_router eh_confirmacao()"""
    t = normalizar(txt or "")

    if not t:
        return False

    if "nao" in t or "não" in t:
        return False

    perguntas_operacionais = [
        "pode ver", "pode verificar", "pode olhar", "pode consultar",
        "pode checar", "pode conferir", "tem como", "consegue ver",
        "consegue verificar",
    ]

    if any(p in t for p in perguntas_operacionais):
        return False

    gatilhos_exatos = {
        "sim", "ok", "certo", "perfeito", "beleza", "blz", "confirmo",
        "confirmado", "pode", "pode ser", "pode sim", "pode ir",
        "manda ver", "fechar",
    }

    if t in gatilhos_exatos:
        return True

    gatilhos_frase = [
        "pode agendar", "pode marcar", "pode confirmar",
        "confirmar", "confirma", "confirme", "agende", "marque",
    ]

    return any(g in t for g in gatilhos_frase)


def eh_desistencia_fluxo(txt: str) -> bool:
    """Match principal_router eh_desistencia_fluxo()"""
    t = normalizar(txt or "")

    sinais_fortes = [
        "nao", "não", "cancelar", "cancela", "nao quero", "deixa pra la",
        "melhor nao", "nao precisa", "desisto",
    ]

    sinais_contexto = [
        "nao vou conseguir", "nao consigo", "tenho compromisso",
        "tenho reuniao", "nesse horario nao da", "depois vejo",
        "vou falar depois", "volto a falar", "deixar para depois",
    ]

    score = 0
    for s in sinais_fortes:
        if s in t:
            score += 2
    for s in sinais_contexto:
        if s in t:
            score += 1

    return score >= 2


async def setup_cenario_com_contexto(tenant_id: str, actor_id: str):
    """Setup com contexto de confirmação pendente"""
    await salvar_dado_em_path(
        f"Clientes/{tenant_id}/Configuracao/info",
        {
            "tenant_id": tenant_id,
            "nome_negocio": "Salão Teste",
            "telefone": "11999999999",
            "data_criacao": datetime.now(pytz.UTC).isoformat(),
        }
    )

    await salvar_dado_em_path(
        f"Clientes/{tenant_id}/Profissionais/bruna",
        {
            "nome": "Bruna",
            "telefone": "11988888888",
            "servicos": ["corte", "escova"],
            "expediente": {
                "seg": {"inicio": "09:00", "fim": "18:00"},
                "ter": {"inicio": "09:00", "fim": "18:00"},
                "qua": {"inicio": "09:00", "fim": "18:00"},
                "qui": {"inicio": "09:00", "fim": "18:00"},
                "sex": {"inicio": "09:00", "fim": "18:00"},
            },
            "ativo": True,
        }
    )

    await salvar_dado_em_path(
        f"Clientes/{tenant_id}/ServicosNegocio/corte",
        {
            "nome": "Corte",
            "duracao_padrao": 30,
            "preco": 50.0,
            "ativo": True,
        }
    )

    await salvar_dado_em_path(
        f"Clientes/{tenant_id}/Sessoes/{actor_id}",
        {
            "ultima_profissional": "Bruna",
            "ultimo_servico": "corte",
        }
    )

    # Contexto com confirmação pendente
    draft_confirmacao = {
        "profissional": "Bruna",
        "hora": "14:00",
        "servico": "corte",
        "data": "amanhã"
    }

    hoje = datetime.now(pytz.UTC).date()
    amanha = hoje + timedelta(days=1)

    await salvar_dado_em_path(
        f"Clientes/{actor_id}/MemoriaTemporaria/contexto",
        {
            "actor_id": actor_id,
            "tenant_id": tenant_id,
            "tipo_usuario": "cliente",
            "canal": "whatsapp",
            "confirmacao_pendente": True,
            "draft_confirmacao": draft_confirmacao,
            "aguardando_confirmacao_agendamento": True,
            "dados_confirmacao_agendamento": {
                "profissional": "Bruna",
                "servico": "corte",
                "data_hora": f"{amanha.isoformat()}T14:00:00",
                "descricao": "Corte com Bruna",
            },
            "estado_fluxo": "agendando",
        }
    )


async def testar_cenario(
    numero: int,
    nome: str,
    mensagem: str,
    tenant_id: str,
    actor_id: str,
):
    """Testa um cenário e coleta evidência"""

    print(f"\n{'='*80}")
    print(f"INVESTIGAÇÃO CENÁRIO {numero}: {nome}")
    print(f"{'='*80}\n")

    # Setup
    print(f"[SETUP] Criando contexto para tenant={tenant_id}")
    await setup_cenario_com_contexto(tenant_id, actor_id)

    # Carregar contexto
    ctx = await buscar_dado_em_path(f"Clientes/{actor_id}/MemoriaTemporaria/contexto")
    print(f"[LOAD] Contexto carregado: {bool(ctx)}")
    print(f"[LOAD] confirmacao_pendente: {ctx.get('aguardando_confirmacao_agendamento')}")
    print(f"[LOAD] draft_confirmacao: {bool(ctx.get('dados_confirmacao_agendamento'))}")
    print(f"[LOAD] estado_fluxo: {ctx.get('estado_fluxo')}")

    # Análise da mensagem
    texto_usuario = mensagem.strip()
    texto_lower = texto_usuario.lower().strip()
    texto_norm = normalizar(texto_usuario)

    print(f"\n[MENSAGEM]")
    print(f"  Original: {texto_usuario!r}")
    print(f"  Lower:    {texto_lower!r}")
    print(f"  Norm:     {texto_norm!r}")

    # Teste de confirmação
    confirmacao = eh_confirmacao(texto_lower)
    desistencia = eh_desistencia_fluxo(texto_norm)

    print(f"\n[DETECÇÃO]")
    print(f"  eh_confirmacao(texto_lower): {confirmacao}")
    print(f"  eh_desistencia_fluxo(texto_norm): {desistencia}")

    # Simulação do ramo
    print(f"\n[SIMULAÇÃO RAMO]")

    # Ramo 1: Confirmação
    confirmacao_pendente_ativa = bool(ctx.get("aguardando_confirmacao_agendamento"))
    print(f"  eh_confirmacao_pendente_ativa(ctx): {confirmacao_pendente_ativa}")

    if confirmacao_pendente_ativa and (confirmacao or False):
        print(f"  > ENTRARIA EM: Bloco CONFIRMACAO (linha 4475)")
        print(f"    Acao: Criar evento com dados={ctx.get('dados_confirmacao_agendamento')}")
    elif confirmacao_pendente_ativa and ctx.get("intencao_conversacional") == "negacao_confirmacao_agendamento":
        print(f"  > ENTRARIA EM: Bloco NEGACAO (linha 4671)")
        print(f"    Acao: Limpar draft e contexto")
    else:
        print(f"  > NENHUM BLOCO P0 ATIVADO")
        print(f"    Razao: confirmacao={confirmacao}, intencao={ctx.get('intencao_conversacional')}")

    # Falha
    print(f"\n[FALHA]")
    if confirmacao_pendente_ativa and not confirmacao:
        print(f"  [X] Confirmacao pendente carregada, mas eh_confirmacao() retornou False")
        print(f"  Ponto exato: principal_router.py:4475-4476")
        print(f"  Condicao falhou: eh_confirmacao(texto_lower) = False")
        print(f"  Raiz: eh_confirmacao() nao esta reconhecendo confirmacao embutida")
    else:
        print(f"  [OK] Confirmacao foi detectada (ou nao deveria entrar)")

    # Cleanup
    await deletar_dado_em_path(f"Clientes/{tenant_id}")


async def main():
    print("\n" + "="*80)
    print("LOTE 3A — INVESTIGAÇÃO P0: CONFIRMAÇÃO/NEGAÇÃO EMBUTIDA")
    print("="*80)

    # Cenário 06
    tenant_06 = f"investigacao_p0_06_{uuid.uuid4().hex[:8]}"
    actor_06 = f"whatsapp:55119999006"

    await testar_cenario(
        numero=6,
        nome="Confirmação embutida em parágrafo",
        mensagem="Pode deixar. Li tudo. Sim, pode confirmar esse horário para mim. Obrigado!",
        tenant_id=tenant_06,
        actor_id=actor_06,
    )

    # Cenário 07
    tenant_07 = f"investigacao_p0_07_{uuid.uuid4().hex[:8]}"
    actor_07 = f"whatsapp:55119999007"

    await testar_cenario(
        numero=7,
        nome="Negação embutida em parágrafo",
        mensagem="Entendi tudo que você explicou, mas não quero mais marcar esse horário.",
        tenant_id=tenant_07,
        actor_id=actor_07,
    )


if __name__ == "__main__":
    asyncio.run(main())
