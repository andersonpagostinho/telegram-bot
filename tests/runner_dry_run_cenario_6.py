#!/usr/bin/env python3
"""
DRY_RUN RUNNER CENÁRIO 6 — aceitar profissional alternativo.
Valida se o router aceita a mudança de profissional mantendo horário e serviço.
"""

import asyncio
import json
import sys
import types
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

handlers_bot_stub = types.ModuleType("handlers.bot")
handlers_bot_stub.register_handlers = lambda *args, **kwargs: None
sys.modules["handlers.bot"] = handlers_bot_stub

import router.principal_router as pr

from tests.mocks.agenda_mock import AgendaMock
from tests.mocks.contexto_mock import ContextoMock
from tests.mocks.firebase_mock import FirebaseMock
from tests.mocks.gpt_mock import GPTMock
from tests.mocks.session_mock import SessionMock


async def main():
    contexto_mock = ContextoMock()
    firebase_mock = FirebaseMock()
    agenda_mock = AgendaMock()
    gpt_mock = GPTMock()
    session_mock = SessionMock()

    pr.carregar_contexto_temporario = contexto_mock.carregar_contexto_temporario
    pr.salvar_contexto_temporario = contexto_mock.salvar_contexto_temporario
    pr.pegar_sessao = session_mock.pegar_sessao
    pr.obter_id_dono = firebase_mock.obter_id_dono
    pr.buscar_subcolecao = firebase_mock.buscar_subcolecao

    async def sem_conflito_mock(*args, **kwargs):
        firebase_mock.chamadas["verificar_conflito_e_sugestoes_profissional"] = {
            "args": [str(a) for a in args],
            "kwargs": kwargs,
        }
        return {
            "conflito": False,
            "sugestoes": [],
            "profissional_alternativo": None,
        }

    pr.verificar_conflito_e_sugestoes_profissional = sem_conflito_mock
    pr.validar_horario_funcionamento = agenda_mock.validar_horario_funcionamento
    pr.gerar_resposta_p1 = gpt_mock.gerar_resposta_p1

    async def send_mock(*args, **kwargs):
        return {"mock": "send", "args": [str(a) for a in args], "kwargs": kwargs}

    async def gpt_contexto_mock(*args, **kwargs):
        return {
            "acao": "responder",
            "resposta": "Mock GPT interceptado",
            "dados": {},
        }

    if hasattr(pr, "_send_and_stop"):
        pr._send_and_stop = send_mock

    if hasattr(pr, "_send_and_stop_ctx"):
        pr._send_and_stop_ctx = send_mock

    if hasattr(pr, "chamar_gpt_com_contexto"):
        pr.chamar_gpt_com_contexto = gpt_contexto_mock

    if hasattr(pr, "chamar_gpt"):
        pr.chamar_gpt = gpt_contexto_mock

    user_id = "user_novo_teste_001"

    contexto_mock.storage[user_id] = {
        "historico_texto": ["quero agendar escova amanhã às 10", "Bruna"],
        "intencao_conversacional": "agendamento_direto",
        "tipo_ajuste_incremental": None,
        "objetivo_conversacional": "preparar_prechecagem_agendamento",
        "modo_conversa": "operacional",
        "confianca_intencao_conversacional": 85,
        "servico": "escova",
        "estado_fluxo": "aguardando_escolha_horario",
        "data_hora": "2026-06-05T10:00:00",
        "ultima_consulta": {"data_hora": "2026-06-05T10:00:00"},
        "draft_agendamento": {
            "servico": "escova",
            "data_hora": "2026-06-05T10:00:00",
            "profissional": "Bruna",
            "modo_prechecagem": True
        },
        "usuario": {
            "user_id": "user_novo_teste_001",
            "id_negocio": "dono_teste_001",
        },
        "profissionais": [
            {"nome": "Carla", "servicos": ["corte", "escova", "hidratação"]},
            {"nome": "Bruna", "servicos": ["corte", "escova", "coloração"]},
            {"nome": "Joana", "servicos": ["escova", "hidratação"]},
        ],
        "modo_escolha_horario": True,
        "horarios_sugeridos": ["10:40", "11:20"],
        "alternativa_profissional": "Carla",
        "ultima_opcao_profissionais": ["Bruna", "Carla"],
        "profissional_escolhido": "Bruna",
    }

    mensagem = "pode ser com Carla"
    update = None
    context = None

    input_data = {
        "user_id": user_id,
        "mensagem": mensagem,
        "update": update,
        "context": context,
    }

    resultado = None
    erro = None

    try:
        resultado = await pr.roteador_principal(
            user_id=user_id,
            mensagem=mensagem,
            update=update,
            context=context,
        )
    except Exception as e:
        erro = {
            "tipo": type(e).__name__,
            "mensagem": str(e),
        }

    output_data = {
        "tipo": type(resultado).__name__,
        "valor": resultado if isinstance(resultado, dict) else str(resultado),
    }

    relatorio = {
        "timestamp": datetime.now().isoformat(),
        "input": input_data,
        "output": output_data,
        "erro": erro,
        "status": "SUCESSO" if erro is None else "ERRO",
        "contexto_final": contexto_mock.get_contexto_final(user_id),
        "chamadas_mocks": {
            "contexto": contexto_mock.chamadas,
            "sessao": session_mock.chamadas,
            "firebase": firebase_mock.chamadas,
            "agenda": agenda_mock.chamadas,
            "gpt": gpt_mock.chamadas,
        },
    }

    caminho = Path(__file__).parent / "resultado_dry_run_cenario_6.json"

    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False, default=str)

    return 0 if erro is None else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
PY