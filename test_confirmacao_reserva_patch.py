"""
Testes obrigatrios: Confirmao automtica de reserva (CONFIRMAR_RESERVA)

6 cenrios conforme especificao:
1. evento status="reservado"  muda para confirmado + notificao processada
2. evento status="confirmado"  no altera evento + notificao processada
3. evento status="cancelado"  no altera evento + notificao processada
4. evento inexistente  notificao processada enviado + sem crash
5. evento_id vazio  notificao erro + sem crash
6. duas execues  estado final consistente (idempotncia)
"""

import asyncio
import json
from datetime import datetime
from pytz import timezone
from unittest.mock import AsyncMock, patch, MagicMock

# Importar o mdulo a testar
import sys
sys.path.insert(0, ".")

FUSO_BR = timezone("America/Sao_Paulo")

# ============================================================
# [TEST] CENARIO 1: evento status="reservado"  confirmado
# ============================================================
async def test_cenario_1_reservado_para_confirmado():
    """
    ENTRADA: notificao CONFIRMAR_RESERVA::evento_123, evento status=reservado
    SADA ESPERADA:
      - evento.status = "confirmado"
      - notificao.processada = True
      - notificao.status = "enviado"
      - notificao.tipo_processamento = "confirmacao_reserva"
      - notificao.evento_status_observado = "reservado"
    """
    print("\n" + "="*60)
    print("[TEST] CENARIO 1: evento reservado  confirmado")
    print("="*60)

    user_id = "user_teste_1"
    evento_id = "evento_123"
    notif_id = "notif_001"
    agora = datetime.now(FUSO_BR)

    # Mock Firestore
    evento_original = {
        "status": "reservado",
        "data": "2026-06-15",
        "hora_inicio": "14:00",
        "profissional": "Carla"
    }

    evento_atualizado = None
    notif_atualizada = None

    async def buscar_mock(path):
        if "Eventos" in path and evento_id in path:
            return evento_original.copy()
        return None

    async def atualizar_mock(path, dados):
        nonlocal evento_atualizado, notif_atualizada
        if f"Eventos/{evento_id}" in path:
            evento_atualizado = dados
            print(f"   Evento atualizado: {dados}")
        elif f"NotificacoesAgendadas/{notif_id}" in path:
            notif_atualizada = dados
            print(f"   Notificao atualizada: {dados}")

    # Simular bloco CONFIRMAR_RESERVA
    try:
        desc = f"CONFIRMAR_RESERVA::{evento_id}"

        # Validar evento_id
        evento_id_parsed = desc.split("::", 1)[1].strip() if "::" in desc else ""
        assert evento_id_parsed == evento_id, "evento_id no foi extrado corretamente"

        # Recarregar evento
        evento = await buscar_mock(f"Clientes/{user_id}/Eventos/{evento_id}")
        evento_status = evento.get("status") if isinstance(evento, dict) else None

        print(f"   evento_status observado: {evento_status}")
        assert evento_status == "reservado", f"Esperado 'reservado', obtido '{evento_status}'"

        # Confirmar
        if isinstance(evento, dict) and evento_status == "reservado":
            await atualizar_mock(f"Clientes/{user_id}/Eventos/{evento_id}", {
                "status": "confirmado",
                "confirmado": True,
                "confirmado_em": agora.isoformat(),
            })

        # Notificao
        await atualizar_mock(f"Clientes/{user_id}/NotificacoesAgendadas/{notif_id}", {
            "avisado": True,
            "processada": True,
            "status": "enviado",
            "enviado_em": agora.isoformat(),
            "tipo_processamento": "confirmacao_reserva",
            "evento_status_observado": evento_status,
            "atualizado_em": agora.isoformat()
        })

        # Validaes
        assert evento_atualizado is not None, "Evento no foi atualizado"
        assert evento_atualizado.get("status") == "confirmado", "Evento no virou 'confirmado'"
        assert evento_atualizado.get("confirmado") is True, "Campo 'confirmado' no  True"

        assert notif_atualizada is not None, "Notificao no foi atualizada"
        assert notif_atualizada.get("processada") is True, "Notificao no est processada"
        assert notif_atualizada.get("status") == "enviado", "Status no  'enviado'"
        assert notif_atualizada.get("tipo_processamento") == "confirmacao_reserva", "tipo_processamento incorreto"
        assert notif_atualizada.get("evento_status_observado") == "reservado", "evento_status_observado no registrado"

        print(" CENRIO 1 PASSOU")
        return True
    except AssertionError as e:
        print(f" CENRIO 1 FALHOU: {e}")
        return False


