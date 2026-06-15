# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
DRY_RUN RUNNER — Executa cenário com mocks instalados
Estratégia: monkey-patch direto no namespace do router
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path


# Configurar UTF-8 para Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent.parent))

import types

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
    pr.verificar_conflito_e_sugestoes_profissional = (
        firebase_mock.verificar_conflito_e_sugestoes_profissional
    )
    pr.validar_horario_funcionamento = agenda_mock.validar_horario_funcionamento
    pr.gerar_resposta_p1 = gpt_mock.gerar_resposta_p1

    async def send_mock(*args, **kwargs):
        return {"mock": "send", "args": [str(a) for a in args], "kwargs": kwargs}

    async def gpt_contexto_mock(*args, **kwargs):
        return {
            "acao": "responder",
            "resposta": "Mock GPT interceptado",
            "dados": {}
        }

    if hasattr(pr, "_send_and_stop"):
        pr._send_and_stop = send_mock

    if hasattr(pr, "chamar_gpt_com_contexto"):
        pr.chamar_gpt_com_contexto = gpt_contexto_mock

    if hasattr(pr, "chamar_gpt"):
        pr.chamar_gpt = gpt_contexto_mock

    user_id = "user_novo_teste_001"
    mensagem = "quero agendar escova amanhã às 10"
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

    caminho = Path(__file__).parent / "resultado_dry_run.json"

    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False, default=str)

    return 0 if erro is None else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
PY