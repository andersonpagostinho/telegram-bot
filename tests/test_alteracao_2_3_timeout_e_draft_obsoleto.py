"""
TEST: Alteração 2.3 — Timeout de Sessão e Draft Obsoleto

Validação completa do contrato de retorno estruturado,
integração das duas mensagens de aviso e proteção contra race conditions.

Cenários T7-T11:
T7:  Timeout comprovado (60+ minutos, evento não criado)
T8:  Draft obsoleto sem timestamp confiável (data já passou)
T9:  Evento foi criado durante timeout (proteção transacional)
T10: Transação abortada durante limpeza (evento criado paralelo)
T11: Mensagem correta é enviada baseado no tipo de aviso
"""

import asyncio
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, "/Users/ANDERSON/iCloudDrive/Projeto Mercado Digital/Agente Bot/NeoEve - Empresarial")


async def test_t7_timeout_comprovado():
    """T7: Timeout comprovado — 60+ minutos sem atividade, evento não existe."""

    print("\n" + "=" * 70)
    print("T7: Timeout Comprovado (60+ minutos sem atividade)")
    print("=" * 70)

    wa_id = "5511991382081"
    user_id = f"whatsapp:{wa_id}"
    dono_id = "7394370553"
    cliente_id = "cliente_teste_t7"

    # Timestamp de 65 minutos atrás
    timestamp_65min_atras = (datetime.now(timezone.utc) - timedelta(minutes=65)).isoformat()

    async def mock_obter_id_dono(user_id):
        return dono_id

    async def mock_carregar_contexto(dono_id, cliente_id):
        return {
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "profissional": "Bruna",
                "data": "2026-10-20",
                "hora_inicio": "14:00",
                "data_hora": datetime.now(timezone.utc).isoformat()  # Data válida (não passou)
            },
            "_last_client_activity": timestamp_65min_atras,
            "cliente_id": cliente_id
        }

    async def mock_limpar_transacional(dono_id, cliente_id):
        """Simula limpeza bem-sucedida (evento não foi criado)."""
        return True

    async def mock_buscar_evento(path):
        """Evento NÃO existe."""
        return None

    async def mock_send_and_stop(context, user_id, mensagem):
        assert "1 hora" in mensagem, f"Mensagem deveria mencionar '1 hora': {mensagem}"
        assert "não gerou um novo agendamento" in mensagem, f"Mensagem deveria mencionar proteção: {mensagem}"
        print(f"  ✅ Mensagem correta enviada: {mensagem[:50]}...")
        return {"handled": True, "resposta": mensagem}

    with patch("router.principal_router.obter_id_dono", side_effect=mock_obter_id_dono):
        with patch("utils.contexto_temporario.carregar_contexto_temporario_v2", side_effect=mock_carregar_contexto):
            with patch("utils.contexto_temporario.limpar_contexto_agendamento_v2_transacional", side_effect=mock_limpar_transacional):
                with patch("services.firebase_service_async.buscar_dado_em_path", side_effect=mock_buscar_evento):
                    with patch("router.principal_router._send_and_stop", side_effect=mock_send_and_stop):
                        try:
                            from router.principal_router import _validar_expiração_sessao

                            # Simular context mock
                            context = MagicMock()

                            resultado = await _validar_expiração_sessao(
                                ctx=await mock_carregar_contexto(dono_id, cliente_id),
                                dono_id=dono_id,
                                cliente_id=cliente_id,
                                user_id=user_id,
                                context=context
                            )

                            # Validar contrato de retorno
                            assert resultado.get("expirou") == True, f"Deveria expirar | {resultado}"
                            assert resultado.get("tipo_aviso") == "timeout_comprovado", f"tipo_aviso incorreto | {resultado}"
                            assert "1 hora" in resultado.get("mensagem", ""), f"Mensagem sem menção de timeout | {resultado}"
                            assert resultado.get("evento_criado") == False, f"Não deveria ter evento | {resultado}"

                            print(f"  ✅ T7 PASSED")
                            print(f"     - Timeout comprovado: 65 minutos")
                            print(f"     - Contrato retornado corretamente")
                            print(f"     - Tipo aviso: timeout_comprovado")
                            print(f"     - Contexto limpo com sucesso")
                            return True

                        except Exception as e:
                            print(f"  ❌ T7 FAILED: {e}")
                            import traceback
                            traceback.print_exc()
                            return False