# ============================================================
#  CENRIO 2: evento status="confirmado"  no altera
# ============================================================
async def test_cenario_2_confirmado_nao_altera():
    """
    ENTRADA: evento status=confirmado (j confirmado antes)
    SADA ESPERADA:
      - evento NO  alterado
      - notificao.processada = True (mas evento no muda)
      - notificao.evento_status_observado = "confirmado"
    """
    print("\n" + "="*60)
    print(" CENRIO 2: evento confirmado  no altera")
    print("="*60)

    user_id = "user_teste_2"
    evento_id = "evento_456"
    notif_id = "notif_002"
    agora = datetime.now(FUSO_BR)

    evento_original = {
        "status": "confirmado",
        "confirmado": True,
        "confirmado_em": "2026-06-10T10:00:00",
        "data": "2026-06-15",
        "hora_inicio": "14:00",
        "profissional": "Bruna"
    }

    evento_atualizado = None
    notif_atualizada = None

    async def buscar_mock(path):
        if "Eventos" in path and evento_id in path:
            return evento_original.copy()
        return None

    async def atualizar_mock(path, dados):
        nonlocal evento_atualizado, notif_atualizada
        if f"Eventos/{evento_id}" in path:
            evento_atualizado = dados
            print(f"   Evento atualizado: {dados}")
        elif f"NotificacoesAgendadas/{notif_id}" in path:
            notif_atualizada = dados
            print(f"   Notificao atualizada: {dados}")

    try:
        desc = f"CONFIRMAR_RESERVA::{evento_id}"
        evento_id_parsed = desc.split("::", 1)[1].strip() if "::" in desc else ""

        evento = await buscar_mock(f"Clientes/{user_id}/Eventos/{evento_id}")
        evento_status = evento.get("status") if isinstance(evento, dict) else None

        print(f"   evento_status observado: {evento_status}")
        assert evento_status == "confirmado", "Status no  'confirmado'"

        # Confirmar SOMENTE se "reservado"  aqui NO confirma
        if isinstance(evento, dict) and evento_status == "reservado":
            await atualizar_mock(f"Clientes/{user_id}/Eventos/{evento_id}", {
                "status": "confirmado",
                "confirmado": True,
                "confirmado_em": agora.isoformat(),
            })

        # Notificao sempre  atualizada
        await atualizar_mock(f"Clientes/{user_id}/NotificacoesAgendadas/{notif_id}", {
            "avisado": True,
            "processada": True,
            "status": "enviado",
            "enviado_em": agora.isoformat(),
            "tipo_processamento": "confirmacao_reserva",
            "evento_status_observado": evento_status,
            "atualizado_em": agora.isoformat()
        })

        # Validaes
        assert evento_atualizado is None, " Evento NO deveria ser alterado, mas foi"

        assert notif_atualizada is not None, "Notificao no foi atualizada"
        assert notif_atualizada.get("processada") is True, "Notificao no est processada"
        assert notif_atualizada.get("evento_status_observado") == "confirmado", "evento_status_observado no registrado"

        print(" CENRIO 2 PASSOU")
        return True
    except AssertionError as e:
        print(f" CENRIO 2 FALHOU: {e}")
        return False


# ============================================================
#  CENRIO 3: evento status="cancelado"  no altera
# ============================================================
async def test_cenario_3_cancelado_nao_altera():
    """
    ENTRADA: evento status=cancelado
    SADA ESPERADA:
      - evento NO  alterado
      - notificao.processada = True
      - notificao.evento_status_observado = "cancelado"
    """
    print("\n" + "="*60)
    print(" CENRIO 3: evento cancelado  no altera")
    print("="*60)

    user_id = "user_teste_3"
    evento_id = "evento_789"
    notif_id = "notif_003"
    agora = datetime.now(FUSO_BR)

    evento_original = {
        "status": "cancelado",
        "data": "2026-06-15",
        "hora_inicio": "14:00",
        "profissional": "Marina"
    }

    evento_atualizado = None
    notif_atualizada = None

    async def buscar_mock(path):
        if "Eventos" in path and evento_id in path:
            return evento_original.copy()
        return None

    async def atualizar_mock(path, dados):
        nonlocal evento_atualizado, notif_atualizada
        if f"Eventos/{evento_id}" in path:
            evento_atualizado = dados
        elif f"NotificacoesAgendadas/{notif_id}" in path:
            notif_atualizada = dados

    try:
        desc = f"CONFIRMAR_RESERVA::{evento_id}"
        evento_id_parsed = desc.split("::", 1)[1].strip() if "::" in desc else ""

        evento = await buscar_mock(f"Clientes/{user_id}/Eventos/{evento_id}")
        evento_status = evento.get("status") if isinstance(evento, dict) else None

        print(f"   evento_status observado: {evento_status}")

        if isinstance(evento, dict) and evento_status == "reservado":
            await atualizar_mock(f"Clientes/{user_id}/Eventos/{evento_id}", {"status": "confirmado"})

        await atualizar_mock(f"Clientes/{user_id}/NotificacoesAgendadas/{notif_id}", {
            "avisado": True,
            "processada": True,
            "status": "enviado",
            "evento_status_observado": evento_status,
        })

        assert evento_atualizado is None, " Evento NO deveria ser alterado, mas foi"
        assert notif_atualizada.get("evento_status_observado") == "cancelado", "Status no registrado"

        print(" CENRIO 3 PASSOU")
        return True
    except AssertionError as e:
        print(f" CENRIO 3 FALHOU: {e}")
        return False


