#!/usr/bin/env python3
# * coding: utf8 *

"""
FORENSE CENRIO 06  CONFIRMAO EMBUTIDA

Escopo: Cenrio 06 apenas
Objetivo: Descobrir exatamente onde o fluxo para

Captura:
1. Mensagem original
2. Mensagem normalizada
3. confirmacao_pendente carregada
4. Entrada no handler
5. Retorno do handler
6. Ao retornada
7. Prximo bloco executado
8. Criao de evento chamada?
9. Lock chamado?
10. Retorno final ao usurio
"""

import asyncio
import sys
import json
import uuid
from unittest.mock import patch, MagicMock
from datetime import datetime
import pytz

sys.path.insert(0, '.')

from services.firebase_service_async import salvar_dado_em_path, obter_id_dono, buscar_dado_em_path, atualizar_dado_em_path
from router.principal_router import roteador_principal

# =========================================================
# MOCK CONTEXT
# =========================================================

class MockContext:
    def __init__(self):
        self.bot = MagicMock()
        self.bot.send_message = MagicMock(return_value=None)

# =========================================================
# SETUP TENANT
# =========================================================

async def setup_tenant_forense(tenant_id: str, actor_id: str):
    """Setup tenant mnimo para cenrio 06"""

    # Config
    await salvar_dado_em_path(
        f"Clientes/{tenant_id}/Configuracao/info",
        {
            "tenant_id": tenant_id,
            "nome_negocio": "Salo Teste",
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

    # Servio corte
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

async def limpar_tenant_forense(tenant_id: str):
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
# FORENSE MAIN
# =========================================================

async def forense_cenario_06():
    """Forense do cenrio 06"""

    print("=" * 80)
    print("FORENSE CENRIO 06  CONFIRMAO EMBUTIDA")
    print("=" * 80)

    tenant_id = f"forense_06_{uuid.uuid4().hex[:8]}"
    actor_id = "whatsapp:55119999006"

    # ETAPA 1: SETUP
    print("\n[ETAPA 1] SETUP TENANT")
    await limpar_tenant_forense(tenant_id)
    await setup_tenant_forense(tenant_id, actor_id)
    print(f"[OK] Tenant criado: {tenant_id}")

    # ETAPA 2: PRCRIAR CONFIRMAO PENDENTE
    print("\n[ETAPA 2] PRCRIAR CONFIRMAO PENDENTE")

    dados_contexto = {
        "_tenant_id_guard": tenant_id,
        "draft_agendamento": {
            "servico": "corte",
            "profissional": "Bruna",
            "data_hora": "amanh 14:00"
        },
        "dados_confirmacao_agendamento": {
            "servico": "corte",
            "profissional": "Bruna",
            "data_hora": "amanh 14:00"
        },
        "confirmacao_pendente": True,
        "aguardando_confirmacao_agendamento": True
    }

    await salvar_dado_em_path(
        f"Clientes/{tenant_id}/MemoriaTemporaria/contexto",
        dados_contexto
    )
    print(f"[OK] Contexto salvo com confirmacao_pendente=True")

    # ETAPA 3: MENSAGEM ORIGINAL
    print("\n[ETAPA 3] MENSAGEM ORIGINAL")
    mensagem_original = "Pode deixar. Li tudo. Sim, pode confirmar esse horrio. Obrigado!"
    print(f" Mensagem: '{mensagem_original}'")

    # ETAPA 4: INTERCEPTAR CARREGAMENTO DE CONTEXTO
    print("\n[ETAPA 4] CARREGAMENTO DE CONTEXTO")

    contexto_carregado = await buscar_dado_em_path(f"Clientes/{tenant_id}/MemoriaTemporaria/contexto")
    print(f"[OK] Contexto carregado:")
    print(f"    confirmacao_pendente: {contexto_carregado.get('confirmacao_pendente')}")
    print(f"    aguardando_confirmacao: {contexto_carregado.get('aguardando_confirmacao_agendamento')}")
    print(f"    draft_agendamento: {bool(contexto_carregado.get('draft_agendamento'))}")

    # ETAPA 5: NORMALIZAR MENSAGEM
    print("\n[ETAPA 5] NORMALIZAR MENSAGEM")
    from services.classificador_conversa import normalizar_txt
    mensagem_normalizada = normalizar_txt(mensagem_original)
    print(f"[OK] Normalizada: '{mensagem_normalizada}'")

    # ETAPA 6: TESTAR FUNES DE DETECO
    print("\n[ETAPA 6] TESTAR FUNES DE DETECO")
    from router.principal_router import eh_confirmacao, eh_desistencia_fluxo

    eh_conf = eh_confirmacao(mensagem_normalizada)
    eh_desist = eh_desistencia_fluxo(mensagem_normalizada)
    print(f"[OK] eh_confirmacao(): {eh_conf}")
    print(f"[OK] eh_desistencia_fluxo(): {eh_desist}")

    # ETAPA 7: SIMULAR HANDLER
    print("\n[ETAPA 7] SIMULAR HANDLER")
    from handlers.confirmacao_pendente_handler import resolver_confirmacao_pendente

    handler_entrada = {
        "ctx": contexto_carregado,
        "texto_normalizado": mensagem_normalizada,
        "tenant_id": tenant_id,
        "user_id": actor_id,
    }
    print(f"[OK] Entrada handler:")
    print(f"    confirmacao_pendente em ctx: {handler_entrada['ctx'].get('confirmacao_pendente')}")

    handler_result = await resolver_confirmacao_pendente(
        contexto_carregado,
        mensagem_normalizada,
        tenant_id,
        actor_id,
        funcoes={"eh_desistencia_fluxo": eh_desistencia_fluxo, "eh_confirmacao": eh_confirmacao}
    )

    print(f"[OK] Handler retornou:")
    print(f"    tratado: {handler_result.get('tratado')}")
    print(f"    acao: {handler_result.get('acao')}")
    print(f"    motivo: {handler_result.get('motivo')}")

    # ETAPA 8: SIMULAR ROUTER COM MOCK
    print("\n[ETAPA 8] ROUTER COM LOGGING ULTRADETALHADO")

    # Criar variveis globais para capturar eventos
    eventos_router = {
        "handler_chamado": False,
        "handler_tratou": False,
        "save_contexto_chamado": False,
        "send_and_stop_chamado": False,
        "fluxo_continuou": False,
        "erro": None,
    }

    # Patch para capturar eventos
    original_send_and_stop = None
    original_salvar = None

    async def mock_send_and_stop(context, user_id, msg):
        eventos_router["send_and_stop_chamado"] = True
        eventos_router["mensagem_enviada"] = msg
        return {"resposta": msg}

    async def mock_salvar(user_id, ctx, tenant_id=None):
        eventos_router["save_contexto_chamado"] = True
        eventos_router["contexto_salvo"] = True
        return True

    # Mock obter_id_dono para retornar tenant_id
    with patch('router.principal_router.obter_id_dono') as mock_obter_id, \
         patch('router.principal_router._send_and_stop', mock_send_and_stop), \
         patch('router.principal_router.salvar_contexto_temporario', mock_salvar):

        mock_obter_id.return_value = tenant_id

        try:
            print(f" Chamando roteador_principal...")
            resposta = await roteador_principal(
                user_id=actor_id,
                mensagem=mensagem_original,
                update=None,
                context=MockContext()
            )

            eventos_router["fluxo_continuou"] = True
            eventos_router["resposta_final"] = resposta.get("resposta") if isinstance(resposta, dict) else str(resposta)

        except Exception as e:
            eventos_router["erro"] = str(e)
            import traceback
            eventos_router["traceback"] = traceback.format_exc()

    # ETAPA 9: RESULTADO
    print("\n" + "=" * 80)
    print("RESULTADO DA FORENSE")
    print("=" * 80)

    resultado_tabela = [
        ["Etapa", "Resultado", "Observao"],
        ["" * 30, "" * 40, "" * 40],
        ["1. Mensagem Original", "[OK]", mensagem_original[:50] + "..."],
        ["2. Mensagem Normalizada", "[OK]", mensagem_normalizada[:50] + "..."],
        ["3. confirmacao_pendente", "[OK] TRUE" if contexto_carregado.get('confirmacao_pendente') else "[FAIL] FALSE", ""],
        ["4. eh_confirmacao()", "[OK] TRUE" if eh_conf else "[FAIL] FALSE", "Detecta 'pode confirmar'"],
        ["5. eh_desistencia_fluxo()", "[OK] FALSE" if not eh_desist else "[FAIL] TRUE", "No  desistncia"],
        ["6. Handler entrada", "[OK]", f"confirmacao_pendente={contexto_carregado.get('confirmacao_pendente')}"],
        ["7. Handler retorno", "[OK] TRATADO" if handler_result.get('tratado') else "[FAIL] NO", f"acao={handler_result.get('acao')}"],
        ["8. Router chamado", "[OK]", "Com mock obter_id_dono"],
        ["9. send_and_stop", "[OK]" if eventos_router.get('send_and_stop_chamado') else "[FAIL]", "Mensagem final"],
        ["10. Erro", "[OK]" if not eventos_router.get('erro') else "[FAIL] " + eventos_router.get('erro', "")[:50], ""],
    ]

    for row in resultado_tabela:
        print(f"{row[0]:35} | {row[1]:15} | {row[2]}")

    # CLASSIFICAO
    print("\n" + "=" * 80)
    print("CLASSIFICAO")
    print("=" * 80)

    if eh_conf and handler_result.get('tratado') and handler_result.get('acao') == 'confirmar':
        if eventos_router.get('send_and_stop_chamado'):
            print("[PASS] B) CONFIRMAO RECONHECIDA, FLUXO CORRETO")
        elif eventos_router.get('erro'):
            print("[WARN]  B) CONFIRMAO RECONHECIDA, FALHA POSTERIOR")
            print(f"   Erro: {eventos_router.get('erro')}")
        else:
            print("[WARN]  D) REGRESSO DO NOVO HANDLER (no chamou send_and_stop)")
    elif eh_conf and not handler_result.get('tratado'):
        print("[ERRO] C) CONFIRMAO NO RECONHECIDA PELO HANDLER")
    else:
        print("[ERRO] C) CONFIRMAO NO DETECTADA PELA FUNO eh_confirmacao()")

    # DEBUG INFO
    print("\n" + "=" * 80)
    print("DEBUG INFO")
    print("=" * 80)

    print(f"\nEventes Router:")
    for key, val in eventos_router.items():
        if key != "traceback":
            print(f"   {key}: {val}")

    if eventos_router.get("traceback"):
        print(f"\nTraceback:")
        print(eventos_router.get("traceback"))

    # LIMPEZA
    print("\n[LIMPEZA] Removendo tenant de teste...")
    await limpar_tenant_forense(tenant_id)
    print("[OK] Concludo")

# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    asyncio.run(forense_cenario_06())
