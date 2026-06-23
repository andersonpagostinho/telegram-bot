#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPT-TEST-01: Auditoria Cenário 05 com Logs GPT Reais

Objetivo:
- Executar cenário 05 com OPENAI_API_KEY presente
- Capturar logs reais em cada etapa
- Documentar fluxo completo com JSON do GPT
- Identificar causa raiz de falha

Captura:
1. Texto original
2. Texto normalizado
3. Classificação conversacional
4. Prompt enviado ao GPT
5. JSON bruto do GPT
6. JSON parseado
7. Slots extraídos
8. Decisão do router
9. Estado final da sessão

Execução:
python tests/audit_cenario_05_gpt_real.py

Pré-requisito:
OPENAI_API_KEY deve estar configurada (validado por smoke.py)
"""

import asyncio
import json
import os
import sys
import uuid
import traceback
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

# Pré-requisito
if not os.getenv("OPENAI_API_KEY"):
    print("\n" + "="*80)
    print("[BLOQUEIO] OPENAI_API_KEY não está configurada")
    print("="*80)
    print("\nExecute primeiro: python tests/audit_gpt_real_smoke.py")
    print("Depois configure: $env:OPENAI_API_KEY = 'sk-...'\n")
    sys.exit(1)

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join(os.getcwd(), 'firebase_credentials.json')
sys.path.insert(0, os.getcwd())

from router.principal_router import roteador_principal
from services.firebase_service_async import limpar_tenant, setup_tenant_completo, obter_estado_sessao
from utils.normalizador_humano import normalizar_mensagem
from services.classificador_conversa import ClassificadorConversa

class MockContext:
    def __init__(self):
        self.bot = MagicMock()
        self.bot.send_message = MagicMock(return_value=None)

async def auditoria_cenario_05_gpt_real():
    """Executar cenário 05 com captura de logs GPT reais"""

    print("\n" + "="*80)
    print("GPT-TEST-01: AUDITORIA CENÁRIO 05 COM LOGS GPT REAIS")
    print("="*80 + "\n")

    auditoria = {
        "timestamp": datetime.now().isoformat(),
        "cenario": 5,
        "descricao": "Mensagem longa com pedido no final",
        "etapas": [],
        "fluxo_completo": {}
    }

    tenant_id = f"audit_cenario_05_gpt_{uuid.uuid4().hex[:8]}"
    actor_id = "whatsapp:55119999005"

    try:
        # ETAPA 1: Setup
        print("[1/9] SETUP TENANT...")
        await limpar_tenant(tenant_id)
        await setup_tenant_completo(tenant_id, actor_id)

        auditoria["etapas"].append({
            "numero": 1,
            "nome": "setup_tenant",
            "status": "OK",
            "tenant_id": tenant_id,
            "actor_id": actor_id
        })
        print(f"  ✓ Tenant criado: {tenant_id}\n")

        # ETAPA 2: Texto Original
        print("[2/9] TEXTO ORIGINAL...")
        mensagem_original = (
            "Olá! Tudo bem? Meu fim de semana foi ótimo! " * 30 +
            "e queria marcar corte com a Bruna amanhã às 15h"
        )

        auditoria["etapas"].append({
            "numero": 2,
            "nome": "texto_original",
            "tamanho_chars": len(mensagem_original),
            "primeiros_100": mensagem_original[:100],
            "ultimos_100": mensagem_original[-100:]
        })
        print(f"  Tamanho: {len(mensagem_original)} chars\n")

        # ETAPA 3: Normalização
        print("[3/9] NORMALIZAÇÃO...")
        try:
            msg_normalizada = normalizar_mensagem(mensagem_original)
            auditoria["etapas"].append({
                "numero": 3,
                "nome": "normalizacao",
                "entrada_chars": len(mensagem_original),
                "saida_chars": len(msg_normalizada),
                "completo": msg_normalizada
            })
            print(f"  {len(mensagem_original)} → {len(msg_normalizada)} chars\n")
        except Exception as e:
            auditoria["etapas"].append({
                "numero": 3,
                "nome": "normalizacao",
                "status": "ERRO",
                "erro": str(e)
            })
            raise

        # ETAPA 4: Classificação
        print("[4/9] CLASSIFICAÇÃO CONVERSACIONAL...")
        try:
            classificador = ClassificadorConversa()
            classificacao = await classificador.classificar(msg_normalizada, tenant_id)

            auditoria["etapas"].append({
                "numero": 4,
                "nome": "classificacao",
                "tipo": classificacao.get("tipo"),
                "confianca": classificacao.get("confianca"),
                "completo": classificacao
            })
            print(f"  Tipo: {classificacao.get('tipo')}")
            print(f"  Confiança: {classificacao.get('confianca')}\n")
        except Exception as e:
            auditoria["etapas"].append({
                "numero": 4,
                "nome": "classificacao",
                "status": "ERRO",
                "erro": str(e)
            })
            raise

        # ETAPA 5: Estado Antes
        print("[5/9] ESTADO SESSÃO ANTES...")
        estado_antes = await obter_estado_sessao(tenant_id, actor_id)

        auditoria["etapas"].append({
            "numero": 5,
            "nome": "estado_antes",
            "confirmacao_pendente": estado_antes.get("confirmacao_pendente", False) if estado_antes else False,
            "completo": estado_antes
        })
        print(f"  confirmacao_pendente: {estado_antes.get('confirmacao_pendente', False) if estado_antes else False}\n")

        # ETAPA 6-9: Router com Captura de GPT
        print("[6/9] EXECUTANDO ROUTER PRINCIPAL...")

        gpt_prompt_capturado = None
        gpt_resposta_capturada = None

        # Patchar para capturar chamadas GPT
        original_create = None

        async def capture_gpt_create(self, **kwargs):
            nonlocal gpt_prompt_capturado, gpt_resposta_capturada
            gpt_prompt_capturado = kwargs.get("messages")

            # Chamar original
            response = await original_create(**kwargs)
            gpt_resposta_capturada = response.choices[0].message.content if response.choices else None

            return response

        try:
            from openai import AsyncOpenAI
            original_create = AsyncOpenAI.chat.completions.create
            AsyncOpenAI.chat.completions.create = capture_gpt_create

            with patch('router.principal_router.obter_id_dono') as mock_router, \
                 patch('services.gpt_executor.obter_id_dono') as mock_gpt, \
                 patch('handlers.bot.obter_id_dono') as mock_bot, \
                 patch('handlers.event_handler.obter_id_dono') as mock_handler:

                mock_router.return_value = tenant_id
                mock_gpt.return_value = tenant_id
                mock_bot.return_value = tenant_id
                mock_handler.return_value = tenant_id

                resposta = await roteador_principal(
                    user_id=actor_id,
                    mensagem=mensagem_original,
                    update=None,
                    context=MockContext()
                )

                auditoria["etapas"].append({
                    "numero": 6,
                    "nome": "router_principal",
                    "resposta": resposta.get('resposta', '')[:200]
                })
                print(f"  ✓ Router executado\n")

        finally:
            if original_create:
                AsyncOpenAI.chat.completions.create = original_create

        # ETAPA 7: Prompt GPT
        print("[7/9] PROMPT ENVIADO AO GPT...")
        if gpt_prompt_capturado:
            auditoria["etapas"].append({
                "numero": 7,
                "nome": "prompt_gpt",
                "messages": gpt_prompt_capturado
            })
            print(f"  ✓ Prompt capturado ({len(str(gpt_prompt_capturado))} chars)\n")
        else:
            auditoria["etapas"].append({
                "numero": 7,
                "nome": "prompt_gpt",
                "status": "NAO_CAPTURADO"
            })
            print(f"  ⚠ Prompt não foi capturado\n")

        # ETAPA 8: Resposta GPT
        print("[8/9] RESPOSTA GPT BRUTA...")
        if gpt_resposta_capturada:
            auditoria["etapas"].append({
                "numero": 8,
                "nome": "resposta_gpt_bruta",
                "conteudo": gpt_resposta_capturada[:500]
            })

            # Tentar parsear
            try:
                slots = json.loads(gpt_resposta_capturada)
                auditoria["etapas"].append({
                    "numero": 8.5,
                    "nome": "resposta_gpt_parseada",
                    "servico": slots.get("servico"),
                    "profissional": slots.get("profissional"),
                    "data": slots.get("data"),
                    "hora": slots.get("hora"),
                    "completo": slots
                })
                print(f"  ✓ JSON parseado")
                print(f"    - serviço: {slots.get('servico')}")
                print(f"    - profissional: {slots.get('profissional')}")
                print(f"    - data: {slots.get('data')}")
                print(f"    - hora: {slots.get('hora')}\n")
            except:
                print(f"  ⚠ Falha ao parsear JSON\n")
        else:
            auditoria["etapas"].append({
                "numero": 8,
                "nome": "resposta_gpt_bruta",
                "status": "NAO_CAPTURADO"
            })
            print(f"  ⚠ Resposta não foi capturada\n")

        # ETAPA 9: Estado Depois
        print("[9/9] ESTADO SESSÃO DEPOIS...")
        estado_depois = await obter_estado_sessao(tenant_id, actor_id)
        confirmacao_pendente = estado_depois.get("confirmacao_pendente", False) if estado_depois else False

        auditoria["etapas"].append({
            "numero": 9,
            "nome": "estado_depois",
            "confirmacao_pendente": confirmacao_pendente,
            "completo": estado_depois
        })

        # RESULTADO FINAL
        print("\n" + "="*80)
        print("RESULTADO FINAL")
        print("="*80 + "\n")

        if confirmacao_pendente:
            resultado = "✓ PASS — Pedido final foi detectado"
            status = "PASS"
        else:
            resultado = "✗ FAIL — Pedido final NÃO foi detectado"
            status = "FAIL"

        print(f"{resultado}\n")

        auditoria["resultado_final"] = {
            "status": status,
            "confirmacao_pendente": confirmacao_pendente,
            "slots_extraidos": {
                "servico": None,
                "profissional": None,
                "data": None,
                "hora": None
            }
        }

        # Tentar extrair slots se parseou JSON
        for etapa in auditoria["etapas"]:
            if etapa.get("nome") == "resposta_gpt_parseada":
                auditoria["resultado_final"]["slots_extraidos"] = {
                    "servico": etapa.get("servico"),
                    "profissional": etapa.get("profissional"),
                    "data": etapa.get("data"),
                    "hora": etapa.get("hora")
                }

    except Exception as e:
        print(f"\n✗ ERRO: {str(e)}")
        print(f"Traceback:\n{traceback.format_exc()}\n")

        auditoria["erro"] = {
            "mensagem": str(e),
            "tipo": type(e).__name__,
            "traceback": traceback.format_exc()
        }

    # SALVAR RESULTADO
    print("="*80)
    print("SALVANDO AUDITORIA")
    print("="*80 + "\n")

    output_file = "resultado_audit_cenario_05_gpt_real.json"
    with open(output_file, 'w') as f:
        json.dump(auditoria, f, indent=2, default=str)

    print(f"✓ Auditoria salva em: {output_file}\n")

    return auditoria.get("resultado_final", {}).get("status") == "PASS"

if __name__ == "__main__":
    success = asyncio.run(auditoria_cenario_05_gpt_real())
    sys.exit(0 if success else 1)