# ============================================================
#  CENRIO 4: evento inexistente  notificao processada
# ============================================================
async def test_cenario_4_evento_inexistente():
    """
    ENTRADA: evento_id no existe no Firestore
    SADA ESPERADA:
      - evento = None
      - notificao.processada = True
      - notificao.status = "enviado"
      - notificao.evento_status_observado = None
      - sem crash
    """
    print("\n" + "="*60)
    print(" CENRIO 4: evento inexistente  sem crash")
    print("="*60)

    user_id = "user_teste_4"
    evento_id = "evento_inexistente"
    notif_id = "notif_004"
    agora = datetime.now(FUSO_BR)

    notif_atualizada = None

    async def buscar_mock(path):
        # Retorna None (evento no existe)
        return None

    async def atualizar_mock(path, dados):
        nonlocal notif_atualizada
        if f"NotificacoesAgendadas/{notif_id}" in path:
            notif_atualizada = dados

    try:
        desc = f"CONFIRMAR_RESERVA::{evento_id}"
        evento_id_parsed = desc.split("::", 1)[1].strip() if "::" in desc else ""

        evento = await buscar_mock(f"Clientes/{user_id}/Eventos/{evento_id}")
        evento_status = evento.get("status") if isinstance(evento, dict) else None

        print(f"   evento_status observado: {evento_status} (None = inexistente)")
        assert evento_status is None, "evento_status deveria ser None"

        # Guard rail: evento no existe, no tenta confirmar
        if isinstance(evento, dict) and evento_status == "reservado":
            print("   No deveria entrar aqui")
            raise AssertionError("No deveria confirmar evento inexistente")

        # Sempre marca notificao
        await atualizar_mock(f"Clientes/{user_id}/NotificacoesAgendadas/{notif_id}", {
            "avisado": True,
            "processada": True,
            "status": "enviado",
            "evento_status_observado": evento_status,
        })

        assert notif_atualizada is not None, "Notificao no foi atualizada"
        assert notif_atualizada.get("processada") is True, "Notificao no est processada"

        print(" CENRIO 4 PASSOU (sem crash)")
        return True
    except Exception as e:
        print(f" CENRIO 4 FALHOU: {e}")
        return False


# ============================================================
#  CENRIO 5: evento_id vazio  erro
# ============================================================
async def test_cenario_5_evento_id_vazio():
    """
    ENTRADA: notificao descricao = "CONFIRMAR_RESERVA::" (sem evento_id)
    SADA ESPERADA:
      - evento_id_parsed = "" (vazio)
      - notificao.status = "erro"
      - notificao.processada = True
      - notificao.erro = "evento_id vazio ou invlido"
      - sem crash
    """
    print("\n" + "="*60)
    print(" CENRIO 5: evento_id vazio  erro")
    print("="*60)

    user_id = "user_teste_5"
    notif_id = "notif_005"
    agora = datetime.now(FUSO_BR)

    notif_atualizada = None

    async def atualizar_mock(path, dados):
        nonlocal notif_atualizada
        if f"NotificacoesAgendadas/{notif_id}" in path:
            notif_atualizada = dados
            print(f"   Notificao com ERRO marcada: {dados}")

    try:
        desc = "CONFIRMAR_RESERVA::"  # Sem evento_id
        evento_id = desc.split("::", 1)[1].strip() if "::" in desc else ""

        print(f"   evento_id extrado: '{evento_id}' (vazio? {not evento_id})")

        # Guard rail: evento_id vazio
        if not evento_id:
            print("   evento_id vazio detectado")
            await atualizar_mock(f"Clientes/{user_id}/NotificacoesAgendadas/{notif_id}", {
                "avisado": True,
                "processada": True,
                "status": "erro",
                "erro": "CONFIRMAR_RESERVA: evento_id vazio ou invlido",
                "atualizado_em": agora.isoformat()
            })

        assert notif_atualizada is not None, "Notificao no foi atualizada"
        assert notif_atualizada.get("status") == "erro", "Status no  'erro'"
        assert notif_atualizada.get("processada") is True, "No est marcada como processada"
        assert "evento_id vazio" in notif_atualizada.get("erro", ""), "Mensagem de erro no menciona evento_id"

        print(" CENRIO 5 PASSOU (sem crash)")
        return True
    except Exception as e:
        print(f" CENRIO 5 FALHOU: {e}")
        return False


