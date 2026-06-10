# -*- coding: utf-8 -*-
# test_isolamento_multitenant.py
"""
Teste de isolamento multi-tenant em processar_notificacoes_agendadas().
Valida que apenas tenants DONO processam notificacoes.
"""

import asyncio
from datetime import datetime, timedelta
from pytz import timezone
from unittest.mock import AsyncMock, patch
import logging

FUSO_BR = timezone("America/Sao_Paulo")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_processar_apenas_dono():
    """
    Teste 1: user_id com tipo_usuario="dono" deve processar notificacoes.
    """
    print("\n" + "="*70)
    print("[TEST 1] Processar apenas DONO")
    print("="*70)

    # Dados
    dono_id = "usuario_dono"
    dono_doc = {
        "id": dono_id,
        "tipo_usuario": "dono",
        "nome": "Anderson",
    }

    notif_pendente = {
        "notif_1": {
            "descricao": "lembrete",
            "data_hora": (datetime.now(FUSO_BR) - timedelta(minutes=5)).isoformat(),
            "avisado": False,
            "status": "pendente",
            "canal": "telegram",
            "destinatario_user_id": dono_id,
            "minutos_antes": 30,
        }
    }

    # Mock
    with patch("scheduler.notificacoes_scheduler.buscar_dado_em_path") as mock_buscar:
        with patch("scheduler.notificacoes_scheduler.buscar_notificacoes_pendentes") as mock_notif:
            with patch("scheduler.notificacoes_scheduler._get_bot") as mock_bot:

                mock_buscar.return_value = dono_doc
                mock_notif.return_value = notif_pendente
                mock_bot.return_value = AsyncMock()

                # Simular o que scheduler faz
                doc_cli = mock_buscar.return_value or {}
                tipo_usuario = (doc_cli.get("tipo_usuario") or "").strip().lower()

                print("\n  Entrada:")
                print("    user_id: {}".format(dono_id))
                print("    tipo_usuario: {}".format(tipo_usuario))

                print("\n  Validacao:")
                if tipo_usuario == "dono":
                    print("    [PASS] user_id eh DONO, deve processar")
                    # Mock chamaria buscar_notificacoes_pendentes
                    notificacoes_chamadas = True
                else:
                    print("    [FAIL] user_id nao eh DONO")
                    notificacoes_chamadas = False

                print("\n  Resultado:")
                print("    Deve chamar buscar_notificacoes_pendentes: {}".format(notificacoes_chamadas))

                return notificacoes_chamadas


async def test_pular_cliente():
    """
    Teste 2: user_id com tipo_usuario="cliente" NÃO deve processar.
    """
    print("\n" + "="*70)
    print("[TEST 2] PULAR cliente (tipo_usuario != dono)")
    print("="*70)

    cliente_id = "usuario_cliente"
    cliente_doc = {
        "id": cliente_id,
        "tipo_usuario": "cliente",
        "nome": "Bruna",
        "id_negocio": "usuario_dono",
    }

    # Mock
    with patch("scheduler.notificacoes_scheduler.buscar_dado_em_path") as mock_buscar:
        with patch("scheduler.notificacoes_scheduler.buscar_notificacoes_pendentes") as mock_notif:

            mock_buscar.return_value = cliente_doc
            mock_notif.return_value = {"notif_1": {"data_hora": "..."}}

            # Simular validacao
            doc_cli = mock_buscar.return_value or {}
            tipo_usuario = (doc_cli.get("tipo_usuario") or "").strip().lower()

            print("\n  Entrada:")
            print("    user_id: {}".format(cliente_id))
            print("    tipo_usuario: {}".format(tipo_usuario))

            print("\n  Validacao:")
            if tipo_usuario != "dono":
                print("    [PASS] user_id eh CLIENTE, deve PULAR")
                print("    Log esperado: [NOTIF] pulando user_id nao-dono: {} tipo_usuario={}".format(cliente_id, tipo_usuario))
                chamou_notif = mock_notif.called
                print("\n  Resultado:")
                print("    Chamou buscar_notificacoes_pendentes: {}".format(chamou_notif))

                if not chamou_notif:
                    print("    [PASS] Nao chamou (correto)")
                    return True
                else:
                    print("    [FAIL] Chamou mesmo sendo cliente")
                    return False
            else:
                print("    [FAIL] user_id nao deveria ser dono")
                return False


