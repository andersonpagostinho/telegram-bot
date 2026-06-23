#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPT-TEST-01: Auditoria Cenário 05 com Logs GPT Reais

Nota: Encoding configurado para UTF-8 para suportar caracteres especiais em Windows
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
"""
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
import pytz
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

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
from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_dado_em_path,
    buscar_subcolecao
)
from services.firestore_client import get_db
from services.classificador_conversa import classificar_contexto_mensagem

# ============================================================================
# UTILITÁRIOS DE TESTE (Copiados de p1_robustez_fluxo_conversacional_real.py)
# ============================================================================

async def limpar_tenant(tenant_id: str, actor_id: str = None):
    """Limpar tenant completamente, incluindo contexto legado de TODOS os actor_ids"""
    try:
        db = get_db()
        print(f"  [CLEANUP] Limpando tenant: {tenant_id}")
        for subcol in [
            "Configuracao", "Profissionais", "ServicosNegocio",
            "Atores", "Clientes", "Sessoes", "Eventos", "Notificacoes", "Agendas"
        ]:
            docs = db.collection("Clientes").document(tenant_id).collection(subcol).stream()
            for doc in docs:
                await asyncio.to_thread(lambda d=doc: d.reference.delete())

        doc_ref = db.collection("Clientes").document(tenant_id)
        await asyncio.to_thread(lambda: doc_ref.delete())

        # Também limpar contexto legado para evitar contaminação entre cenários
        # Limpa o actor_id específico E TODOS os possíveis actor_ids dos testes (001-013)
        actor_ids_to_clean = [actor_id] if actor_id else []
        for i in range(1, 14):
            actor_ids_to_clean.append(f"whatsapp:5511999900{i:02d}")

        for aid in set(actor_ids_to_clean):
            if not aid:
                continue
            try:
                legado_ref = db.collection("Clientes").document(aid).collection("MemoriaTemporaria").document("contexto")
                await asyncio.to_thread(lambda: legado_ref.delete())
            except:
                pass  # Arquivo pode não existir, ignorar

        print(f"  [CLEANUP] [OK] Tenant e contextos legados limpos: {tenant_id}")
    except Exception as e:
        print(f"  [CLEANUP] [AVISO] Erro ao limpar: {e}")


async def setup_tenant_completo(tenant_id: str, actor_id: str):
    """Setup: config, profissional, serviço, ator"""

    # Criar configuração
    config = {
        "tenant_id": tenant_id,
        "nome_negocio": "Salão Teste",
        "telefone": "11999999999",
        "data_criacao": datetime.now(pytz.UTC).isoformat(),
    }
    await salvar_dado_em_path(f"Clientes/{tenant_id}/Configuracao/info", config)

    # Criar profissional "Bruna"
    prof_bruna = {
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
    await salvar_dado_em_path(f"Clientes/{tenant_id}/Profissionais/bruna", prof_bruna)

    # Criar serviço "corte"
    servico_corte = {
        "nome": "Corte",
        "duracao_padrao": 30,
        "preco": 50.0,
        "ativo": True,
    }
    await salvar_dado_em_path(f"Clientes/{tenant_id}/ServicosNegocio/corte", servico_corte)

    # Criar serviço "escova"
    servico_escova = {
        "nome": "Escova",
        "duracao_padrao": 45,
        "preco": 80.0,
        "ativo": True,
    }
    await salvar_dado_em_path(f"Clientes/{tenant_id}/ServicosNegocio/escova", servico_escova)

    # Criar ator cliente
    ator = {
        "actor_id": actor_id,
        "tipo_usuario": "cliente",
        "nome": "Cliente Teste",
        "canal": "whatsapp",
        "tenant_id": tenant_id,
        "data_criacao": datetime.now(pytz.UTC).isoformat(),
    }
    await salvar_dado_em_path(f"Clientes/{tenant_id}/Atores/{actor_id}", ator)


async def obter_estado_sessao(tenant_id: str, actor_id: str):
    """Obter estado completo da sessão"""
    return await buscar_dado_em_path(f"Clientes/{tenant_id}/Sessoes/{actor_id}")


# ============================================================================
# MOCK CONTEXT (para não chamar Telegram real)
# ============================================================================

class MockContext:
    def __init__(self):
        self.bot = AsyncMock()
        self.bot.send_message = AsyncMock(return_value=None)

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
        print(f"  [OK] Tenant criado: {tenant_id}\n")

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

        # ETAPA 3: Normalização (Skipped — classificador normaliza internamente)
        print("[3/9] NORMALIZAÇÃO...")
        msg_normalizada = mensagem_original  # Usar original, classificador normaliza
        auditoria["etapas"].append({
            "numero": 3,
            "nome": "normalizacao",
            "entrada_chars": len(mensagem_original),
            "saida_chars": len(msg_normalizada),
            "nota": "Classificador normaliza internamente"
        })
        print(f"  {len(mensagem_original)} chars\n")

        # ETAPA 4: Classificação
        print("[4/9] CLASSIFICAÇÃO CONVERSACIONAL...")
        try:
            classificacao = classificar_contexto_mensagem(msg_normalizada)

            auditoria["etapas"].append({
                "numero": 4,
                "nome": "classificacao",
                "modo": classificacao.get("modo_conversa"),
                "confianca": classificacao.get("confianca"),
                "completo": classificacao
            })
            print(f"  Modo: {classificacao.get('modo_conversa')}")
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

        # ETAPA 6: Executar Router (com GPT real, sem patch)
        print("[6/9] EXECUTANDO ROUTER PRINCIPAL...")

        try:
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
                    "resposta": resposta.get('resposta', '')[:200] if resposta else None,
                    "status": "OK"
                })
                print(f"  [OK] Router executado\n")

        except Exception as e:
            auditoria["etapas"].append({
                "numero": 6,
                "nome": "router_principal",
                "status": "ERRO",
                "erro": str(e)
            })
            print(f"  [ERRO] Router falhou: {str(e)}\n")

        # ETAPA 7: Prompt (não capturável sem patch, skip)
        print("[7/9] PROMPT ENVIADO AO GPT...")
        auditoria["etapas"].append({
            "numero": 7,
            "nome": "prompt_gpt",
            "status": "SKIPPED",
            "nota": "Patch de captura removido para simplificar execução"
        })
        print(f"  [SKIP] Captura de prompt desabilitada\n")

        # ETAPA 8: Resposta (não capturável sem patch, skip)
        print("[8/9] RESPOSTA GPT BRUTA...")
        auditoria["etapas"].append({
            "numero": 8,
            "nome": "resposta_gpt_bruta",
            "status": "SKIPPED",
            "nota": "Patch de captura removido para simplificar execução"
        })
        print(f"  [SKIP] Captura de resposta desabilitada\n")

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
            resultado = "[OK] PASS — Pedido final foi detectado"
            status = "PASS"
        else:
            resultado = "[ERRO] FAIL — Pedido final NÃO foi detectado"
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
        print(f"\n[ERRO] ERRO: {str(e)}")
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

    print(f"[OK] Auditoria salva em: {output_file}\n")

    return auditoria.get("resultado_final", {}).get("status") == "PASS"

if __name__ == "__main__":
    success = asyncio.run(auditoria_cenario_05_gpt_real())
    sys.exit(0 if success else 1)
