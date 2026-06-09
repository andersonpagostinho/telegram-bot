#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import copy
import sys
import types
from pathlib import Path

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
    print("="*100)
    print("AUDITORIA CENÁRIO 1 — Rajada: Serviço + Data + Hora + Profissional")
    print("="*100)

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
        return {"conflito": False}

    if hasattr(pr, "verificar_conflito_e_sugestoes_profissional"):
        pr.verificar_conflito_e_sugestoes_profissional = mock_conflict
    if hasattr(pr, "validar_horario_funcionamento"):
        pr.validar_horario_funcionamento = mock_conflict

    async def exec_mock(update, context, acao, dados):
        return {"sucesso": True}

    pr.executar_acao_gpt = exec_mock

    user_id = "user_audit_c1"
    contexto_mock.set_contexto(user_id, {})

    mensagens = [
        ("quero corte", "MSG1: Serviço"),
        ("amanhã", "MSG2: Data"),
        ("às 10", "MSG3: Hora"),
        ("Bruna", "MSG4: Profissional"),
    ]

    for i, (texto, desc) in enumerate(mensagens, 1):
        print(f"\n{'='*100}")
        print(f"[MSG {i}] {desc}")
        print(f"{'='*100}")
        print(f"Entrada: {repr(texto)}\n")

        ctx_antes = contexto_mock.get_contexto_final(user_id)
        print(f"ANTES de MSG {i}:")
        print(f"  estado_fluxo        = {ctx_antes.get('estado_fluxo')}")
        print(f"  servico             = {ctx_antes.get('servico')}")
        print(f"  profissional_escolhido = {ctx_antes.get('profissional_escolhido')}")
        print(f"  data_hora           = {ctx_antes.get('data_hora')}")
        draft = ctx_antes.get('draft_agendamento') or {}
        print(f"  draft_agendamento   = {draft}\n")

        print(f"Executando roteador...\n")

        try:
            await pr.roteador_principal(
                user_id=user_id,
                mensagem=texto,
                update=None,
                context=None
            )
        except Exception as e:
            print(f"\n❌ ERRO: {type(e).__name__}: {str(e)[:150]}\n")

        ctx_depois = contexto_mock.get_contexto_final(user_id)
        print(f"\nDEPOIS de MSG {i}:")
        print(f"  estado_fluxo        = {ctx_depois.get('estado_fluxo')}")
        print(f"  servico             = {ctx_depois.get('servico')}")
        print(f"  profissional_escolhido = {ctx_depois.get('profissional_escolhido')}")
        print(f"  data_hora           = {ctx_depois.get('data_hora')}")
        draft = ctx_depois.get('draft_agendamento') or {}
        print(f"  draft_agendamento   = {draft}")
        print(f"  draft.profissional  = {draft.get('profissional')}\n")

    print(f"\n{'='*100}")
    print("RESUMO FINAL")
    print(f"{'='*100}")
    ctx_final = contexto_mock.get_contexto_final(user_id)
    draft_final = ctx_final.get('draft_agendamento') or {}

    print(f"\nExpectativas:")
    print(f"  ✓ servico           = corte (obtido: {ctx_final.get('servico')})")
    print(f"  ✓ data_hora         = T10:00 (obtido: {ctx_final.get('data_hora')})")
    print(f"  ✓ draft_prof        = Bruna (obtido: {draft_final.get('profissional')})")
    print(f"  ✓ draft_data_hora   = T10:00 (obtido: {draft_final.get('data_hora')})")

    if draft_final.get('profissional') == 'Bruna':
        print(f"\n✅ CENÁRIO 1 PASSOU")
        return 0
    else:
        print(f"\n❌ CENÁRIO 1 FALHOU")
        print(f"\nA persistência falhou em MSG4.")
        print(f"Procure nos logs acima:")
        print(f"  - [DETECTAR_ALTERACAO] tipo=profissional")
        print(f"  - [TYPE_AUDIT] validação ok=True")
        print(f"  - Se há atribuição ctx['profissional_escolhido'] = 'Bruna'")
        print(f"  - Se há chamada a salvar_contexto_temporario depois disso")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
