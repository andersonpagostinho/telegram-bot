#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P1-R01B: Auditoria Técnica Cenário 05 — Logs Reais em Cada Etapa

Captura em uma única execução:
  1. Texto original
  2. Texto normalizado
  3. Saída classificador conversacional
  4. Prompt enviado ao GPT
  5. JSON bruto do GPT
  6. JSON parseado
  7. Slots extraídos
  8. Decisão do router
  9. Estado final da sessão

Requer: OPENAI_API_KEY configurada
"""

import asyncio
import sys
import os
import json
import uuid
import traceback
from datetime import datetime
from unittest.mock import patch, MagicMock
from pathlib import Path

# Prerequisito crítico
if not os.getenv("OPENAI_API_KEY"):
    print("\n" + "="*80)
    print("BLOQUEIO: OPENAI_API_KEY não está configurada")
    print("="*80)
    print("\nConfigure com:")
    print("  $env:OPENAI_API_KEY = 'sk-your-actual-key-here'")
    print("\nOu use arquivo .env")
    sys.exit(1)

# Setup
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join(os.getcwd(), 'firebase_credentials.json')
sys.path.insert(0, os.getcwd())

# Imports agora seguros
from router.principal_router import get_roteador_principal
from services.firebase_service_async import limpar_tenant, setup_tenant_completo, obter_estado_sessao
from utils.normalizador_humano import normalizar_mensagem
from services.classificador_conversa import ClassificadorConversa

class MockContext:
    def __init__(self):
        self.bot = MagicMock()
        self.bot.send_message = MagicMock(return_value=None)

class AuditLogger:
    """Captura logs estruturados de cada etapa"""

    def __init__(self):
        self.logs = {
            "timestamp": datetime.now().isoformat(),
            "cenario": 5,
            "baseline": "baseline-216-pass",
            "etapas": []
        }

    def registrar(self, etapa_nome: str, dados: dict):
        """Registrar etapa com dados estruturados"""
        entry = {
            "etapa": etapa_nome,
            "timestamp": datetime.now().isoformat(),
            **dados
        }
        self.logs["etapas"].append(entry)

        # Também imprimir
        print(f"\n[{etapa_nome}]")
        if isinstance(dados, dict):
            for k, v in dados.items():
                if isinstance(v, (dict, list)) and len(str(v)) > 100:
                    print(f"  {k}: {str(v)[:200]}...")
                else:
                    print(f"  {k}: {v}")

    def salvar(self, filename: str):
        """Salvar logs em JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.logs, f, indent=2, default=str)
        return filename

