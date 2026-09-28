#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTE DIAGNÓSTICO: Rastrear fluxo "ola" WhatsApp
Objetivo: Determinar exatamente qual função produz already_sent=True

CONTEXTO FIXO:
- tenant_id: 7394370553
- user_id: whatsapp:5511991382080
- mensagem: "ola"

NÃO ALTERA CÓDIGO OU FIRESTORE
"""

import sys
import asyncio
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def teste_rastreamento():
    print("\n" + "=" * 80)
    print("TESTE DIAGNÓSTICO: Rastreamento Fluxo 'ola' em WhatsApp")
    print("=" * 80)
    print()

    # Parametros do teste
    user_id = "whatsapp:5511991382080"
    tenant_id = "7394370553"
    mensagem = "ola"

    print(f"[PARAMETROS]")
    print(f"  user_id: {user_id}")
    print(f"  tenant_id: {tenant_id}")
    print(f"  mensagem: {mensagem}")
    print()

    # ========================================================================
    # ETAPA 1: Verificar resolver_tenant_por_endpoint
    # ========================================================================
    print("[ETAPA 1] Verificar resolver_tenant_por_endpoint")
    print("-" * 80)

    try:
        from services.whatsapp_endpoint_service import resolver_tenant_por_endpoint

        phone_number_id = "1350170954840548"
        tenant_resolvido = resolver_tenant_por_endpoint(phone_number_id)

        print(f"resolver_tenant_por_endpoint('{phone_number_id}')")
        print(f"  Resultado: {tenant_resolvido}")
        print(f"  Esperado:  {tenant_id}")
        print(f"  Status:    {'✅ OK' if tenant_resolvido == tenant_id else '❌ ERRO'}")
        print()
    except Exception as e:
        print(f"[ERRO] {e}")
        print()

    # ========================================================================
    # ETAPA 2: Chamar roteador_principal COM PARAMETERS EXATOS DO WHATSAPP
    # ========================================================================
    print("[ETAPA 2] Chamar roteador_principal")
    print("-" * 80)

    try:
        from router.principal_router import roteador_principal

        print(f"Chamando: roteador_principal(")
        print(f"  user_id='{user_id}',")
        print(f"  mensagem='{mensagem}',")
        print(f"  tenant_id='{tenant_id}',")
        print(f"  update=None,")
        print(f"  context=None")
        print(f")")
        print()

        resultado = await roteador_principal(
            user_id=user_id,
            mensagem=mensagem,
            tenant_id=tenant_id,
            update=None,
            context=None
        )

        print(f"[RESULTADO BRUTO]")
        print(f"  Type: {type(resultado)}")
        print(f"  Valor: {resultado}")
        print()

        # ====================================================================
        # ETAPA 3: Analisar o resultado
        # ====================================================================
        print("[ETAPA 3] Analisar Resultado")
        print("-" * 80)

        if isinstance(resultado, dict):
            print(f"✅ Resultado é dict")
            print(f"  Chaves: {list(resultado.keys())}")

            if "already_sent" in resultado:
                print(f"  already_sent: {resultado.get('already_sent')}")

            if "handled" in resultado:
                print(f"  handled: {resultado.get('handled')}")

            if "resposta" in resultado:
                print(f"  resposta: {resultado.get('resposta')[:80]}...")

            if "acao" in resultado:
                print(f"  acao: {resultado.get('acao')}")

            print()

            # Verificar se already_sent=True
            if resultado.get("already_sent") == True:
                print("[ACHADO!] already_sent=True detectado")
                print(f"  Significado: Mensagem já foi enviada internamente")
                print(f"  Origem: _send_and_stop() retornou este dict")
                print()

        elif isinstance(resultado, str):
            print(f"✅ Resultado é string")
            print(f"  Conteúdo: {resultado[:100]}...")
            print()
        else:
            print(f"❓ Resultado é {type(resultado).__name__}")
            print()

        # ====================================================================
        # ETAPA 4: Determinar que função foi executada
        # ====================================================================
        print("[ETAPA 4] Qual função/bloco foi executado?")
        print("-" * 80)

        if isinstance(resultado, dict) and resultado.get("already_sent") == True:
            print("✅ Origem identificada: _send_and_stop()")
            print()
            print("[TRACE]")
            print("  1. roteador_principal() foi chamado")
            print("  2. Processou 'ola'")
            print("  3. Chegou a um handler que reconheceu (provavelmente NEOEVE NEUTRA)")
            print("  4. Chamou: return await _send_and_stop(context, user_id, 'resposta')")
            print("  5. _send_and_stop retornou: {'handled': True, 'already_sent': True}")
            print()
        elif isinstance(resultado, str):
            print("❌ Resultado é string, não dict")
            print("  Isso significa que:")
            print("  - Mensagem foi retornada como texto simples")
            print("  - WhatsApp webhook (main.py) vai enviar via enviar_mensagem_whatsapp()")
            print("  - NÃO haverá already_sent=True")
            print()
        else:
            print(f"❓ Resultado anormal: {type(resultado)}")
            print()

    except Exception as e:
        print(f"[ERRO] Erro ao chamar roteador_principal: {e}")
        import traceback
        traceback.print_exc()
        print()

    # ========================================================================
    # ETAPA 5: Simular o webhook WhatsApp (main.py)
    # ========================================================================
    print("[ETAPA 5] Simular processamento webhook (main.py linhas 264-290)")
    print("-" * 80)

    if isinstance(resultado, dict):
        print(f"[CODIGO REAL DO WEBHOOK]")
        print(f"if resposta:")
        print(f"    if isinstance(resposta, dict):")
        print(f"        texto_resposta = resposta.get('resposta')")
        print(f"    elif isinstance(resposta, str):")
        print(f"        texto_resposta = resposta")
        print()

        texto_resposta = None
        if isinstance(resultado, dict):
            texto_resposta = resultado.get("resposta")
        elif isinstance(resultado, str):
            texto_resposta = resultado

        print(f"texto_resposta = {repr(texto_resposta)}")
        print()

        if texto_resposta:
            print(f"[RESULTADO]")
            print(f"  Webhoo enviaria via WhatsApp: {texto_resposta[:80]}...")
            print(f"  Status HTTP: 200 OK")
            print()
        else:
            print(f"[RESULTADO]")
            print(f"  Webhook NÃO enviaria nada")
            print(f"  Log: 'Resposta sem texto (já enviada por outro canal ou é ação interna)'")
            print()

    print("=" * 80)
    print("FIM DO TESTE")
    print("=" * 80)
    print()

if __name__ == "__main__":
    asyncio.run(teste_rastreamento())
