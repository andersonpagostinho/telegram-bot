#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auditoria Forense Cenário 05 — Mensagem Longa com Pedido no Final
Sem correções, apenas evidência.
"""

import asyncio
import sys
import os
import json
import uuid
import traceback
from datetime import datetime
from unittest.mock import patch, MagicMock

# Setup
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join(os.getcwd(), 'firebase_credentials.json')
sys.path.insert(0, os.getcwd())

from router.principal_router import get_roteador_principal
from services.firebase_service_async import limpar_tenant, setup_tenant_completo, obter_estado_sessao

class MockContext:
    def __init__(self):
        self.bot = MagicMock()
        self.bot.send_message = MagicMock(return_value=None)

async def auditoria_cenario_05():
    """Executar apenas cenário 05 com captura completa de fluxo"""

    print("\n" + "="*80)
    print("AUDITORIA FORENSE — CENÁRIO 05: MENSAGEM LONGA + PEDIDO FINAL")
    print("="*80 + "\n")

    auditoria = {
        "timestamp": datetime.now().isoformat(),
        "cenario": 5,
        "descricao": "Mensagem >2000 chars com conteúdo pessoal + pedido operacional final",
        "fluxo": [],
        "tabela_resultado": []
    }

    tenant_id = f"auditoria_cenario_05_{uuid.uuid4().hex[:8]}"
    actor_id = "whatsapp:55119999005"

    try:
        # 1. SETUP
        print("[1/8] SETUP TENANT")
        await limpar_tenant(tenant_id)
        await setup_tenant_completo(tenant_id, actor_id)
        auditoria["fluxo"].append({
            "etapa": "setup_tenant",
            "status": "OK",
            "tenant_id": tenant_id,
            "actor_id": actor_id
        })
        print(f"  ✓ Tenant criado: {tenant_id}")
        print(f"  ✓ Actor criado: {actor_id}\n")

        # 2. MENSAGEM ORIGINAL
        print("[2/8] MENSAGEM ORIGINAL")
        mensagem = (
            "Olá! Tudo bem? Meu fim de semana foi ótimo! " * 30 +
            "e queria marcar corte com a Bruna amanhã às 15h"
        )
        print(f"  Tamanho: {len(mensagem)} chars")
        print(f"  Primeiros 100 chars: {mensagem[:100]}")
        print(f"  Últimos 100 chars: {mensagem[-100:]}")
        auditoria["fluxo"].append({
            "etapa": "mensagem_original",
            "tamanho_chars": len(mensagem),
            "primeira_parte": mensagem[:100],
            "ultima_parte": mensagem[-100:]
        })
        print()

        # 3. ESTADO ANTES
        print("[3/8] ESTADO SESSÃO ANTES")
        estado_antes = await obter_estado_sessao(tenant_id, actor_id)
        print(f"  Estado: {json.dumps(estado_antes, indent=2, default=str)[:500]}")
        auditoria["fluxo"].append({
            "etapa": "estado_antes",
            "confirmacao_pendente": estado_antes.get("confirmacao_pendente", False) if estado_antes else False,
            "estado_fluxo": estado_antes.get("estado_fluxo", "desconhecido") if estado_antes else None
        })
        print()

        # 4. NORMALIZAÇÃO
        print("[4/8] NORMALIZAÇÃO DE TEXTO")
        from utils.normalizador_humano import normalizar_mensagem
        msg_normalizada = normalizar_mensagem(mensagem)
        print(f"  Original ({len(mensagem)} chars) → Normalizada ({len(msg_normalizada)} chars)")
        print(f"  Resultado: {msg_normalizada[:200]}")
        auditoria["fluxo"].append({
            "etapa": "normalizacao",
            "entrada_chars": len(mensagem),
            "saida_chars": len(msg_normalizada),
            "resultado_preview": msg_normalizada[:200]
        })
        print()

        # 5. CLASSIFICAÇÃO CONVERSACIONAL
        print("[5/8] CLASSIFICAÇÃO CONVERSACIONAL")
        from services.classificador_conversa import ClassificadorConversa
        classificador = ClassificadorConversa()
        classificacao = await classificador.classificar(msg_normalizada, tenant_id)
        print(f"  Tipo: {classificacao.get('tipo', 'desconhecido')}")
        print(f"  Confiança: {classificacao.get('confianca', 0):.2f}")
        print(f"  Payload: {json.dumps(classificacao, indent=2, default=str)[:500]}")
        auditoria["fluxo"].append({
            "etapa": "classificacao",
            "tipo": classificacao.get("tipo", "desconhecido"),
            "confianca": classificacao.get("confianca", 0),
            "resultado_completo": classificacao
        })
        print()

        # 6. EXTRAÇÃO GPT
        print("[6/8] EXTRAÇÃO GPT (interpretador_conversacional)")
        from services.interpretador_conversacional import InterpretadorConversacional
        interpretador = InterpretadorConversacional()

        # Executar roteador principal com mocks
        print("[EXECUTANDO] roteador_principal()")
        with patch('router.principal_router.obter_id_dono') as mock_router, \
             patch('services.gpt_executor.obter_id_dono') as mock_gpt, \
             patch('handlers.bot.obter_id_dono') as mock_bot, \
             patch('handlers.event_handler.obter_id_dono') as mock_handler:

            mock_router.return_value = tenant_id
            mock_gpt.return_value = tenant_id
            mock_bot.return_value = tenant_id
            mock_handler.return_value = tenant_id

            roteador_principal = get_roteador_principal()
            resposta = await roteador_principal(
                user_id=actor_id,
                mensagem=mensagem,
                update=None,
                context=MockContext()
            )

            print(f"  Resposta roteador: {resposta.get('resposta', '')[:200]}")
            auditoria["fluxo"].append({
                "etapa": "roteador_principal",
                "resposta": resposta.get('resposta', '')[:200],
                "resposta_completa": resposta
            })
        print()

        # 7. ESTADO DEPOIS
        print("[7/8] ESTADO SESSÃO DEPOIS")
        estado_depois = await obter_estado_sessao(tenant_id, actor_id)
        confirmacao_pendente = estado_depois.get("confirmacao_pendente", False) if estado_depois else False
        print(f"  Confirmação Pendente: {confirmacao_pendente}")
        print(f"  Estado: {json.dumps(estado_depois, indent=2, default=str)[:500]}")
        auditoria["fluxo"].append({
            "etapa": "estado_depois",
            "confirmacao_pendente": confirmacao_pendente,
            "estado_fluxo": estado_depois.get("estado_fluxo", "desconhecido") if estado_depois else None
        })
        print()

        # 8. RESULTADO FINAL
        print("[8/8] RESULTADO FINAL")
        if confirmacao_pendente:
            resultado = "✅ PASS - Pedido final detectado"
            status = "PASS"
        else:
            resultado = "❌ FAIL - Pedido final NÃO detectado"
            status = "FAIL"

        print(f"  {resultado}")
        auditoria["resultado_final"] = {
            "status": status,
            "confirmacao_pendente": confirmacao_pendente,
            "motivo": resultado
        }

    except Exception as e:
        print(f"\n❌ ERRO DURANTE AUDITORIA: {str(e)}")
        print(f"Traceback:\n{traceback.format_exc()}")
        auditoria["erro"] = {
            "mensagem": str(e),
            "traceback": traceback.format_exc()
        }

    # SALVAR RESULTADO
    print("\n" + "="*80)
    print("SALVANDO AUDITORIA")
    print("="*80)

    audit_file = "resultado_auditoria_cenario_05.json"
    with open(audit_file, 'w') as f:
        json.dump(auditoria, f, indent=2, default=str)
    print(f"✓ Auditoria salva em: {audit_file}")

    return auditoria

if __name__ == "__main__":
    resultado = asyncio.run(auditoria_cenario_05())
    sys.exit(0 if resultado.get("resultado_final", {}).get("status") == "PASS" else 1)
