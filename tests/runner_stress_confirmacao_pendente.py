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
    print("=" * 100)
    print("STRESS TEST: CONFIRMAÇÃO PENDENTE")
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
        profissional = kwargs.get("profissional") or (args[2] if len(args) > 2 else None)
        servico = kwargs.get("servico") or (args[3] if len(args) > 3 else None)

        prof_servicos = {
            "Bruna": ["corte", "escova", "hidratacao"],
            "Carla": ["luzes", "escova", "hidratacao"],
            "Gloria": ["corte", "escova"],
        }

        if profissional and servico and profissional in prof_servicos:
            servicos = prof_servicos[profissional]
            incompativel = servico.lower() not in [s.lower() for s in servicos]
            if incompativel:
                return {
                    "conflito": True,
                    "sugestoes": [],
                    "profissional_alternativo": "Bruna"
                }

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

    # Simular evento criado: alterar estado para confirmado
    async def exec_mock(update, context, acao, dados):
        # Procurar qual user_id tem aguardando_confirmacao=True
        for uid in list(contexto_mock.storage.keys()):
            ctx = contexto_mock.storage.get(uid, {})
            if ctx.get("aguardando_confirmacao_agendamento") is False and acao == "criar_evento":
                # Este é nosso user_id - ele foi setado para False na linha anterior
                ctx_loaded = await contexto_mock.carregar_contexto_temporario(uid)
                ctx_loaded["estado_fluxo"] = "confirmado"
                ctx_loaded["ultima_acao"] = "criar_evento"
                await contexto_mock.salvar_contexto_temporario(uid, ctx_loaded)
                return {"sucesso": True, "evento_id": "evt_123"}
        return {"sucesso": True}

    pr.executar_acao_gpt = exec_mock

    resultados = {}

    # ===== CENÁRIO 1: Confirmação simples =====
    print("\n" + "=" * 100)
    print("CENÁRIO 1: Confirmação simples")
    print("=" * 100)

    user_id_c1 = "user_confirmacao_c1"
    contexto_c1 = {
        "servico": "corte",
        "profissional_escolhido": "Bruna",
        "data_hora": "2026-06-10T10:00:00",
        "estado_fluxo": "agendando",
        "aguardando_confirmacao_agendamento": True,
        "dados_confirmacao_agendamento": {
            "profissional": "Bruna",
            "servico": "corte",
            "data_hora": "2026-06-10T10:00:00",
            "duracao": 30,
            "descricao": "Corte com Bruna",
        },
        "draft_agendamento": {
            "profissional": "Bruna",
            "servico": "corte",
            "data_hora": "2026-06-10T10:00:00",
        },
    }
    contexto_mock.set_contexto(user_id_c1, contexto_c1)

    print("\nANTES:")
    print(f"  aguardando_confirmacao_agendamento: {contexto_c1.get('aguardando_confirmacao_agendamento')}")
    print(f"  dados_confirmacao_agendamento: {contexto_c1.get('dados_confirmacao_agendamento')}")

    await pr.roteador_principal(
        user_id=user_id_c1,
        mensagem="pode ser",
        update=None,
        context=None
    )

    ctx_c1_depois = contexto_mock.get_contexto_final(user_id_c1)
    print("\nDEPOIS:")
    print(f"  aguardando_confirmacao_agendamento: {ctx_c1_depois.get('aguardando_confirmacao_agendamento')}")
    print(f"  estado_fluxo: {ctx_c1_depois.get('estado_fluxo')}")
    print(f"  servico: {ctx_c1_depois.get('servico')}")
    print(f"  profissional_escolhido: {ctx_c1_depois.get('profissional_escolhido')}")

    validacoes_c1 = {
        "evento_criado": ctx_c1_depois.get("estado_fluxo") not in ["agendando", "aguardando_confirmacao"],
        "confirmacao_limpa": ctx_c1_depois.get("aguardando_confirmacao_agendamento") is not True,
        "servico_preservado": ctx_c1_depois.get("servico") == "corte",
        "profissional_preservado": ctx_c1_depois.get("profissional_escolhido") == "Bruna",
    }

    print("\n[VALIDACOES]")
    if all(validacoes_c1.values()):
        print("  Status: SUCESSO")
        resultados["Cenário 1"] = "SUCESSO"
    else:
        print("  Status: FALHA")
        for k, v in validacoes_c1.items():
            print(f"    - {k}: {v}")
        resultados["Cenário 1"] = f"FALHA ({', '.join([k for k, v in validacoes_c1.items() if not v])})"

    # ===== CENÁRIO 2: Negação simples =====
    print("\n" + "=" * 100)
    print("CENÁRIO 2: Negação simples")
    print("=" * 100)

    user_id_c2 = "user_confirmacao_c2"
    contexto_c2 = {
        "servico": "escova",
        "profissional_escolhido": "Gloria",
        "data_hora": "2026-06-11T14:00:00",
        "estado_fluxo": "agendando",
        "aguardando_confirmacao_agendamento": True,
        "dados_confirmacao_agendamento": {
            "profissional": "Gloria",
            "servico": "escova",
            "data_hora": "2026-06-11T14:00:00",
            "duracao": 40,
        },
    }
    contexto_mock.set_contexto(user_id_c2, contexto_c2)

    print("\nANTES:")
    print(f"  servico: {contexto_c2.get('servico')}")
    print(f"  profissional_escolhido: {contexto_c2.get('profissional_escolhido')}")
    print(f"  aguardando_confirmacao_agendamento: {contexto_c2.get('aguardando_confirmacao_agendamento')}")

    await pr.roteador_principal(
        user_id=user_id_c2,
        mensagem="não quero",
        update=None,
        context=None
    )

    ctx_c2_depois = contexto_mock.get_contexto_final(user_id_c2)
    print("\nDEPOIS:")
    print(f"  aguardando_confirmacao_agendamento: {ctx_c2_depois.get('aguardando_confirmacao_agendamento')}")
    print(f"  estado_fluxo: {ctx_c2_depois.get('estado_fluxo')}")
    print(f"  servico: {ctx_c2_depois.get('servico')}")

    validacoes_c2 = {
        "evento_nao_criado": ctx_c2_depois.get("estado_fluxo") != "confirmado",
        "confirmacao_encerrada": ctx_c2_depois.get("aguardando_confirmacao_agendamento") is not True,
    }

    print("\n[VALIDACOES]")
    if all(validacoes_c2.values()):
        print("  Status: SUCESSO")
        resultados["Cenário 2"] = "SUCESSO"
    else:
        print("  Status: FALHA")
        for k, v in validacoes_c2.items():
            print(f"    - {k}: {v}")
        resultados["Cenário 2"] = f"FALHA ({', '.join([k for k, v in validacoes_c2.items() if not v])})"

    # ===== CENÁRIO 3: Ajuste de horário =====
    print("\n" + "=" * 100)
    print("CENÁRIO 3: Ajuste de horário durante confirmação")
    print("=" * 100)

    user_id_c3 = "user_confirmacao_c3"
    contexto_c3 = {
        "servico": "corte",
        "profissional_escolhido": "Bruna",
        "data_hora": "2026-06-10T10:00:00",
        "estado_fluxo": "agendando",
        "aguardando_confirmacao_agendamento": True,
        "dados_confirmacao_agendamento": {
            "profissional": "Bruna",
            "servico": "corte",
            "data_hora": "2026-06-10T10:00:00",
        },
    }
    contexto_mock.set_contexto(user_id_c3, contexto_c3)

    print("\nANTES:")
    print(f"  data_hora: {contexto_c3.get('data_hora')}")

    await pr.roteador_principal(
        user_id=user_id_c3,
        mensagem="na verdade às 14",
        update=None,
        context=None
    )

    ctx_c3_depois = contexto_mock.get_contexto_final(user_id_c3)
    print("\nDEPOIS:")
    print(f"  data_hora: {ctx_c3_depois.get('data_hora')}")
    print(f"  estado_fluxo: {ctx_c3_depois.get('estado_fluxo')}")
    print(f"  servico: {ctx_c3_depois.get('servico')}")
    print(f"  profissional_escolhido: {ctx_c3_depois.get('profissional_escolhido')}")

    data_hora_c3 = ctx_c3_depois.get("data_hora") or ""
    validacoes_c3 = {
        "hora_alterada": "14:00" in data_hora_c3,
        "servico_preservado": ctx_c3_depois.get("servico") == "corte",
        "profissional_preservado": ctx_c3_depois.get("profissional_escolhido") == "Bruna",
        "confirmacao_ativa": ctx_c3_depois.get("aguardando_confirmacao_agendamento") in [True, None],
    }

    print("\n[VALIDACOES]")
    if all(validacoes_c3.values()):
        print("  Status: SUCESSO")
        resultados["Cenário 3"] = "SUCESSO"
    else:
        print("  Status: FALHA")
        for k, v in validacoes_c3.items():
            print(f"    - {k}: {v}")
        resultados["Cenário 3"] = f"FALHA ({', '.join([k for k, v in validacoes_c3.items() if not v])})"

    # ===== CENÁRIO 4: Troca de profissional válida =====
    print("\n" + "=" * 100)
    print("CENÁRIO 4: Troca de profissional válida")
    print("=" * 100)

    user_id_c4 = "user_confirmacao_c4"
    contexto_c4 = {
        "servico": "corte",
        "profissional_escolhido": "Bruna",
        "data_hora": "2026-06-10T10:00:00",
        "estado_fluxo": "agendando",
        "aguardando_confirmacao_agendamento": True,
        "dados_confirmacao_agendamento": {
            "profissional": "Bruna",
            "servico": "corte",
            "data_hora": "2026-06-10T10:00:00",
        },
    }
    contexto_mock.set_contexto(user_id_c4, contexto_c4)

    print("\nANTES:")
    print(f"  profissional_escolhido: {contexto_c4.get('profissional_escolhido')}")

    await pr.roteador_principal(
        user_id=user_id_c4,
        mensagem="na verdade com Gloria",
        update=None,
        context=None
    )

    ctx_c4_depois = contexto_mock.get_contexto_final(user_id_c4)
    print("\nDEPOIS:")
    print(f"  profissional_escolhido: {ctx_c4_depois.get('profissional_escolhido')}")
    print(f"  servico: {ctx_c4_depois.get('servico')}")
    print(f"  data_hora: {ctx_c4_depois.get('data_hora')}")

    validacoes_c4 = {
        "profissional_alterado": ctx_c4_depois.get("profissional_escolhido") == "Gloria",
        "servico_preservado": ctx_c4_depois.get("servico") == "corte",
        "data_hora_preservada": ctx_c4_depois.get("data_hora") == "2026-06-10T10:00:00",
    }

    print("\n[VALIDACOES]")
    if all(validacoes_c4.values()):
        print("  Status: SUCESSO")
        resultados["Cenário 4"] = "SUCESSO"
    else:
        print("  Status: FALHA")
        for k, v in validacoes_c4.items():
            print(f"    - {k}: {v}")
        resultados["Cenário 4"] = f"FALHA ({', '.join([k for k, v in validacoes_c4.items() if not v])})"

    # ===== CENÁRIO 5: Troca de profissional incompatível =====
    print("\n" + "=" * 100)
    print("CENÁRIO 5: Troca de profissional incompatível")
    print("=" * 100)

    user_id_c5 = "user_confirmacao_c5"
    contexto_c5 = {
        "servico": "corte",
        "profissional_escolhido": "Bruna",
        "data_hora": "2026-06-10T10:00:00",
        "estado_fluxo": "agendando",
        "aguardando_confirmacao_agendamento": True,
        "dados_confirmacao_agendamento": {
            "profissional": "Bruna",
            "servico": "corte",
            "data_hora": "2026-06-10T10:00:00",
        },
    }
    contexto_mock.set_contexto(user_id_c5, contexto_c5)

    print("\nANTES:")
    print(f"  profissional_escolhido: {contexto_c5.get('profissional_escolhido')}")
    print(f"  servico: {contexto_c5.get('servico')}")

    await pr.roteador_principal(
        user_id=user_id_c5,
        mensagem="na verdade com Carla",
        update=None,
        context=None
    )

    ctx_c5_depois = contexto_mock.get_contexto_final(user_id_c5)
    print("\nDEPOIS:")
    print(f"  profissional_escolhido: {ctx_c5_depois.get('profissional_escolhido')}")
    print(f"  servico: {ctx_c5_depois.get('servico')}")

    validacoes_c5 = {
        "carla_rejeitada": ctx_c5_depois.get("profissional_escolhido") != "Carla",
        "bruna_preservada": ctx_c5_depois.get("profissional_escolhido") == "Bruna",
        "servico_preservado": ctx_c5_depois.get("servico") == "corte",
    }

    print("\n[VALIDACOES]")
    if all(validacoes_c5.values()):
        print("  Status: SUCESSO")
        resultados["Cenário 5"] = "SUCESSO"
    else:
        print("  Status: FALHA")
        for k, v in validacoes_c5.items():
            print(f"    - {k}: {v}")
        resultados["Cenário 5"] = f"FALHA ({', '.join([k for k, v in validacoes_c5.items() if not v])})"

    # ===== CENÁRIO 6: Pergunta informativa =====
    print("\n" + "=" * 100)
    print("CENÁRIO 6: Pergunta informativa durante confirmação")
    print("=" * 100)

    user_id_c6 = "user_confirmacao_c6"
    contexto_c6 = {
        "servico": "hidratacao",
        "profissional_escolhido": "Bruna",
        "data_hora": "2026-06-12T15:00:00",
        "estado_fluxo": "agendando",
        "aguardando_confirmacao_agendamento": True,
        "dados_confirmacao_agendamento": {
            "profissional": "Bruna",
            "servico": "hidratacao",
            "data_hora": "2026-06-12T15:00:00",
        },
    }
    contexto_mock.set_contexto(user_id_c6, contexto_c6)

    print("\nANTES:")
    print(f"  aguardando_confirmacao_agendamento: {contexto_c6.get('aguardando_confirmacao_agendamento')}")
    print(f"  dados_confirmacao_agendamento: {contexto_c6.get('dados_confirmacao_agendamento')}")

    await pr.roteador_principal(
        user_id=user_id_c6,
        mensagem="qual o endereço?",
        update=None,
        context=None
    )

    ctx_c6_depois = contexto_mock.get_contexto_final(user_id_c6)
    print("\nDEPOIS:")
    print(f"  aguardando_confirmacao_agendamento: {ctx_c6_depois.get('aguardando_confirmacao_agendamento')}")
    print(f"  dados_confirmacao_agendamento: {ctx_c6_depois.get('dados_confirmacao_agendamento')}")

    dados_intactos = (
        ctx_c6_depois.get('dados_confirmacao_agendamento', {}).get('profissional') == 'Bruna'
        and ctx_c6_depois.get('dados_confirmacao_agendamento', {}).get('servico') == 'hidratacao'
    )

    validacoes_c6 = {
        "confirmacao_ativa": ctx_c6_depois.get("aguardando_confirmacao_agendamento") in [True, None],
        "dados_intactos": dados_intactos,
    }

    print("\n[VALIDACOES]")
    if all(validacoes_c6.values()):
        print("  Status: SUCESSO")
        resultados["Cenário 6"] = "SUCESSO"
    else:
        print("  Status: FALHA")
        for k, v in validacoes_c6.items():
            print(f"    - {k}: {v}")
        resultados["Cenário 6"] = f"FALHA ({', '.join([k for k, v in validacoes_c6.items() if not v])})"

    # ===== RESUMO FINAL =====
    print("\n" + "=" * 100)
    print("RESUMO FINAL")
    print("=" * 100)

    for cenario, resultado in resultados.items():
        status = "✅" if resultado == "SUCESSO" else "❌"
        print(f"{cenario:30} : {status} {resultado}")

    total = sum(1 for r in resultados.values() if r == "SUCESSO")
    print(f"\nTotal: {total}/{len(resultados)} cenários passaram")

    return 0 if total == len(resultados) else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
