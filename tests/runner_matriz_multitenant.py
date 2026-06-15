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
        self.acessos = []

    async def buscar_dado_em_path(self, path):
        self.acessos.append(("READ", path))
        return self.dados.get(path)

    async def salvar_dado_em_path(self, path, dados):
        self.acessos.append(("WRITE", path, list(dados.keys()) if isinstance(dados, dict) else None))
        self.dados[path] = dados
        return True

    async def atualizar_dado_em_path(self, path, dados):
        self.acessos.append(("UPDATE", path, list(dados.keys()) if isinstance(dados, dict) else None))
        if path in self.dados:
            self.dados[path].update(dados)
        else:
            self.dados[path] = dados.copy()
        return True


class ContextoMock:
    def __init__(self):
        self.storage = {}
        self.acessos = []

    async def carregar_contexto_temporario(self, user_id):
        self.acessos.append(("LOAD_CTX", user_id))
        return copy.deepcopy(self.storage.get(str(user_id), {}))

    async def salvar_contexto_temporario(self, user_id, contexto):
        self.acessos.append(("SAVE_CTX", user_id))
        self.storage[str(user_id)] = copy.deepcopy(contexto or {})
        return True

    def set_contexto(self, user_id, contexto):
        self.storage[str(user_id)] = copy.deepcopy(contexto)

    def get_contexto_final(self, user_id):
        return copy.deepcopy(self.storage.get(str(user_id), {}))


class FirebaseMock:
    async def obter_id_dono(self, actor_id):
        # Simular: cliente 7371670478 tem dono 7394370553
        if actor_id == "7371670478":
            return "7394370553"
        return actor_id

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
    print("MATRIZ FINAL MULTI-TENANT")
    print("=" * 100)

    perfis = [
        {
            "nome": "CLIENTE",
            "actor_id": "7371670478",
            "dono_id": "7394370553",
            "tipo_usuario": "cliente",
        },
        {
            "nome": "DONO",
            "actor_id": "7394370553",
            "dono_id": "7394370553",
            "tipo_usuario": "dono",
        },
    ]

    for perfil in perfis:
        print("\n" + "=" * 100)
        print(f"PERFIL: {perfil['nome']}")
        print("=" * 100)
        print(f"  actor_id: {perfil['actor_id']}")
        print(f"  dono_id: {perfil['dono_id']}")
        print(f"  tipo_usuario: {perfil['tipo_usuario']}")

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
            if acao == "criar_evento":
                for uid in list(contexto_mock.storage.keys()):
                    ctx = contexto_mock.storage.get(uid, {})
                    if ctx.get("aguardando_confirmacao_agendamento") is False:
                        ctx_loaded = await contexto_mock.carregar_contexto_temporario(uid)
                        ctx_loaded["estado_fluxo"] = "confirmado"
                        ctx_loaded["ultima_acao"] = "criar_evento"
                        await contexto_mock.salvar_contexto_temporario(uid, ctx_loaded)
                        return {"sucesso": True, "evento_id": "evt_123"}
            return {"sucesso": True}

        pr.executar_acao_gpt = exec_mock

        user_id = f"user_{perfil['nome'].lower()}"
        contexto_mock.set_contexto(user_id, {
            "actor_id": perfil["actor_id"],
            "dono_id": perfil["dono_id"],
            "tipo_usuario": perfil["tipo_usuario"],
        })

        print(f"\n[TESTE 1] Agendamento completo: corte com Bruna amanhã às 10")

        contexto_mock.acessos = []
        firebase_async_mock.acessos = []

        await pr.roteador_principal(
            user_id=user_id,
            mensagem="quero corte amanhã às 10 com Bruna",
            update=None,
            context=None
        )

        ctx_final = contexto_mock.get_contexto_final(user_id)

        print(f"\n[RESULTADO FINAL]")
        print(f"  servico: {ctx_final.get('servico')}")
        print(f"  profissional_escolhido: {ctx_final.get('profissional_escolhido')}")
        print(f"  data_hora: {ctx_final.get('data_hora')}")
        print(f"  estado_fluxo: {ctx_final.get('estado_fluxo')}")

        print(f"\n[VALIDAÇÕES MULTI-TENANT]")

        # Validar que Profissionais vêm do tenant correto
        prof_paths = [path for op, path in firebase_async_mock.acessos if "Profissionais" in path]
        prof_correto = all(f"Clientes/{perfil['dono_id']}/Profissionais" in p for p in prof_paths)
        print(f"  ✅ Profissionais lidos de Clientes/{perfil['dono_id']}: {prof_correto}" if prof_correto else f"  ❌ Profissionais incorretos: {prof_paths}")

        # Validar que Serviços vêm do tenant correto
        serv_paths = [path for op, path in firebase_async_mock.acessos if "ServicosNegocio" in path]
        serv_correto = all(f"Clientes/{perfil['dono_id']}/ServicosNegocio" in p for p in serv_paths)
        print(f"  ✅ Serviços lidos de Clientes/{perfil['dono_id']}: {serv_correto}" if serv_correto else f"  ❌ Serviços incorretos: {serv_paths}")

        # Validar isolamento de contexto temporário
        ctx_paths = [path for op, path in contexto_mock.acessos]
        ctx_user_correto = all(user_id in str(path) for path in ctx_paths)
        print(f"  ✅ Contexto isolado por user_id: {ctx_user_correto}" if ctx_user_correto else f"  ❌ Contexto não isolado")

        # Validar actor_id no contexto
        actor_preservado = ctx_final.get("actor_id") == perfil["actor_id"]
        print(f"  ✅ actor_id preservado ({perfil['actor_id']}): {actor_preservado}" if actor_preservado else f"  ❌ actor_id não preservado")

        # Validar dono_id no contexto
        dono_preservado = ctx_final.get("dono_id") == perfil["dono_id"]
        print(f"  ✅ dono_id preservado ({perfil['dono_id']}): {dono_preservado}" if dono_preservado else f"  ❌ dono_id não preservado")

        # Validar tipo_usuario
        tipo_preservado = ctx_final.get("tipo_usuario") == perfil["tipo_usuario"]
        print(f"  ✅ tipo_usuario preservado ({perfil['tipo_usuario']}): {tipo_preservado}" if tipo_preservado else f"  ❌ tipo_usuario não preservado")

    print("\n" + "=" * 100)
    print("MATRIZ MULTI-TENANT COMPLETA")
    print("=" * 100)

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
