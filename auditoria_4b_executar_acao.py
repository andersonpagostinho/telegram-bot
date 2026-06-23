#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LOTE 4B — AUDITORIA executar_acao_gpt EM CENÁRIO 06

Objetivo: Rastrear payload, tipos, campos e contrato quebrado
"""

import asyncio
import sys
import json
import traceback
from unittest.mock import patch, MagicMock
from datetime import datetime
import pytz

sys.path.insert(0, '.')

from services.firebase_service_async import salvar_dado_em_path, buscar_dado_em_path
from router.principal_router import roteador_principal
from tests.p1_robustez_fluxo_conversacional_real import (
    setup_tenant_completo,
    limpar_tenant,
    obter_estado_sessao,
    MockContext,
    get_roteador_principal
)
import uuid

async def auditoria_4b():
    print("\n" + "="*100)
    print("LOTE 4B — AUDITORIA executar_acao_gpt CENÁRIO 06")
    print("="*100 + "\n")

    tenant_id = f"audit_4b_{uuid.uuid4().hex[:8]}"
    actor_id = "whatsapp:55119999006"

    # SETUP
    print("[SETUP] Criando tenant...")
    await limpar_tenant(tenant_id)
    await setup_tenant_completo(tenant_id, actor_id)
    print(f"[OK] Tenant: {tenant_id}\n")

    # PRÉ-CARREGAR CONTEXTO (CORRIGIDO COM ACTOR_ID)
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
        f"Clientes/{actor_id}/MemoriaTemporaria/contexto",
        contexto_pre
    )
    print("[OK] Contexto pré-carregado\n")

    # MENSAGEM
    mensagem = "Pode deixar. Li tudo. Sim, pode confirmar esse horário. Obrigado!"
    print(f"[MSG] Mensagem: {mensagem}\n")

    # INSTRUMENTAR executar_acao_gpt PARA AUDITAR
    original_exec = None
    audit_data = {
        "chamadas": [],
        "erro_detalhado": None,
        "stacktrace": None,
    }

    async def executar_acao_gpt_auditado(update, context, acao, dados_exec=None):
        """Versão auditada que captura payload antes de executar"""
        print(f"\n{'='*100}")
        print("[EXECUTAR_ACAO_AUDITADA] Interceptado chamada")
        print(f"{'='*100}\n")

        # Auditar entrada
        print("[AUDIT] Payload de entrada:")
        print(f"  - update: {type(update)} = {update}")
        print(f"  - context: {type(context)}")
        print(f"  - acao: {type(acao)} = {acao}")
        print(f"  - dados_exec: {type(dados_exec)}")

        if dados_exec:
            print("\n[AUDIT] Campos em dados_exec:")
            for k, v in dados_exec.items():
                print(f"    {k}: {type(v).__name__:15s} = {str(v)[:80]}")

        # Registrar auditoria
        audit_data["chamadas"].append({
            "acao": acao,
            "dados_exec": dados_exec,
            "tipos": {k: type(v).__name__ for k, v in (dados_exec or {}).items()},
        })

        # Executar original com try/except detalhado
        try:
            from services.gpt_executor import executar_acao_gpt as exec_original
            resultado = await exec_original(update, context, acao, dados_exec)
            print(f"\n[RESULTADO] Retornou: {type(resultado)} = {str(resultado)[:100]}")
            return resultado
        except Exception as e:
            import traceback as tb
            print(f"\n[ERRO] Exceção capturada:")
            print(f"  Tipo: {type(e).__name__}")
            print(f"  Mensagem: {e}")
            print(f"\n[STACKTRACE]:")
            stack = tb.format_exc()
            print(stack)

            audit_data["erro_detalhado"] = {
                "tipo": type(e).__name__,
                "mensagem": str(e),
                "stacktrace": stack,
            }
            raise

    # PATCH executar_acao_gpt
    from services import gpt_executor
    gpt_executor.executar_acao_gpt = executar_acao_gpt_auditado

    # RODAR ROUTER
    print("\n[ROUTER] Chamando roteador_principal...")

    with patch('router.principal_router.obter_id_dono') as mock_obter_id:
        mock_obter_id.return_value = tenant_id

        try:
            roteador_principal_inst = get_roteador_principal()
            resposta = await roteador_principal_inst(
                user_id=actor_id,
                mensagem=mensagem,
                update=None,
                context=MockContext()
            )
            print(f"\n[RESPOSTA] Retornou: {resposta}")
        except Exception as e:
            print(f"\n[ERRO ROUTER] {type(e).__name__}: {e}")

    # RELATÓRIO FINAL
    print("\n" + "="*100)
    print("RELATÓRIO DE AUDITORIA")
    print("="*100 + "\n")

    if audit_data["chamadas"]:
        print("[CHAMADAS A executar_acao_gpt]")
        for i, chamada in enumerate(audit_data["chamadas"], 1):
            print(f"\n  Chamada {i}:")
            print(f"    Ação: {chamada['acao']}")
            print(f"    Campos em dados_exec: {list(chamada['tipos'].keys())}")
            print(f"    Tipos: {chamada['tipos']}")

    if audit_data["erro_detalhado"]:
        print(f"\n[ERRO CAPTURADO]")
        print(f"  Tipo: {audit_data['erro_detalhado']['tipo']}")
        print(f"  Mensagem: {audit_data['erro_detalhado']['mensagem']}")
        print(f"\n[STACKTRACE COMPLETO]")
        print(audit_data['erro_detalhado']['stacktrace'])

    # LIMPEZA
    print("\n[LIMPEZA] Removendo tenant...")
    await limpar_tenant(tenant_id)
    print("[OK] Auditoria concluída")

if __name__ == "__main__":
    asyncio.run(auditoria_4b())
