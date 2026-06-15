#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import copy
import sys
import types
from pathlib import Path


# Configurar UTF-8 para Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

handlers_bot_stub = types.ModuleType("handlers.bot")
handlers_bot_stub.register_handlers = lambda *args, **kwargs: None
sys.modules["handlers.bot"] = handlers_bot_stub

import router.principal_router as pr
import services.firebase_service_async as firebase_async


class FirebaseAsyncMock:
    def __init__(self):
        self.dados = {}

    async def buscar_dado_em_path(self, path):
        return self.dados.get(path)

    async def salvar_dado_em_path(self, path, dados):
        self.dados[path] = dados
        return True

    async def atualizar_dado_em_path(self, path, dados):
        if path in self.dados:
            self.dados[path].update(dados)
        else:
            self.dados[path] = dados.copy()
        return True


class ContextoMock:
    def __init__(self):
        self.storage = {}

    async def carregar_contexto_temporario(self, user_id):
        return copy.deepcopy(self.storage.get(str(user_id), {}))

    async def salvar_contexto_temporario(self, user_id, contexto):
        self.storage[str(user_id)] = copy.deepcopy(contexto or {})
        return True

    def set_contexto(self, user_id, contexto):
        self.storage[str(user_id)] = copy.deepcopy(contexto)

    def get_contexto_final(self, user_id):
        return copy.deepcopy(self.storage.get(str(user_id), {}))


class FirebaseMock:
    async def obter_id_dono(self, actor_id):
        return "7394370553"

    async def buscar_subcolecao(self, path):
        path = str(path)
        if "Profissionais" in path:
            return {
                "Bruna": {"nome": "Bruna", "servicos": ["corte", "escova", "hidratacao"]},
                "Carla": {"nome": "Carla", "servicos": ["luzes", "escova", "hidratacao"]},
                "Gloria": {"nome": "Gloria", "servicos": ["corte", "escova"]},
            }
        if "ServicosNegocio" in path:
            return {
                "corte": {"nome": "corte", "duracao": 30, "preco": 50.0},
                "hidratacao": {"nome": "hidratacao", "duracao": 45, "preco": 55.0},
                "escova": {"nome": "escova", "duracao": 40, "preco": 45.0},
                "luzes": {"nome": "luzes", "duracao": 90, "preco": 120.0},
            }
        return {}