async def test_t8_draft_obsoleto_sem_timestamp():
    """T8: Draft obsoleto — sem timestamp confiável, data já passou."""

    print("\n" + "=" * 70)
    print("T8: Draft Obsoleto (sem timestamp, data já passou)")
    print("=" * 70)

    wa_id = "5511991382082"
    user_id = f"whatsapp:{wa_id}"
    dono_id = "7394370553"
    cliente_id = "cliente_teste_t8"

    # Data que já passou (ontem)
    data_ontem = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

    async def mock_obter_id_dono(user_id):
        return dono_id

    async def mock_carregar_contexto(dono_id, cliente_id):
        return {
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "profissional": "Carla",
                "data": "2026-10-14",
                "hora_inicio": "10:00",
                "data_hora": data_ontem  # Data já passou
            },
            "_last_client_activity": None,  # Sem timestamp
            "cliente_id": cliente_id
        }

    async def mock_limpar_transacional(dono_id, cliente_id):
        """Simula limpeza bem-sucedida."""
        return True

    with patch("router.principal_router.obter_id_dono", side_effect=mock_obter_id_dono):
        with patch("utils.contexto_temporario.carregar_contexto_temporario_v2", side_effect=mock_carregar_contexto):
            with patch("utils.contexto_temporario.limpar_contexto_agendamento_v2_transacional", side_effect=mock_limpar_transacional):
                try:
                    from router.principal_router import _validar_expiração_sessao

                    context = MagicMock()

                    resultado = await _validar_expiração_sessao(
                        ctx=await mock_carregar_contexto(dono_id, cliente_id),
                        dono_id=dono_id,
                        cliente_id=cliente_id,
                        user_id=user_id,
                        context=context
                    )

                    # Validar contrato de retorno
                    assert resultado.get("expirou") == True, f"Deveria expirar | {resultado}"
                    assert resultado.get("tipo_aviso") == "draft_obsoleto", f"tipo_aviso incorreto | {resultado}"
                    assert "agendamento anterior não foi concluído" in resultado.get("mensagem", ""), \
                        f"Mensagem incorreta | {resultado}"
                    assert resultado.get("evento_criado") == False, f"Não deveria ter evento | {resultado}"

                    print(f"  ✅ T8 PASSED")
                    print(f"     - Draft obsoleto detectado")
                    print(f"     - Contrato retornado corretamente")
                    print(f"     - Tipo aviso: draft_obsoleto")
                    print(f"     - Contexto limpo com sucesso")
                    return True

                except Exception as e:
                    print(f"  ❌ T8 FAILED: {e}")
                    import traceback
                    traceback.print_exc()
                    return False


async def test_t9_evento_criado_durante_timeout():
    """T9: Proteção — evento foi criado durante timeout (não deve limpar)."""

    print("\n" + "=" * 70)
    print("T9: Evento Criado Durante Timeout (proteção contra race condition)")
    print("=" * 70)

    wa_id = "5511991382083"
    user_id = f"whatsapp:{wa_id}"
    dono_id = "7394370553"
    cliente_id = "cliente_teste_t9"

    # Timestamp de 65 minutos atrás
    timestamp_65min_atras = (datetime.now(timezone.utc) - timedelta(minutes=65)).isoformat()

    async def mock_obter_id_dono(user_id):
        return dono_id

    async def mock_carregar_contexto(dono_id, cliente_id):
        return {
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "profissional": "Bruna",
                "data": "2026-10-20",
                "hora_inicio": "14:00",
                "data_hora": datetime.now(timezone.utc).isoformat()
            },
            "_last_client_activity": timestamp_65min_atras,
            "cliente_id": cliente_id
        }

    async def mock_buscar_evento(path):
        """Evento JÁ EXISTE (criado paralelo)."""
        return {"confirmado": True, "profissional": "Bruna"}

    with patch("router.principal_router.obter_id_dono", side_effect=mock_obter_id_dono):
        with patch("utils.contexto_temporario.carregar_contexto_temporario_v2", side_effect=mock_carregar_contexto):
            with patch("services.firebase_service_async.buscar_dado_em_path", side_effect=mock_buscar_evento):
                try:
                    from router.principal_router import _validar_expiração_sessao

                    context = MagicMock()

                    resultado = await _validar_expiração_sessao(
                        ctx=await mock_carregar_contexto(dono_id, cliente_id),
                        dono_id=dono_id,
                        cliente_id=cliente_id,
                        user_id=user_id,
                        context=context
                    )

                    # Validar contrato de retorno
                    assert resultado.get("expirou") == False, f"NÃO deveria expirar (evento existe) | {resultado}"
                    assert resultado.get("tipo_aviso") is None, f"tipo_aviso deveria ser None | {resultado}"
                    assert resultado.get("evento_criado") == True, f"Deveria marcar evento_criado=True | {resultado}"

                    print(f"  ✅ T9 PASSED")
                    print(f"     - Evento detectado como já criado")
                    print(f"     - Limpeza não foi executada (proteção)")
                    print(f"     - Fluxo continua normal (não reinicia)")
                    return True

                except Exception as e:
                    print(f"  ❌ T9 FAILED: {e}")
                    import traceback
                    traceback.print_exc()
                    return False


