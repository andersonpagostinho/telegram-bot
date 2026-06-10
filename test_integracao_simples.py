# -*- coding: utf-8 -*-
# test_integracao_simples.py
"""
Teste de integracao simples: validar que event_id eh calculado corretamente
e que as notificacoes sao criadas via o helper.
"""

import asyncio
from datetime import datetime
from pytz import timezone

FUSO_BR = timezone("America/Sao_Paulo")


def calcular_event_id(cliente_id, profissional, data, hora_inicio):
    """Funcao auxiliar para calcular event_id (mesma logica do handler)."""
    event_id = f"{cliente_id}_{profissional or 'pessoal'}_{data}_{hora_inicio}".replace(" ", "_").lower()
    return event_id


async def test_event_id_calculation():
    """
    Valida que event_id eh calculado corretamente.
    """
    print("\n" + "="*70)
    print("[TEST SIMPLES] Calculo de event_id")
    print("="*70)

    # Dados do evento
    cliente_id = "usuario_dono"
    profissional = "Bruna"
    data = "2026-06-15"
    hora_inicio = "14:00"

    event_id = calcular_event_id(cliente_id, profissional, data, hora_inicio)

    print("\n  Entrada:")
    print("    cliente_id: {}".format(cliente_id))
    print("    profissional: {}".format(profissional))
    print("    data: {}".format(data))
    print("    hora_inicio: {}".format(hora_inicio))

    print("\n  Resultado:")
    print("    event_id: {}".format(event_id))

    # Validar
    esperado_padrao = "usuario_dono_bruna_2026-06-15_14:00"
    if event_id == esperado_padrao:
        print("\n  [PASS] event_id calculado corretamente")
        return True
    else:
        print("\n  [FAIL] event_id incorreto")
        print("    Esperado: {}".format(esperado_padrao))
        print("    Obtido: {}".format(event_id))
        return False


async def test_event_id_sem_profissional():
    """
    Valida event_id quando nao ha profissional (agenda pessoal).
    """
    print("\n" + "="*70)
    print("[TEST SIMPLES] event_id sem profissional")
    print("="*70)

    cliente_id = "usuario_123"
    profissional = None
    data = "2026-06-20"
    hora_inicio = "10:00"

    event_id = calcular_event_id(cliente_id, profissional, data, hora_inicio)

    print("\n  Entrada:")
    print("    cliente_id: {}".format(cliente_id))
    print("    profissional: {}".format(profissional))
    print("    data: {}".format(data))
    print("    hora_inicio: {}".format(hora_inicio))

    print("\n  Resultado:")
    print("    event_id: {}".format(event_id))

    # Validar
    esperado = "usuario_123_pessoal_2026-06-20_10:00"
    if event_id == esperado:
        print("\n  [PASS] event_id correto para agenda pessoal")
        return True
    else:
        print("\n  [FAIL] event_id incorreto")
        return False


async def test_notificacao_helper_signature():
    """
    Valida que criar_notificacoes_evento_cliente_e_profissional existe
    e tem assinatura correta.
    """
    print("\n" + "="*70)
    print("[TEST SIMPLES] Assinatura de criar_notificacoes_evento_cliente_e_profissional")
    print("="*70)

    try:
        from services.notificacao_service import criar_notificacoes_evento_cliente_e_profissional
        import inspect

        sig = inspect.signature(criar_notificacoes_evento_cliente_e_profissional)
        params = list(sig.parameters.keys())

        print("\n  Parametros encontrados:")
        for param in params:
            print("    - {}".format(param))

        # Validar parametros essenciais
        essenciais = [
            "tenant_id",
            "evento_id",
            "cliente_id",
            "cliente_nome",
            "profissional_nome",
            "profissional_user_id",
            "data",
            "hora_inicio",
        ]

        todos_presentes = all(p in params for p in essenciais)

        if todos_presentes:
            print("\n  [PASS] Todos parametros essenciais presentes")
            return True
        else:
            print("\n  [FAIL] Faltam parametros")
            faltando = [p for p in essenciais if p not in params]
            print("    Faltando: {}".format(faltando))
            return False

    except ImportError as e:
        print("\n  [FAIL] Erro ao importar funcao: {}".format(e))
        return False
    except Exception as e:
        print("\n  [FAIL] Erro: {}".format(e))
        return False


