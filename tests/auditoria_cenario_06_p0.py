#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AUDITORIA CENÁRIO 06 — P0 FECHAMENTO

Objetivo: Identificar o ponto exato após o handler.

Captura:
1. Contexto carregado antes do handler
2. Payload recebido pelo handler
3. Retorno do handler
4. Ação executada após retorno
5. Se chama salvar_evento/criar_evento
6. Se chama send_and_stop
7. Se algum return anterior/intermediário interrompe
8. Se contexto usado pelo handler é diferente do depois
9. Divergências em campos específicos
"""

import asyncio
import sys
import json
import uuid
from unittest.mock import patch, MagicMock
from datetime import datetime
import pytz

sys.path.insert(0, '.')

from services.firebase_service_async import salvar_dado_em_path, obter_id_dono, buscar_dado_em_path
from router.principal_router import roteador_principal
from handlers.confirmacao_pendente_handler import resolver_confirmacao_pendente
from router.principal_router import eh_confirmacao, eh_desistencia_fluxo

# =========================================================
# MOCK CONTEXT
# =========================================================

class MockContext:
    def __init__(self):
        self.bot = MagicMock()
        self.bot.send_message = MagicMock(return_value=None)

# =========================================================
# SETUP
# =========================================================

async def setup_cenario_06(tenant_id: str, actor_id: str):
    """Setup idêntico ao teste real"""

    # Config
    await salvar_dado_em_path(
        f"Clientes/{tenant_id}/Configuracao/info",
        {
            "tenant_id": tenant_id,
            "nome_negocio": "Salao Teste",
            "telefone": "11999999999",
            "data_criacao": datetime.now(pytz.UTC).isoformat(),
        }
    )

    # Profissional Bruna
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

    # Servico
    await salvar_dado_em_path(
        f"Clientes/{tenant_id}/ServicosNegocio/corte",
        {
            "nome": "Corte",
            "duracao_padrao": 30,
            "preco": 50.0,
            "ativo": True,
        }
    )

    # Ator
    await salvar_dado_em_path(
        f"Clientes/{tenant_id}/Atores/{actor_id}",
        {
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            "nome": "Cliente Teste",
            "canal": "whatsapp",
            "tenant_id": tenant_id,
            "data_criacao": datetime.now(pytz.UTC).isoformat(),
        }
    )

async def limpar_cenario(tenant_id: str):
    """Limpar tenant"""
    from google.cloud import firestore
    db = firestore.Client()
    try:
        def delete_collection(coll_ref):
            docs = coll_ref.stream()
            for doc in docs:
                doc.reference.delete()

        def delete_recursive(path):
            ref = db.document(path)
            col_refs = ref.collections()
            for col_ref in col_refs:
                delete_collection(col_ref)
            ref.delete()

        delete_recursive(f"Clientes/{tenant_id}")
    except Exception as e:
        print(f"[CLEANUP] Erro: {e}")

# =========================================================
# AUDITORIA MAIN
# =========================================================

async def auditoria_cenario_06():
    """Auditoria detalhada do cenário 06"""

    print("=" * 100)
    print("AUDITORIA CENÁRIO 06 — P0 FECHAMENTO")
    print("=" * 100)
    print()

    tenant_id = f"audit_06_{uuid.uuid4().hex[:8]}"
    actor_id = "whatsapp:55119999006"

    # SETUP
    print("[SETUP] Criando tenant...")
    await limpar_cenario(tenant_id)
    await setup_cenario_06(tenant_id, actor_id)
    print(f"[OK] Tenant: {tenant_id}")
    print()

    # PRÉ-CARREGAR CONTEXTO COM CONFIRMACAO_PENDENTE
    print("[PREPARACAO] Pré-carregando contexto com confirmacao_pendente=True")
    contexto_pre = {
        "_tenant_id_guard": tenant_id,
        "draft_agendamento": {
            "servico": "corte",
            "profissional": "Bruna",
            "data_hora": "amanha 14:00"
        },
        "dados_confirmacao_agendamento": {
            "servico": "corte",
            "profissional": "Bruna",
            "data_hora": "amanha 14:00"
        },
        "confirmacao_pendente": True,
        "aguardando_confirmacao_agendamento": True,
        "estado_fluxo": "confirmacao_pendente",
    }
    await salvar_dado_em_path(
        f"Clientes/{tenant_id}/MemoriaTemporaria/contexto",
        contexto_pre
    )
    print("[OK] Contexto pré-carregado")
    print()

    # MENSAGEM
    mensagem = "Pode deixar. Li tudo. Sim, pode confirmar esse horario. Obrigado!"
    print(f"[MSG] Mensagem: {mensagem}")
    print()

    # ETAPA 1: CARREGAR CONTEXTO
    print("[ETAPA 1] CARREGAR CONTEXTO")
    ctx_carregado = await buscar_dado_em_path(f"Clientes/{tenant_id}/MemoriaTemporaria/contexto")

    print(f"  confirmacao_pendente: {ctx_carregado.get('confirmacao_pendente')}")
    print(f"  aguardando_confirmacao_agendamento: {ctx_carregado.get('aguardando_confirmacao_agendamento')}")
    print(f"  estado_fluxo: {ctx_carregado.get('estado_fluxo')}")
    print(f"  draft_agendamento: {bool(ctx_carregado.get('draft_agendamento'))}")
    print()

    # ETAPA 2: HANDLER
    print("[ETAPA 2] EXECUTAR HANDLER")
    handler_result = await resolver_confirmacao_pendente(
        ctx_carregado,
        mensagem.lower(),
        tenant_id,
        actor_id,
        funcoes={"eh_desistencia_fluxo": eh_desistencia_fluxo, "eh_confirmacao": eh_confirmacao}
    )

    print(f"  tratado: {handler_result.get('tratado')}")
    print(f"  acao: {handler_result.get('acao')}")
    print(f"  motivo: {handler_result.get('motivo')}")

    ctx_pos_handler = handler_result.get('ctx_modificado')
    if ctx_pos_handler:
        print(f"  ctx_modificado - confirmacao_pendente: {ctx_pos_handler.get('confirmacao_pendente')}")
        print(f"  ctx_modificado - intencao_conversacional: {ctx_pos_handler.get('intencao_conversacional')}")
    print()

    # ETAPA 3: SIMULAÇÃO DO ROUTER
    print("[ETAPA 3] SIMULAR FLUXO ROUTER")

    eventos_capturados = {
        "handler_chamado": False,
        "handler_retornou": handler_result.get('tratado'),
        "send_and_stop_chamado": False,
        "salvar_evento_chamado": False,
        "criar_evento_chamado": False,
        "resposta_final": None,
        "erro": None,
        "etapa_parou": None,
    }

    async def mock_send_and_stop(context, user_id, msg):
        eventos_capturados["send_and_stop_chamado"] = True
        eventos_capturados["resposta_final"] = msg
        print(f"  [SEND_AND_STOP] Chamado com msg: {msg[:50]}")
        return {"resposta": msg}

    async def mock_salvar_evento(*args, **kwargs):
        eventos_capturados["salvar_evento_chamado"] = True
        print(f"  [SALVAR_EVENTO] Chamado")
        return True

    async def mock_criar_evento(*args, **kwargs):
        eventos_capturados["criar_evento_chamado"] = True
        print(f"  [CRIAR_EVENTO] Chamado")
        return {"id": "evento_teste"}

    # Patch
    with patch('router.principal_router.obter_id_dono') as mock_obter_id, \
         patch('router.principal_router._send_and_stop', mock_send_and_stop), \
         patch('router.principal_router.salvar_evento', mock_salvar_evento), \
         patch('router.principal_router.criar_evento', mock_criar_evento), \
         patch('services.event_service_async.criar_evento', mock_criar_evento):

        mock_obter_id.return_value = tenant_id

        try:
            print("  [CHAMAR] router_principal()...")
            resposta = await roteador_principal(
                user_id=actor_id,
                mensagem=mensagem,
                update=None,
                context=MockContext()
            )
            eventos_capturados["resposta_final"] = resposta.get("resposta") if isinstance(resposta, dict) else str(resposta)
        except Exception as e:
            eventos_capturados["erro"] = str(e)
            print(f"  [ERRO] {e}")

    print()

    # TABELA FINAL
    print("=" * 100)
    print("TABELA AUDITORIA")
    print("=" * 100)
    print()

    tabela = [
        ["ETAPA", "ESPERADO", "OBTIDO", "PONTO_DIVERGENCIA"],
        ["-" * 40, "-" * 40, "-" * 40, "-" * 40],
        ["1. Contexto carregado", "confirmacao_pendente=True",
         f"confirmacao_pendente={ctx_carregado.get('confirmacao_pendente')}",
         "OK" if ctx_carregado.get('confirmacao_pendente') else "DIVERGENCIA"],
        ["2. Handler detecta", "eh_confirmacao=True",
         f"eh_confirmacao={eh_confirmacao(mensagem.lower())}",
         "OK" if eh_confirmacao(mensagem.lower()) else "DIVERGENCIA"],
        ["3. Handler retorna", "tratado=True, acao='confirmar'",
         f"tratado={handler_result.get('tratado')}, acao={handler_result.get('acao')}",
         "OK" if handler_result.get('tratado') and handler_result.get('acao') == 'confirmar' else "DIVERGENCIA"],
        ["4. send_and_stop chamado", "True",
         f"{eventos_capturados['send_and_stop_chamado']}",
         "DIVERGENCIA" if not eventos_capturados['send_and_stop_chamado'] else "OK"],
        ["5. Salvar evento chamado", "True (ou criacao evento)",
         f"salvar={eventos_capturados['salvar_evento_chamado']}, criar={eventos_capturados['criar_evento_chamado']}",
         "DIVERGENCIA" if not (eventos_capturados['salvar_evento_chamado'] or eventos_capturados['criar_evento_chamado']) else "OK"],
        ["6. Resposta enviada", "Mensagem de confirmacao",
         f"{eventos_capturados['resposta_final'][:50] if eventos_capturados['resposta_final'] else 'VAZIA'}",
         "OK" if eventos_capturados['resposta_final'] else "DIVERGENCIA"],
    ]

    for row in tabela:
        print(f"{row[0]:45} | {row[1]:35} | {row[2]:35} | {row[3]:20}")

    print()
    print("=" * 100)
    print("DIVERGENCIAS ENCONTRADAS")
    print("=" * 100)
    print()

    divergencias = []
    if not ctx_carregado.get('confirmacao_pendente'):
        divergencias.append("Contexto nao carregado com confirmacao_pendente=True")
    if not handler_result.get('tratado'):
        divergencias.append("Handler nao ativou (tratado=False)")
    if not eventos_capturados['send_and_stop_chamado']:
        divergencias.append("send_and_stop nao foi chamado")
    if not eventos_capturados['resposta_final']:
        divergencias.append("Nenhuma resposta foi enviada")

    if divergencias:
        for i, div in enumerate(divergencias, 1):
            print(f"{i}. {div}")
    else:
        print("Nenhuma divergencia encontrada - Fluxo OK")

    print()
    print("=" * 100)
    print("ANALISE DE CAMPOS")
    print("=" * 100)
    print()

    print("Campos em ctx_carregado:")
    for key in ['confirmacao_pendente', 'aguardando_confirmacao_agendamento', 'estado_fluxo', 'draft_agendamento']:
        print(f"  {key}: {ctx_carregado.get(key)}")

    if ctx_pos_handler:
        print()
        print("Campos em ctx_pos_handler (retornado pelo handler):")
        for key in ['confirmacao_pendente', 'aguardando_confirmacao_agendamento', 'estado_fluxo', 'intencao_conversacional']:
            print(f"  {key}: {ctx_pos_handler.get(key)}")

    # LIMPEZA
    print()
    print("[LIMPEZA] Removendo tenant...")
    await limpar_cenario(tenant_id)
    print("[OK] Auditoria concluida")

# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    asyncio.run(auditoria_cenario_06())