async def main():
    print("=" * 100)
    print("AUDITORIA MULTI-ENTIDADES — CENÁRIOS 1 E 6")
    print("=" * 100)

    firebase_async_mock = FirebaseAsyncMock()
    firebase_async.buscar_dado_em_path = firebase_async_mock.buscar_dado_em_path
    firebase_async.salvar_dado_em_path = firebase_async_mock.salvar_dado_em_path
    firebase_async.atualizar_dado_em_path = firebase_async_mock.atualizar_dado_em_path

    contexto_mock = ContextoMock()
    firebase_mock = FirebaseMock()

    pr.carregar_contexto_temporario = contexto_mock.carregar_contexto_temporario
    pr.salvar_contexto_temporario = contexto_mock.salvar_contexto_temporario

    if hasattr(pr, "obter_id_dono"):
        pr.obter_id_dono = firebase_mock.obter_id_dono
    if hasattr(pr, "buscar_subcolecao"):
        pr.buscar_subcolecao = firebase_mock.buscar_subcolecao

    async def mock_conflict(*args, **kwargs):
        return {"conflito": False, "sugestoes": [], "profissional_alternativo": None}

    async def mock_validar_horario(*args, **kwargs):
        return {"permitido": True, "aberto": True}

    async def mock_validar_profissional(*args, **kwargs):
        profissional = kwargs.get("profissional") or (args[1] if len(args) > 1 else None)
        servico = kwargs.get("servico") or (args[2] if len(args) > 2 else None)

        prof_servicos = {
            "Bruna": ["corte", "escova", "hidratacao"],
            "Carla": ["luzes", "escova", "hidratacao"],
            "Gloria": ["corte", "escova"],
        }

        resultado = {"ok": False, "validos": []}
        if profissional and servico and profissional in prof_servicos:
            servicos = prof_servicos[profissional]
            ok = servico.lower() in [s.lower() for s in servicos]
            resultado = {"ok": ok, "validos": servicos}

        return resultado

    if hasattr(pr, "verificar_conflito_e_sugestoes_profissional"):
        pr.verificar_conflito_e_sugestoes_profissional = mock_conflict
    if hasattr(pr, "validar_horario_funcionamento"):
        pr.validar_horario_funcionamento = mock_validar_horario
    if hasattr(pr, "validar_profissional_para_servico"):
        pr.validar_profissional_para_servico = mock_validar_profissional

    async def exec_mock(update, context, acao, dados):
        return {"sucesso": True}

    pr.executar_acao_gpt = exec_mock

    # ===== CENÁRIO 1: Dois serviços =====
    print("\n" + "=" * 100)
    print("CENÁRIO 1: Dois serviços na mesma frase")
    print("=" * 100)

    user_id_c1 = "user_audit_c1"
    contexto_mock.set_contexto(user_id_c1, {})

    print("\nMSG: 'quero corte e escova amanhã às 10'")
    print("\nRastreando fluxo...")

    await pr.roteador_principal(
        user_id=user_id_c1,
        mensagem="quero corte e escova amanhã às 10",
        update=None,
        context=None
    )

    ctx_c1_final = contexto_mock.get_contexto_final(user_id_c1)

    print("\n[RESULTADO FINAL CENÁRIO 1]")
    print(f"  servico: {ctx_c1_final.get('servico')}")
    print(f"  draft_agendamento.servico: {(ctx_c1_final.get('draft_agendamento') or {}).get('servico')}")
    print(f"  estado_fluxo: {ctx_c1_final.get('estado_fluxo')}")
    print(f"  proximo_passo esperado: perguntar_servico")
    print(f"  proximo_passo real: {ctx_c1_final.get('estado_fluxo')}")

    print("\n[INVESTIGAÇÃO CENÁRIO 1]")
    print("Procurar nos logs acima:")
    print("  1. Onde múltiplos serviços foram detectados")
    print("  2. Qual função escolheu um único serviço")
    print("  3. Linha exata de atribuição")

    # ===== CENÁRIO 6: Consulta + agendamento =====
    print("\n" + "=" * 100)
    print("CENÁRIO 6: Consulta + agendamento misturados")
    print("=" * 100)

    user_id_c6 = "user_audit_c6"
    contexto_mock.set_contexto(user_id_c6, {})

    print("\nMSG: 'quanto custa corte e dá para agendar amanhã às 10?'")
    print("\nRastreando fluxo...")

    await pr.roteador_principal(
        user_id=user_id_c6,
        mensagem="quanto custa corte e dá para agendar amanhã às 10?",
        update=None,
        context=None
    )

    ctx_c6_final = contexto_mock.get_contexto_final(user_id_c6)

    print("\n[RESULTADO FINAL CENÁRIO 6]")
    print(f"  servico: {ctx_c6_final.get('servico')}")
    print(f"  data_hora: {ctx_c6_final.get('data_hora')}")
    print(f"  estado_fluxo: {ctx_c6_final.get('estado_fluxo')}")
    print(f"  intencao_conversacional: {ctx_c6_final.get('intencao_conversacional')}")
    print(f"  objetivo_conversacional: {ctx_c6_final.get('objetivo_conversacional')}")

    print("\n[INVESTIGAÇÃO CENÁRIO 6]")
    print("Procurar nos logs acima:")
    print("  1. Se classificador marcou como 'consulta pura'")
    print("  2. Se parser detectou data/hora mas não salvou")
    print("  3. Se serviço foi detectado mas depois removido")
    print("  4. Onde o fluxo foi interceptado")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