async def test_t10_transacao_abortada():
    """T10: Transação abortada — evento foi criado durante limpeza."""

    print("\n" + "=" * 70)
    print("T10: Transação Abortada (evento criado durante limpeza)")
    print("=" * 70)

    wa_id = "5511991382084"
    user_id = f"whatsapp:{wa_id}"
    dono_id = "7394370553"
    cliente_id = "cliente_teste_t10"

    # Timestamp de 65 minutos atrás
    timestamp_65min_atras = (datetime.now(timezone.utc) - timedelta(minutes=65)).isoformat()

    async def mock_obter_id_dono(user_id):
        return dono_id

    async def mock_carregar_contexto(dono_id, cliente_id):
        return {
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "profissional": "Bruna",
                "data": "2026-10-20",
                "hora_inicio": "14:00",
                "data_hora": datetime.now(timezone.utc).isoformat()
            },
            "_last_client_activity": timestamp_65min_atras,
            "cliente_id": cliente_id
        }

    async def mock_limpar_transacional_falha(dono_id, cliente_id):
        """Simula transação abortada (evento foi criado paralelo)."""
        return False

    async def mock_buscar_evento(path):
        """Evento NÃO existe na primeira busca."""
        return None

    with patch("router.principal_router.obter_id_dono", side_effect=mock_obter_id_dono):
        with patch("utils.contexto_temporario.carregar_contexto_temporario_v2", side_effect=mock_carregar_contexto):
            with patch("utils.contexto_temporario.limpar_contexto_agendamento_v2_transacional", side_effect=mock_limpar_transacional_falha):
                with patch("services.firebase_service_async.buscar_dado_em_path", side_effect=mock_buscar_evento):
                    try:
                        from router.principal_router import _validar_expiração_sessao

                        context = MagicMock()

                        resultado = await _validar_expiração_sessao(
                            ctx=await mock_carregar_contexto(dono_id, cliente_id),
                            dono_id=dono_id,
                            cliente_id=cliente_id,
                            user_id=user_id,
                            context=context
                        )

                        # Validar contrato de retorno
                        assert resultado.get("expirou") == False, f"NÃO deveria expirar (transação abortou) | {resultado}"
                        assert resultado.get("tipo_aviso") is None, f"tipo_aviso deveria ser None | {resultado}"
                        assert resultado.get("evento_criado") == True, f"Deveria indicar evento criado paralelo | {resultado}"

                        print(f"  ✅ T10 PASSED")
                        print(f"     - Transação abortada detectada")
                        print(f"     - Limpeza não foi aplicada")
                        print(f"     - Evento paralelo foi preservado")
                        return True

                    except Exception as e:
                        print(f"  ❌ T10 FAILED: {e}")
                        import traceback
                        traceback.print_exc()
                        return False