async def auditoria_cenario_05_com_logs():
    """Executar cenário 05 com captura de logs reais"""

    print("\n" + "="*80)
    print("P1-R01B: AUDITORIA TÉCNICA CENÁRIO 05 — LOGS REAIS")
    print("="*80)

    logger = AuditLogger()
    tenant_id = f"audit_cenario_05_{uuid.uuid4().hex[:8]}"
    actor_id = "whatsapp:55119999005"

    try:
        # ETAPA 1: Setup
        print("\n[1/9] SETUP TENANT")
        await limpar_tenant(tenant_id)
        await setup_tenant_completo(tenant_id, actor_id)

        logger.registrar("setup_tenant", {
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "status": "OK"
        })

        # ETAPA 2: Texto Original
        print("\n[2/9] TEXTO ORIGINAL")
        mensagem_original = (
            "Olá! Tudo bem? Meu fim de semana foi ótimo! " * 30 +
            "e queria marcar corte com a Bruna amanhã às 15h"
        )

        logger.registrar("texto_original", {
            "tamanho_chars": len(mensagem_original),
            "tamanho_kb": len(mensagem_original) / 1024,
            "primeiros_100": mensagem_original[:100],
            "ultimos_100": mensagem_original[-100:],
            "completo": mensagem_original
        })

        # ETAPA 3: Texto Normalizado
        print("\n[3/9] NORMALIZAÇÃO")
        try:
            msg_normalizada = normalizar_mensagem(mensagem_original)
            logger.registrar("texto_normalizado", {
                "entrada_chars": len(mensagem_original),
                "saida_chars": len(msg_normalizada),
                "redução_pct": (1 - len(msg_normalizada) / len(mensagem_original)) * 100,
                "primeiros_100": msg_normalizada[:100],
                "ultimos_100": msg_normalizada[-100:],
                "completo": msg_normalizada
            })
        except Exception as e:
            logger.registrar("texto_normalizado", {
                "status": "ERRO",
                "erro": str(e),
                "traceback": traceback.format_exc()
            })
            raise

        # ETAPA 4: Classificação Conversacional
        print("\n[4/9] CLASSIFICAÇÃO CONVERSACIONAL")
        try:
            classificador = ClassificadorConversa()
            classificacao = await classificador.classificar(msg_normalizada, tenant_id)

            logger.registrar("classificacao_conversacional", {
                "tipo": classificacao.get("tipo", "desconhecido"),
                "confianca": classificacao.get("confianca", 0),
                "resultado_completo": classificacao
            })
        except Exception as e:
            logger.registrar("classificacao_conversacional", {
                "status": "ERRO",
                "erro": str(e),
                "traceback": traceback.format_exc()
            })
            raise

        # ETAPA 5: Estado antes do processamento
        print("\n[5/9] ESTADO SESSÃO ANTES")
        estado_antes = await obter_estado_sessao(tenant_id, actor_id)

        logger.registrar("estado_antes", {
            "estado_fluxo": estado_antes.get("estado_fluxo", "desconhecido") if estado_antes else None,
            "confirmacao_pendente": estado_antes.get("confirmacao_pendente", False) if estado_antes else False,
            "slots": estado_antes.get("slots", {}) if estado_antes else {},
            "completo": estado_antes
        })

        # ETAPA 6-9: Execução Router com Mocks
        print("\n[6/9] EXECUÇÃO ROTEADOR PRINCIPAL")

        # Adicionar hook para capturar chamada GPT
        gpt_prompt_capturado = None
        gpt_resposta_capturada = None

        # Salvar referência original se possível
        async def capture_gpt_call(messages, **kwargs):
            nonlocal gpt_prompt_capturado, gpt_resposta_capturada
            gpt_prompt_capturado = messages

            # Chamar GPT real
            from services.gpt_client import client
            response = await client.chat.completions.create(messages=messages, **kwargs)
            gpt_resposta_capturada = response.choices[0].message.content if response.choices else None

            return response

        # Mocks para tenant_id
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
                mensagem=mensagem_original,
                update=None,
                context=MockContext()
            )

            logger.registrar("execucao_router", {
                "resposta": resposta.get('resposta', '')[:200],
                "resposta_completa": resposta
            })

        # ETAPA 7: Prompt GPT (se capturado)
        if gpt_prompt_capturado:
            logger.registrar("prompt_gpt", {
                "tipo": "chat_completions",
                "messages": gpt_prompt_capturado
            })
        else:
            logger.registrar("prompt_gpt", {
                "status": "NAO_CAPTURADO",
                "detalhes": "Hook de captura não foi acionado"
            })

        # ETAPA 8: Resposta GPT (se capturada)
        if gpt_resposta_capturada:
            logger.registrar("resposta_gpt_bruta", {
                "conteudo": gpt_resposta_capturada
            })

            # Tentar parsear
            try:
                slots = json.loads(gpt_resposta_capturada) if isinstance(gpt_resposta_capturada, str) else gpt_resposta_capturada
                logger.registrar("resposta_gpt_parseada", {
                    "servico": slots.get("servico"),
                    "profissional": slots.get("profissional"),
                    "data": slots.get("data"),
                    "hora": slots.get("hora"),
                    "completo": slots
                })
            except Exception as e:
                logger.registrar("resposta_gpt_parseada", {
                    "status": "PARSE_ERRO",
                    "erro": str(e)
                })
        else:
            logger.registrar("resposta_gpt_bruta", {
                "status": "NAO_CAPTURADO"
            })

        # ETAPA 9: Estado após processamento
        print("\n[9/9] ESTADO SESSÃO DEPOIS")
        estado_depois = await obter_estado_sessao(tenant_id, actor_id)
        confirmacao_pendente = estado_depois.get("confirmacao_pendente", False) if estado_depois else False

        logger.registrar("estado_depois", {
            "estado_fluxo": estado_depois.get("estado_fluxo", "desconhecido") if estado_depois else None,
            "confirmacao_pendente": confirmacao_pendente,
            "slots": estado_depois.get("slots", {}) if estado_depois else {},
            "completo": estado_depois
        })

        # RESULTADO FINAL
        print("\n" + "="*80)
        print("RESULTADO FINAL")
        print("="*80)

        if confirmacao_pendente:
            resultado = "PASS — Pedido final foi detectado"
            status = "PASS"
        else:
            resultado = "FAIL — Pedido final NÃO foi detectado"
            status = "FAIL"

        logger.registrar("resultado_final", {
            "status": status,
            "confirmacao_pendente": confirmacao_pendente,
            "mensagem": resultado
        })

        print(f"\n{resultado}")

    except Exception as e:
        print(f"\n[ERRO CRÍTICO] {str(e)}")
        print(f"Traceback:\n{traceback.format_exc()}")
        logger.registrar("erro_critico", {
            "mensagem": str(e),
            "traceback": traceback.format_exc()
        })
        return False

    # SALVAR RESULTADO
    output_file = "resultado_audit_cenario_05_logs_reais.json"
    logger.salvar(output_file)
    print(f"\n✓ Logs salvos em: {output_file}")

    return status == "PASS"

if __name__ == "__main__":
    resultado = asyncio.run(auditoria_cenario_05_com_logs())
    sys.exit(0 if resultado else 1)