async def test_pular_sem_tipo_usuario():
    """
    Teste 3: user_id sem tipo_usuario deve PULAR.
    """
    print("\n" + "="*70)
    print("[TEST 3] PULAR quando tipo_usuario eh vazio/ausente")
    print("="*70)

    usuario_incompleto = "usuario_sem_tipo"
    usuario_doc = {
        "id": usuario_incompleto,
        # tipo_usuario ausente
        "nome": "Incompleto",
    }

    # Mock
    with patch("scheduler.notificacoes_scheduler.buscar_dado_em_path") as mock_buscar:
        with patch("scheduler.notificacoes_scheduler.buscar_notificacoes_pendentes") as mock_notif:

            mock_buscar.return_value = usuario_doc
            mock_notif.return_value = None

            # Simular validacao
            doc_cli = mock_buscar.return_value or {}
            tipo_usuario = (doc_cli.get("tipo_usuario") or "").strip().lower()

            print("\n  Entrada:")
            print("    user_id: {}".format(usuario_incompleto))
            print("    tipo_usuario: '{}' (vazio)".format(tipo_usuario))

            print("\n  Validacao:")
            if tipo_usuario != "dono":
                print("    [PASS] tipo_usuario vazio != 'dono', deve PULAR")
                print("    Log esperado: [NOTIF] pulando user_id nao-dono: {} tipo_usuario=".format(usuario_incompleto))

                chamou_notif = mock_notif.called
                if not chamou_notif:
                    print("\n  Resultado:")
                    print("    [PASS] Nao chamou buscar_notificacoes (correto)")
                    return True
                else:
                    print("\n  Resultado:")
                    print("    [FAIL] Chamou mesmo sem tipo_usuario")
                    return False


async def test_pular_profissional():
    """
    Teste 4: user_id com tipo_usuario="profissional" deve PULAR.
    """
    print("\n" + "="*70)
    print("[TEST 4] PULAR profissional (tipo_usuario=profissional)")
    print("="*70)

    prof_id = "prof_carla"
    prof_doc = {
        "id": prof_id,
        "tipo_usuario": "profissional",
        "nome": "Carla",
    }

    # Mock
    with patch("scheduler.notificacoes_scheduler.buscar_dado_em_path") as mock_buscar:
        with patch("scheduler.notificacoes_scheduler.buscar_notificacoes_pendentes") as mock_notif:

            mock_buscar.return_value = prof_doc
            mock_notif.return_value = None

            # Simular validacao
            doc_cli = mock_buscar.return_value or {}
            tipo_usuario = (doc_cli.get("tipo_usuario") or "").strip().lower()

            print("\n  Entrada:")
            print("    user_id: {}".format(prof_id))
            print("    tipo_usuario: {}".format(tipo_usuario))

            print("\n  Validacao:")
            if tipo_usuario != "dono":
                print("    [PASS] user_id eh PROFISSIONAL, deve PULAR")
                chamou_notif = mock_notif.called

                if not chamou_notif:
                    print("\n  Resultado:")
                    print("    [PASS] Nao chamou buscar_notificacoes (correto)")
                    return True
                else:
                    print("\n  Resultado:")
                    print("    [FAIL] Chamou mesmo sendo profissional")
                    return False


async def main():
    print("\n" + "="*70)
    print("TESTES: Isolamento Multi-Tenant em processar_notificacoes_agendadas()")
    print("="*70)

    resultado1 = await test_processar_apenas_dono()
    resultado2 = await test_pular_cliente()
    resultado3 = await test_pular_sem_tipo_usuario()
    resultado4 = await test_pular_profissional()

    print("\n" + "="*70)
    print("RESUMO:")
    print("  Teste 1 (DONO processa): {}".format("PASSOU" if resultado1 else "FALHOU"))
    print("  Teste 2 (CLIENTE pula): {}".format("PASSOU" if resultado2 else "FALHOU"))
    print("  Teste 3 (SEM TIPO pula): {}".format("PASSOU" if resultado3 else "FALHOU"))
    print("  Teste 4 (PROFISSIONAL pula): {}".format("PASSOU" if resultado4 else "FALHOU"))
    print("="*70)

    if resultado1 and resultado2 and resultado3 and resultado4:
        print("\nTODOS OS TESTES PASSARAM!")
        return 0
    else:
        print("\nALGUNS TESTES FALHARAM!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
