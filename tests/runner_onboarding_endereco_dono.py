#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ONBOARDING RUNNER — COLETA OBRIGATÓRIA DE ENDEREÇO DO DONO

Objetivo:
Validar que no primeiro acesso, o sistema coleta o endereço do negócio.

Regras:
- Se actor_id é dono e tenant não tem endereço → pergunta
- Extrai: rua + número deterministicamente
- Salva em: Clientes/{tenant_id}/configuracao/dados_negocio
- Não mistura tenants
- Não chama GPT para validar
- Se não encontrar número: pede novamente
- Se não encontrar rua: pede novamente

Casos testados:
1. Primeiro acesso sem endereço → pergunta endereço
2. Resposta válida (rua + número) → salva endereço
3. Segundo acesso com endereço salvo → não pergunta de novo
"""

import asyncio
import copy
import json
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

# Criar mocks ANTES de qualquer import
class TempContextoMock:
    def __init__(self):
        self.storage = {}

    async def carregar_contexto_temporario(self, user_id):
        resultado = copy.deepcopy(self.storage.get(str(user_id), {}))
        return resultado

    async def salvar_contexto_temporario(self, user_id, contexto):
        self.storage[str(user_id)] = copy.deepcopy(contexto or {})
        return True

_temp_ctx_mock = TempContextoMock()

# Mockar ANTES de importar qualquer coisa
import utils.contexto_temporario
utils.contexto_temporario.salvar_contexto_temporario = _temp_ctx_mock.salvar_contexto_temporario
utils.contexto_temporario.carregar_contexto_temporario = _temp_ctx_mock.carregar_contexto_temporario

# IMPORTANTE: Mockar Firebase ANTES de importar o router!
import services.firebase_service_async as firebase_async
import services.onboarding_service as onboarding_svc


class FirebaseAsyncMock:
    def __init__(self):
        self.dados_negocio = {}

    async def buscar_dado_em_path(self, path):
        """Mock de buscar_dado_em_path"""
        if path in self.dados_negocio:
            return self.dados_negocio[path]
        return None

    async def salvar_dado_em_path(self, path, dados):
        """Mock de salvar_dado_em_path"""
        self.dados_negocio[path] = dados
        return True

    async def atualizar_dado_em_path(self, path, dados):
        """Mock de atualizar_dado_em_path (merge)"""
        if path in self.dados_negocio:
            self.dados_negocio[path].update(dados)
        else:
            self.dados_negocio[path] = dados.copy()
        return True


class ContextoMock:
    def __init__(self, storage=None):
        self.storage = storage if storage is not None else {}

    def set_contexto(self, user_id, contexto):
        self.storage[str(user_id)] = copy.deepcopy(contexto)

    def get_contexto_final(self, user_id):
        resultado = copy.deepcopy(self.storage.get(str(user_id), {}))
        return resultado


class FirebaseMock:
    def __init__(self):
        self.dados_negocio = {}  # Simula Clientes/{tenant_id}/configuracao/dados_negocio

    async def obter_id_dono(self, actor_id):
        # actor_id == tenant_id quando é dono
        return actor_id

    async def buscar_subcolecao(self, path):
        return {}

    async def salvar_endereco_negocio(self, tenant_id, endereco):
        """Simula salvamento em Firestore"""
        self.dados_negocio[tenant_id] = {
            "configuracao": {
                "dados_negocio": {
                    "endereco": endereco
                }
            }
        }
        return True

    async def buscar_endereco_negocio(self, tenant_id):
        """Simula busca em Firestore"""
        if tenant_id in self.dados_negocio:
            return self.dados_negocio[tenant_id]["configuracao"]["dados_negocio"].get("endereco")
        return None


class SessionMock:
    async def pegar_sessao(self, user_id):
        return {
            "user_id": user_id,
            "chat_id": user_id,
            "message_id": None,
            "message_thread_id": None,
        }


class GPTMock:
    async def chamar_gpt(self, *args, **kwargs):
        return {"resposta": "mock_resposta"}

    async def gerar_resposta_p1(self, *args, **kwargs):
        return {"resposta": "mock_resposta"}


def resumo_ctx(ctx):
    return {
        "estado_fluxo": ctx.get("estado_fluxo"),
        "aguardando_endereco_negocio": ctx.get("aguardando_endereco_negocio"),
    }


async def main():
    firebase_async_mock = FirebaseAsyncMock()

    # Mock Firebase ANTES de importar router
    firebase_async.buscar_dado_em_path = firebase_async_mock.buscar_dado_em_path
    firebase_async.salvar_dado_em_path = firebase_async_mock.salvar_dado_em_path
    firebase_async.atualizar_dado_em_path = firebase_async_mock.atualizar_dado_em_path

    # AGORA importar o router (após mocks de Firebase)
    import router.principal_router as pr

    # Criar wrapper para ContextoMock que compartilha storage com o mock global
    contexto_mock = ContextoMock(_temp_ctx_mock.storage)

    firebase_mock = FirebaseMock()
    session_mock = SessionMock()
    gpt_mock = GPTMock()

    if hasattr(pr, "pegar_sessao"):
        pr.pegar_sessao = session_mock.pegar_sessao

    if hasattr(pr, "obter_id_dono"):
        pr.obter_id_dono = firebase_mock.obter_id_dono

    if hasattr(pr, "buscar_subcolecao"):
        pr.buscar_subcolecao = firebase_mock.buscar_subcolecao

    # Dono ID = Tenant ID
    dono_id = "7371670478"
    user_id = dono_id

    mensagens_onboarding = [
        {
            "texto": "Olá",
            "caso": "1. Primeiro acesso sem endereço",
            "esperado_estado": "aguardando_endereco_negocio",
            "esperado_pergunta": True,
        },
        {
            "texto": "Rua João Baroni número 550",
            "caso": "2. Resposta válida (rua + número)",
            "esperado_estado": "agendando",
            "esperado_salvo": {
                "rua": "Rua João Baroni",
                "numero": "550",
                "completo": "Rua João Baroni, 550"
            },
        },
    ]

    mensagens_enviadas = []
    falhas = []

    async def send_mock(*args, **kwargs):
        payload = {
            "args": [str(a) for a in args],
            "kwargs": kwargs,
        }
        mensagens_enviadas.append(payload)
        return {
            "handled": True,
            "already_sent": True,
            "mock_send": payload,
        }

    if hasattr(pr, "_send_and_stop"):
        pr._send_and_stop = send_mock

    if hasattr(pr, "_send_and_stop_ctx"):
        pr._send_and_stop_ctx = send_mock

    # Iniciar sem endereço
    contexto_mock.set_contexto(user_id, {})

    print("\n" + "=" * 90)
    print("ONBOARDING RUNNER - COLETA DE ENDEREÇO DO DONO")
    print("=" * 90)

    for i, msg_data in enumerate(mensagens_onboarding, 1):
        texto = msg_data["texto"]
        caso = msg_data["caso"]
        print(f"\nCASO {i}: {caso}")
        print(f"   Entrada: {repr(texto)}")

        mensagens_enviadas.clear()
        resultado = None
        erro = None

        try:
            resultado = await pr.roteador_principal(
                user_id=user_id,
                mensagem=texto,
                update=None,
                context=None,
            )
        except Exception as e:
            erro = {
                "tipo": type(e).__name__,
                "mensagem": str(e),
            }
            falhas.append(f"Caso {i} falhou: {e}")

        if erro:
            print(f"   ❌ ERRO: {erro['mensagem']}")
        else:
            print(f"   ✓ Processado")

        ctx_atual = contexto_mock.get_contexto_final(user_id)

        if i == 1:
            # Caso 1: Deve perguntar endereço
            if ctx_atual.get("estado_fluxo") == "aguardando_endereco_negocio":
                print(f"   ✅ Estado correto: aguardando_endereco_negocio")
            else:
                falhas.append(f"Caso 1: estado errado, esperado 'aguardando_endereco_negocio', obtido {ctx_atual.get('estado_fluxo')!r}")

            if mensagens_enviadas and "endereço" in str(mensagens_enviadas[0]).lower():
                print(f"   ✅ Perguntou endereço")
            else:
                falhas.append(f"Caso 1: não perguntou endereço")

        elif i == 2:
            # Caso 2: Deve salvar endereço (verificar em firebase_async_mock)
            path = f"Clientes/{dono_id}/configuracao/dados_negocio"
            dados_negocio = firebase_async_mock.dados_negocio.get(path, {})
            endereco_salvo = dados_negocio.get("endereco")

            if endereco_salvo:
                print(f"   ✅ Endereço salvo em Firestore:")
                print(f"      rua: {endereco_salvo.get('rua')!r}")
                print(f"      numero: {endereco_salvo.get('numero')!r}")
                print(f"      completo: {endereco_salvo.get('completo')!r}")

                if endereco_salvo.get("rua") != "Rua João Baroni":
                    falhas.append(f"Caso 2: rua incorreta, esperado 'Rua João Baroni', obtido {endereco_salvo.get('rua')!r}")
                if endereco_salvo.get("numero") != "550":
                    falhas.append(f"Caso 2: número incorreto, esperado '550', obtido {endereco_salvo.get('numero')!r}")
            else:
                falhas.append(f"Caso 2: endereço não foi salvo em Firestore")

            if ctx_atual.get("estado_fluxo") == "agendando":
                print(f"   ✅ Estado voltou a: agendando")
            else:
                falhas.append(f"Caso 2: estado errado, esperado 'agendando', obtido {ctx_atual.get('estado_fluxo')!r}")

    # Caso 3: Segundo acesso (verificar que não pergunta de novo)
    print(f"\nCASO 3: Segundo acesso com endereço salvo")
    print(f"   Entrada: 'Olá de novo'")

    mensagens_enviadas.clear()
    try:
        resultado = await pr.roteador_principal(
            user_id=user_id,
            mensagem="Olá de novo",
            update=None,
            context=None,
        )
    except Exception as e:
        falhas.append(f"Caso 3 falhou: {e}")

    ctx_atual = contexto_mock.get_contexto_final(user_id)

    # Não deve estar aguardando endereço
    if ctx_atual.get("estado_fluxo") != "aguardando_endereco_negocio":
        print(f"   ✅ Não perguntou endereço de novo (estado: {ctx_atual.get('estado_fluxo')!r})")
    else:
        falhas.append(f"Caso 3: não deveria perguntar endereço de novo")

    # Validação final
    print("\n" + "=" * 90)
    print("VALIDAÇÃO FINAL")
    print("=" * 90)

    if falhas:
        print("❌ FALHA")
        print("\nProblemas encontrados:")
        for falha in falhas:
            print(f"  • {falha}")
        status = "FALHA"
    else:
        print("✅ SUCESSO")
        status = "SUCESSO"

    print("\n" + "=" * 90)
    print("RESUMO")
    print("=" * 90)

    sucessos = 0 if falhas else 1
    num_falhas = 1 if falhas else 0

    print(f"TOTAL: 1")
    print(f"SUCESSOS: {sucessos}")
    print(f"FALHAS: {num_falhas}")

    resultado_path = Path(__file__).parent / "resultado_onboarding_endereco_dono.json"
    path_final = f"Clientes/{dono_id}/configuracao/dados_negocio"
    endereco_final = firebase_async_mock.dados_negocio.get(path_final, {}).get("endereco")

    resultado_completo = {
        "nome": "onboarding_endereco_dono",
        "descricao": "Coleta obrigatória de endereço no primeiro acesso do dono",
        "casos_testados": 3,
        "status": status,
        "falhas": falhas,
        "endereco_salvo": endereco_final,
    }

    with open(resultado_path, "w", encoding="utf-8") as f:
        json.dump([resultado_completo], f, ensure_ascii=False, indent=2)

    print(f"\nResultado salvo em: {resultado_path}")

    return 0 if num_falhas == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
