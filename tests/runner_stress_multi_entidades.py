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
    print("STRESS TEST: MULTI-ENTIDADES")
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

    async def exec_mock(update, context, acao, dados):
        if acao == "criar_evento":
            for uid in list(contexto_mock.storage.keys()):
                ctx = contexto_mock.storage.get(uid, {})
                if ctx.get("aguardando_confirmacao_agendamento") is False and acao == "criar_evento":
                    ctx_loaded = await contexto_mock.carregar_contexto_temporario(uid)
                    ctx_loaded["estado_fluxo"] = "confirmado"
                    ctx_loaded["ultima_acao"] = "criar_evento"
                    await contexto_mock.salvar_contexto_temporario(uid, ctx_loaded)
                    return {"sucesso": True, "evento_id": "evt_123"}
        return {"sucesso": True}

    pr.executar_acao_gpt = exec_mock

    resultados = {}

    # ===== CENÁRIO 1: Dois serviços =====
    print("\n" + "=" * 100)
    print("CENÁRIO 1: Dois serviços na mesma frase")
    print("=" * 100)

    user_id_c1 = "user_multi_c1"
    contexto_mock.set_contexto(user_id_c1, {})

    print("\nMSG: 'quero corte e escova amanhã às 10'")
    print("\nANTES:")
    print(f"  servico: None")

    await pr.roteador_principal(
        user_id=user_id_c1,
        mensagem="quero corte e escova amanhã às 10",
        update=None,
        context=None
    )

    ctx_c1 = contexto_mock.get_contexto_final(user_id_c1)
    print("\nDEPOIS:")
    print(f"  servico: {ctx_c1.get('servico')}")
    print(f"  estado_fluxo: {ctx_c1.get('estado_fluxo')}")
    print(f"  aguardando_confirmacao: {ctx_c1.get('aguardando_confirmacao_agendamento')}")

    validacoes_c1 = {
        "nao_criou_evento": ctx_c1.get("estado_fluxo") != "confirmado",
        "perguntou_servico": ctx_c1.get("estado_fluxo") in ["aguardando_servico", "agendando"],
        "data_hora_preenchida": ctx_c1.get("data_hora") is not None,
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

    # ===== CENÁRIO 2: Serviço + profissional + horário completo =====
    print("\n" + "=" * 100)
    print("CENÁRIO 2: Serviço + profissional + horário completo")
    print("=" * 100)

    user_id_c2 = "user_multi_c2"
    contexto_mock.set_contexto(user_id_c2, {})

    print("\nMSG: 'quero corte amanhã às 10 com Bruna'")

    await pr.roteador_principal(
        user_id=user_id_c2,
        mensagem="quero corte amanhã às 10 com Bruna",
        update=None,
        context=None
    )

    ctx_c2 = contexto_mock.get_contexto_final(user_id_c2)
    print("\nDEPOIS:")
    print(f"  servico: {ctx_c2.get('servico')}")
    print(f"  profissional_escolhido: {ctx_c2.get('profissional_escolhido')}")
    print(f"  data_hora: {ctx_c2.get('data_hora')}")
    print(f"  aguardando_confirmacao: {ctx_c2.get('aguardando_confirmacao_agendamento')}")

    validacoes_c2 = {
        "servico_correto": ctx_c2.get("servico") == "corte",
        "profissional_correto": ctx_c2.get("profissional_escolhido") == "Bruna",
        "data_hora_preenchida": "10:00" in (ctx_c2.get("data_hora") or ""),
        "aguardando_ou_confirmado": ctx_c2.get("aguardando_confirmacao_agendamento") in [True, None],
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

    # ===== CENÁRIO 3: Dois horários =====
    print("\n" + "=" * 100)
    print("CENÁRIO 3: Dois horários")
    print("=" * 100)

    user_id_c3 = "user_multi_c3"
    contexto_mock.set_contexto(user_id_c3, {})

    print("\nMSG: 'quero corte amanhã às 10 ou às 14 com Bruna'")

    await pr.roteador_principal(
        user_id=user_id_c3,
        mensagem="quero corte amanhã às 10 ou às 14 com Bruna",
        update=None,
        context=None
    )

    ctx_c3 = contexto_mock.get_contexto_final(user_id_c3)
    print("\nDEPOIS:")
    print(f"  servico: {ctx_c3.get('servico')}")
    print(f"  data_hora: {ctx_c3.get('data_hora')}")
    print(f"  horarios_sugeridos: {ctx_c3.get('horarios_sugeridos')}")

    validacoes_c3 = {
        "servico_preservado": ctx_c3.get("servico") == "corte",
        "horario_selecionado": ctx_c3.get("data_hora") is not None,
        "nao_confirmado_automaticamente": ctx_c3.get("aguardando_confirmacao_agendamento") is not True,
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

    # ===== CENÁRIO 4: Dois profissionais =====
    print("\n" + "=" * 100)
    print("CENÁRIO 4: Dois profissionais aptos")
    print("=" * 100)

    user_id_c4 = "user_multi_c4"
    contexto_mock.set_contexto(user_id_c4, {})

    print("\nMSG: 'quero corte amanhã às 10 com Bruna ou Gloria'")

    await pr.roteador_principal(
        user_id=user_id_c4,
        mensagem="quero corte amanhã às 10 com Bruna ou Gloria",
        update=None,
        context=None
    )

    ctx_c4 = contexto_mock.get_contexto_final(user_id_c4)
    print("\nDEPOIS:")
    print(f"  servico: {ctx_c4.get('servico')}")
    print(f"  data_hora: {ctx_c4.get('data_hora')}")
    print(f"  profissional_escolhido: {ctx_c4.get('profissional_escolhido')}")
    print(f"  alternativa_profissional: {ctx_c4.get('alternativa_profissional')}")

    validacoes_c4 = {
        "servico_preservado": ctx_c4.get("servico") == "corte",
        "data_hora_preservada": "10:00" in (ctx_c4.get("data_hora") or ""),
        "profissional_escolhido": ctx_c4.get("profissional_escolhido") in ["Bruna", "Gloria"],
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

    # ===== CENÁRIO 5: Serviço incompatível + profissional =====
    print("\n" + "=" * 100)
    print("CENÁRIO 5: Serviço incompatível com profissional")
    print("=" * 100)

    user_id_c5 = "user_multi_c5"
    contexto_mock.set_contexto(user_id_c5, {})

    print("\nMSG: 'quero corte amanhã às 10 com Carla'")
    print("(Carla não atende corte - apenas luzes, escova, hidratacao)")

    await pr.roteador_principal(
        user_id=user_id_c5,
        mensagem="quero corte amanhã às 10 com Carla",
        update=None,
        context=None
    )

    ctx_c5 = contexto_mock.get_contexto_final(user_id_c5)
    print("\nDEPOIS:")
    print(f"  servico: {ctx_c5.get('servico')}")
    print(f"  data_hora: {ctx_c5.get('data_hora')}")
    print(f"  profissional_escolhido: {ctx_c5.get('profissional_escolhido')}")

    validacoes_c5 = {
        "carla_nao_salva": ctx_c5.get("profissional_escolhido") != "Carla",
        "servico_preservado": ctx_c5.get("servico") == "corte",
        "data_hora_preservada": "10:00" in (ctx_c5.get("data_hora") or ""),
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

    # ===== CENÁRIO 6: Consulta + agendamento =====
    print("\n" + "=" * 100)
    print("CENÁRIO 6: Consulta + agendamento misturados")
    print("=" * 100)

    user_id_c6 = "user_multi_c6"
    contexto_mock.set_contexto(user_id_c6, {})

    print("\nMSG: 'quanto custa corte e dá para agendar amanhã às 10?'")

    await pr.roteador_principal(
        user_id=user_id_c6,
        mensagem="quanto custa corte e dá para agendar amanhã às 10?",
        update=None,
        context=None
    )

    ctx_c6 = contexto_mock.get_contexto_final(user_id_c6)
    print("\nDEPOIS:")
    print(f"  servico: {ctx_c6.get('servico')}")
    print(f"  data_hora: {ctx_c6.get('data_hora')}")
    print(f"  estado_fluxo: {ctx_c6.get('estado_fluxo')}")

    validacoes_c6 = {
        "nao_criou_evento": ctx_c6.get("estado_fluxo") != "confirmado",
        "servico_detectado": ctx_c6.get("servico") == "corte",
        "data_hora_detectada": "10:00" in (ctx_c6.get("data_hora") or ""),
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