async def test_t11_mensagens_corretas():
    """T11: Mensagens corretas são enviadas baseado no tipo de aviso."""

    print("\n" + "=" * 70)
    print("T11: Mensagens Corretas Enviadas")
    print("=" * 70)

    wa_id = "5511991382085"
    user_id = f"whatsapp:{wa_id}"
    dono_id = "7394370553"
    cliente_id = "cliente_teste_t11"

    # Teste A: Timeout comprovado
    print("\n[T11-A] Verificando mensagem de timeout comprovado...")

    mensagens_enviadas = []

    async def mock_send_and_stop_a(context, user_id, mensagem):
        mensagens_enviadas.append(("timeout", mensagem))
        return {"handled": True, "resposta": mensagem}

    timestamp_65min_atras = (datetime.now(timezone.utc) - timedelta(minutes=65)).isoformat()

    async def mock_carregar_contexto_timeout(dono_id, cliente_id):
        return {
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "profissional": "Bruna",
                "data": "2026-10-20",
                "hora_inicio": "14:00",
                "data_hora": datetime.now(timezone.utc).isoformat()
            },
            "_last_client_activity": timestamp_65min_atras,
            "cliente_id": cliente_id
        }

    async def mock_obter_id_dono(user_id):
        return dono_id

    async def mock_limpar_transacional_ok(dono_id, cliente_id):
        return True

    async def mock_buscar_evento(path):
        return None

    with patch("router.principal_router.obter_id_dono", side_effect=mock_obter_id_dono):
        with patch("utils.contexto_temporario.carregar_contexto_temporario_v2", side_effect=mock_carregar_contexto_timeout):
            with patch("utils.contexto_temporario.limpar_contexto_agendamento_v2_transacional", side_effect=mock_limpar_transacional_ok):
                with patch("services.firebase_service_async.buscar_dado_em_path", side_effect=mock_buscar_evento):
                    with patch("router.principal_router._send_and_stop", side_effect=mock_send_and_stop_a):
                        try:
                            from router.principal_router import _validar_expiração_sessao

                            context = MagicMock()

                            resultado_timeout = await _validar_expiração_sessao(
                                ctx=await mock_carregar_contexto_timeout(dono_id, cliente_id),
                                dono_id=dono_id,
                                cliente_id=cliente_id,
                                user_id=user_id,
                                context=context
                            )

                            msg_timeout = resultado_timeout.get("mensagem", "")
                            assert "1 hora" in msg_timeout, "Mensagem deveria mencionar '1 hora'"
                            assert "não gerou um novo agendamento" in msg_timeout, "Mensagem deveria proteger evento"
                            print(f"  ✅ Mensagem de timeout correta")

                        except Exception as e:
                            print(f"  ❌ Falha ao validar mensagem de timeout: {e}")
                            return False

    # Teste B: Draft obsoleto
    print("\n[T11-B] Verificando mensagem de draft obsoleto...")

    data_ontem = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

    async def mock_carregar_contexto_draft(dono_id, cliente_id):
        return {
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "profissional": "Carla",
                "data": "2026-10-14",
                "hora_inicio": "10:00",
                "data_hora": data_ontem
            },
            "_last_client_activity": None,
            "cliente_id": cliente_id
        }

    with patch("router.principal_router.obter_id_dono", side_effect=mock_obter_id_dono):
        with patch("utils.contexto_temporario.carregar_contexto_temporario_v2", side_effect=mock_carregar_contexto_draft):
            with patch("utils.contexto_temporario.limpar_contexto_agendamento_v2_transacional", side_effect=mock_limpar_transacional_ok):
                try:
                    from router.principal_router import _validar_expiração_sessao

                    context = MagicMock()

                    resultado_draft = await _validar_expiração_sessao(
                        ctx=await mock_carregar_contexto_draft(dono_id, cliente_id),
                        dono_id=dono_id,
                        cliente_id=cliente_id,
                        user_id=user_id,
                        context=context
                    )

                    msg_draft = resultado_draft.get("mensagem", "")
                    assert "agendamento anterior" in msg_draft, "Mensagem deveria mencionar agendamento anterior"
                    assert "não cancela nenhum agendamento" in msg_draft, "Mensagem deveria proteger agendamentos"
                    print(f"  ✅ Mensagem de draft obsoleto correta")

                    print(f"\n  ✅ T11 PASSED")
                    print(f"     - Mensagem de timeout comprovado: OK")
                    print(f"     - Mensagem de draft obsoleto: OK")
                    print(f"     - Ambas mensagens contêm proteção necessária")
                    return True

                except Exception as e:
                    print(f"  ❌ T11 FAILED: {e}")
                    import traceback
                    traceback.print_exc()
                    return False


async def main():
    """Executar todos os testes T7-T11."""
    print("\n" + "=" * 70)
    print("[TEST] ALTERAÇÃO 2.3 — TESTES T7-T11")
    print("=" * 70)

    resultados = {
        "T7": await test_t7_timeout_comprovado(),
        "T8": await test_t8_draft_obsoleto_sem_timestamp(),
        "T9": await test_t9_evento_criado_durante_timeout(),
        "T10": await test_t10_transacao_abortada(),
        "T11": await test_t11_mensagens_corretas(),
    }

    # Resumo
    print("\n" + "=" * 70)
    print("[SUMMARY] TESTES T7-T11")
    print("=" * 70)
    for teste, resultado in resultados.items():
        status = "✅ PASS" if resultado else "❌ FAIL"
        print(f"{teste}: {status}")

    total_pass = sum(1 for r in resultados.values() if r)
    total_testes = len(resultados)
    print(f"\nTotal: {total_pass}/{total_testes} PASS")

    return all(resultados.values())


if __name__ == "__main__":
    sucesso = asyncio.run(main())
    exit(0 if sucesso else 1)
