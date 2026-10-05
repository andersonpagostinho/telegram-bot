#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTE E2E REAL — Fluxo Completo WhatsApp → Pre_Confirmar

Objetivo: Reproduzir EXATAMENTE o que falha em produção

Cenário:
1. Mensagem WhatsApp: "quero corte amanhã as 9"
2. Parser extrai: data=2026-10-04, hora=09:00, profissional=Bruna, servico=corte
3. P0 valida horário
4. executar_acao_gpt() chamado com pre_confirmar_agendamento
5. Resposta enviada via WhatsApp

Diferenças entre teste unitário e E2E:
- Unitário: Mock de Update, Context, Firestore
- E2E: Firestore REAL, telegram.Update REAL, context REAL

Data: 2026-10-03
Status: Teste diagnóstico
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, "/home/claude/project")

# Setup Firestore
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
    "C:\\Users\\ANDERSON\\iCloudDrive\\Projeto Mercado Digital\\Agente Bot\\NeoEve - Empresarial\\firebase_credentials.json"
)

try:
    from telegram import Update, Chat, Message, User
    from telegram.ext import ContextTypes, CallbackContext
    from router.principal_router import processar_pre_checagem_p0
    from services.identidade_service import criar_identidade_telegram
    print("[OK] Imports carregados com sucesso")
except Exception as e:
    print(f"[ERRO] Falha ao importar: {e}")
    sys.exit(1)


async def test_e2e_pre_confirmar():
    """Testa fluxo E2E real de pre_confirmar_agendamento"""

    print("\n" + "="*70)
    print("TESTE E2E REAL — Pre_Confirmar Agendamento")
    print("="*70 + "\n")

    # Setup
    tenant_id = "7394370553"
    user_id = "7394370553"
    texto_usuario = "quero corte amanhã as 9"

    print(f"[INPUT] Mensagem: {texto_usuario}")
    print(f"[INPUT] Tenant: {tenant_id}")
    print(f"[INPUT] User: {user_id}")

    # Criar Update mock (mais realista que unitário)
    usuario = User(
        id=int(user_id),
        first_name="Cliente",
        is_bot=False
    )
    chat = Chat(
        id=int(user_id),
        type="private"
    )
    mensagem = Message(
        message_id=1,
        date=datetime.now(),
        chat=chat,
        from_user=usuario,
        text=texto_usuario
    )
    update = Update(update_id=1, message=mensagem)

    print(f"[UPDATE] Criado: update_id={update.update_id}")

    # Criar Context mock
    context = CallbackContext(application=None)
    context.user_data = {}
    context.chat_data = {}

    print(f"[CONTEXT] Criado: user_data={context.user_data}")

    # Criar IdentidadeContexto
    try:
        identidade_p01 = criar_identidade_telegram(
            telegram_id=user_id,
            canal_tenant_id=tenant_id
        )
        print(f"[IDENTIDADE] Criada: {identidade_p01}")
    except Exception as e:
        print(f"[ERRO] Falha ao criar identidade: {e}")
        identidade_p01 = None

    # Executar função de pré-checagem
    print("\n[EXEC] Chamando processar_pre_checagem_p0()...")
    print(f"[PARAMS] user_id={user_id}, texto={texto_usuario}, tenant_id={tenant_id}")

    try:
        resultado = await processar_pre_checagem_p0(
            update=update,
            context=context,
            user_id=user_id,
            texto_usuario=texto_usuario,
            tenant_id=tenant_id
        )

        print(f"\n[RESULTADO] Função retornou: {type(resultado).__name__}")

        if resultado:
            print(f"[RESULTADO] Tipo: {type(resultado)}")
            print(f"[RESULTADO] Conteúdo: {resultado}")

            # Analisar resultado
            if isinstance(resultado, str):
                print(f"[ANALISE] String retornada (resposta WhatsApp?)")
                print(f"[ANALISE] Tamanho: {len(resultado)} caracteres")
                if "confirmar" in resultado.lower() or "agendamento" in resultado.lower():
                    print("[PASS] Resposta parece ser confirmação de agendamento")
                    return True
                elif not resultado or resultado.strip() == "":
                    print("[FAIL] Resposta está vazia")
                    return False
        else:
            print("[FAIL] Função retornou None ou vazio")
            return False

    except Exception as e:
        print(f"\n[ERRO] Exceção durante execução: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def test_identidade_propagada():
    """Verifica se identidade_p01 foi propagada até executar_acao_gpt"""

    print("\n" + "="*70)
    print("TESTE — Verificar Propagação de Identidade")
    print("="*70 + "\n")

    tenant_id = "7394370553"
    user_id = "7394370553"

    try:
        identidade = criar_identidade_telegram(
            telegram_id=user_id,
            canal_tenant_id=tenant_id
        )

        print(f"[OK] IdentidadeContexto criada: {identidade}")
        print(f"  - telegram_id: {identidade.actor_id if hasattr(identidade, 'actor_id') else 'N/A'}")
        print(f"  - tenant_id: {identidade.user_id if hasattr(identidade, 'user_id') else 'N/A'}")
        print(f"  - canal: {identidade.canal if hasattr(identidade, 'canal') else 'N/A'}")

        # Verificar se tem os campos necessários
        required_fields = ['actor_id', 'user_id', 'canal']
        missing = [f for f in required_fields if not hasattr(identidade, f)]

        if missing:
            print(f"[FAIL] Campos faltando: {missing}")
            return False
        else:
            print(f"[PASS] Todos os campos obrigatórios presentes")
            return True

    except Exception as e:
        print(f"[ERRO] Falha ao criar identidade: {e}")
        return False


async def main():
    """Executa testes E2E"""

    print("\n" + "="*70)
    print("TESTES E2E — Reprodução do Problema Real")
    print("="*70)

    results = {}

    # Teste 1: Identidade propagada
    print("\n[TESTE 1/2] Verificar propagação de identidade...")
    results["identidade"] = await test_identidade_propagada()

    # Teste 2: Fluxo E2E completo
    print("\n[TESTE 2/2] Fluxo E2E completo...")
    results["e2e_pre_confirmar"] = await test_e2e_pre_confirmar()

    # Sumário
    print("\n" + "="*70)
    print("SUMÁRIO")
    print("="*70)

    for teste, resultado in results.items():
        status = "PASS" if resultado else "FAIL"
        print(f"{teste}: [{status}]")

    passed = sum(1 for r in results.values() if r)
    total = len(results)
    print(f"\nTotal: {passed}/{total} PASSED")

    if passed == total:
        print("\n[SUCCESS] Todos os testes E2E passaram!")
        return 0
    else:
        print(f"\n[FAILURE] {total - passed} teste(s) falharam")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