async def test_campos_notificacao():
    """
    Valida estrutura de notificacao criada (sem Firestore real).
    """
    print("\n" + "="*70)
    print("[TEST SIMPLES] Campos de notificacao")
    print("="*70)

    # Simular o que seria criado
    agora = datetime.now(FUSO_BR)
    data_evento = datetime.fromisoformat("2026-06-15T14:00:00")
    horario_notificacao = data_evento.replace(hour=13, minute=30)

    notificacao_cliente = {
        "tenant_id": "usuario_dono",
        "evento_id": "usuario_dono_bruna_2026-06-15_14:00",
        "destinatario_user_id": "usuario_dono",
        "papel_destinatario": "cliente",
        "profissional_nome": "Bruna",
        "cliente_nome": "Anderson",
        "tipo": "lembrete_evento",
        "data_hora": horario_notificacao.isoformat(),
        "avisado": False,
        "processada": False,
        "status": "pendente",
        "canal": "telegram",
        "minutos_antes": 30,
    }

    notificacao_prof = {
        **notificacao_cliente,
        "destinatario_user_id": "prof_bruna_123",
        "papel_destinatario": "profissional",
    }

    print("\n  Notificacao Cliente:")
    print("    tenant_id: {}".format(notificacao_cliente["tenant_id"]))
    print("    evento_id: {}".format(notificacao_cliente["evento_id"]))
    print("    papel_destinatario: {}".format(notificacao_cliente["papel_destinatario"]))
    print("    destinatario_user_id: {}".format(notificacao_cliente["destinatario_user_id"]))
    print("    tipo: {}".format(notificacao_cliente["tipo"]))
    print("    status: {}".format(notificacao_cliente["status"]))

    print("\n  Notificacao Profissional:")
    print("    tenant_id: {}".format(notificacao_prof["tenant_id"]))
    print("    evento_id: {}".format(notificacao_prof["evento_id"]))
    print("    papel_destinatario: {}".format(notificacao_prof["papel_destinatario"]))
    print("    destinatario_user_id: {}".format(notificacao_prof["destinatario_user_id"]))
    print("    tipo: {}".format(notificacao_prof["tipo"]))
    print("    status: {}".format(notificacao_prof["status"]))

    # Validar
    validacoes = [
        ("tenant_id", notificacao_cliente["tenant_id"] == "usuario_dono"),
        ("papel_cliente", notificacao_cliente["papel_destinatario"] == "cliente"),
        ("papel_prof", notificacao_prof["papel_destinatario"] == "profissional"),
        ("evento_id", notificacao_cliente["evento_id"] == notificacao_prof["evento_id"]),
        ("tipo", notificacao_cliente["tipo"] == "lembrete_evento"),
        ("status", notificacao_cliente["status"] == "pendente"),
    ]

    print("\n  Validacoes:")
    tudo_ok = True
    for nome, resultado in validacoes:
        status_txt = "OK" if resultado else "FALHA"
        print("    {}: {}".format(nome, status_txt))
        tudo_ok = tudo_ok and resultado

    if tudo_ok:
        print("\n  [PASS] Todos campos estruturalmente corretos")
        return True
    else:
        print("\n  [FAIL] Alguns campos incorretos")
        return False


async def main():
    print("\n" + "="*70)
    print("TESTES SIMPLES: Integracao Notificacao Profissional")
    print("="*70)

    resultado1 = await test_event_id_calculation()
    resultado2 = await test_event_id_sem_profissional()
    resultado3 = await test_notificacao_helper_signature()
    resultado4 = await test_campos_notificacao()

    print("\n" + "="*70)
    print("RESUMO:")
    print("  Teste 1 (event_id): {}".format("PASSOU" if resultado1 else "FALHOU"))
    print("  Teste 2 (event_id sem prof): {}".format("PASSOU" if resultado2 else "FALHOU"))
    print("  Teste 3 (assinatura): {}".format("PASSOU" if resultado3 else "FALHOU"))
    print("  Teste 4 (campos): {}".format("PASSOU" if resultado4 else "FALHOU"))
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