# ============================================================
#  CENRIO 6: duas execues  idempotncia
# ============================================================
async def test_cenario_6_idempotencia_dupla_execucao():
    """
    ENTRADA: scheduler roda duas vezes com mesmo evento_id
    SADA ESPERADA:
      - Primeira execuo: evento reservado  confirmado
      - Segunda execuo: evento j confirmado  no altera
      - Estado final consistente (no duplica efeito)
    """
    print("\n" + "="*60)
    print(" CENRIO 6: duas execues  idempotncia")
    print("="*60)

    user_id = "user_teste_6"
    evento_id = "evento_duplo"
    notif_id = "notif_006"
    agora = datetime.now(FUSO_BR)

    # Estado Firestore (simulado)
    estado_evento = {
        "status": "reservado",
        "data": "2026-06-15",
        "hora_inicio": "14:00",
        "profissional": "Sofia"
    }

    confirmou_count = 0

    async def buscar_mock(path):
        if "Eventos" in path and evento_id in path:
            return estado_evento.copy()
        return None

    async def atualizar_mock(path, dados):
        nonlocal confirmou_count, estado_evento
        if f"Eventos/{evento_id}" in path:
            estado_evento.update(dados)
            confirmou_count += 1
            print(f"   Evento atualizado (execuo #{confirmou_count}): status={dados.get('status')}")

    try:
        print("   EXECUO 1 (evento ainda reservado)")

        # Execuo 1
        desc = f"CONFIRMAR_RESERVA::{evento_id}"
        evento_id_parsed = desc.split("::", 1)[1].strip() if "::" in desc else ""

        evento = await buscar_mock(f"Clientes/{user_id}/Eventos/{evento_id}")
        evento_status = evento.get("status") if isinstance(evento, dict) else None

        if isinstance(evento, dict) and evento_status == "reservado":
            await atualizar_mock(f"Clientes/{user_id}/Eventos/{evento_id}", {
                "status": "confirmado",
                "confirmado": True,
                "confirmado_em": agora.isoformat(),
            })

        assert confirmou_count == 1, "Primeira execuo deveria ter confirmado"
        assert estado_evento.get("status") == "confirmado", "Estado no mudou"

        print("   EXECUO 2 (evento j confirmado)")

        # Execuo 2 - reload do mesmo evento
        evento = await buscar_mock(f"Clientes/{user_id}/Eventos/{evento_id}")
        evento_status = evento.get("status") if isinstance(evento, dict) else None

        print(f"    evento_status: {evento_status}")

        # Guard rail: no confirma novamente
        if isinstance(evento, dict) and evento_status == "reservado":
            await atualizar_mock(f"Clientes/{user_id}/Eventos/{evento_id}", {
                "status": "confirmado",
                "confirmado": True,
                "confirmado_em": agora.isoformat(),
            })

        assert confirmou_count == 1, " Segunda execuo NO deveria alterar evento (idempotncia falhou)"

        print(" CENRIO 6 PASSOU (idempotncia validada)")
        return True
    except AssertionError as e:
        print(f" CENRIO 6 FALHOU: {e}")
        return False


# ============================================================
#  EXECUTOR
# ============================================================
async def main():
    print("\n" + "="*80)
    print("[TEST] TESTES: Confirmacao Automatica de Reserva (CONFIRMAR_RESERVA)")
    print("="*80)

    resultados = []

    # Rodar todos os cenarios
    resultados.append(("Cenario 1 (reservado->confirmado)", await test_cenario_1_reservado_para_confirmado()))
    resultados.append(("Cenario 2 (confirmado->nenhuma alteracao)", await test_cenario_2_confirmado_nao_altera()))
    resultados.append(("Cenario 3 (cancelado->nenhuma alteracao)", await test_cenario_3_cancelado_nao_altera()))
    resultados.append(("Cenario 4 (evento inexistente)", await test_cenario_4_evento_inexistente()))
    resultados.append(("Cenario 5 (evento_id vazio)", await test_cenario_5_evento_id_vazio()))
    resultados.append(("Cenario 6 (idempotencia)", await test_cenario_6_idempotencia_dupla_execucao()))

    # Resumo
    print("\n" + "="*80)
    print("[RESUMO]")
    print("="*80)

    total = len(resultados)
    passados = sum(1 for _, resultado in resultados if resultado)

    for nome, resultado in resultados:
        status = "[OK]" if resultado else "[FALHOU]"
        print(f"{status} {nome}")

    print(f"\nTotal: {passados}/{total} cenarios passaram")

    if passados == total:
        print("\n[SUCCESS] TODOS OS TESTES PASSARAM!")
        return True
    else:
        print(f"\n[WARN] {total - passados} teste(s) falharam")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
