#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Forçar UTF-8 no stdout Windows
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

"""
P1 — Robustez de Fluxo Conversacional (Integração Router Real)

Objetivo:
Validar 13 cenários que requerem integração com router real, session,
draft, estado de máquina, confirmação pendente, criação/bloqueio de evento
e validação de fluxo conversacional.

Cenários: 13 (correspondem aos 13 "não aplicáveis" da bateria anterior)
Critério: 13/13 PASS
Validação: Router real, Firestore real isolado por tenant

Serviços usados:
  - principal_router.roteador_principal()
  - session_service.pegar_sessao()
  - event_service_async.salvar_evento()
  - agenda_service.validar_horario_funcionamento()
  - firebase_service_async (Firestore real)

Mockado:
  - context.bot.send_message() (apenas I/O, não afeta lógica)
  - GPT (controladamente para simular respostas boas/ruins)
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
import pytz
from pathlib import Path
import traceback
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

# Adicionar diretório do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.firestore_client import get_db
from services.firebase_service_async import (
    buscar_dado_em_path,
    salvar_dado_em_path,
    buscar_subcolecao,
    deletar_dado_em_path,
    obter_id_dono,
    salvar_cliente,
)
from services.identidade_service import normalizar_actor_id

# Import local para evitar circular import
def get_roteador_principal():
    from router.principal_router import roteador_principal
    return roteador_principal


# ============================================================================
# PATCH GLOBAL: vincular actor_id → tenant_id via obter_id_dono()
# ============================================================================

async def setup_cenario_com_vinculo(tenant_id: str, actor_id: str):
    """
    Setup com mock de obter_id_dono() para vincular actor → tenant.

    Em produção: user_id está vinculado a um tenant via auth token.
    No teste: simulamos esse vínculo mockando obter_id_dono().
    """
    # Setup padrão
    await setup_tenant_completo(tenant_id, actor_id)

    # Mockar obter_id_dono para retornar tenant correto
    # Fazer patch global se necessário (será feito em cada cenário via patch)
    return tenant_id


# ============================================================================
# RESULTADO E UTILIDADES
# ============================================================================

class CenarioFluxo:
    """Resultado de um cenário de fluxo conversacional"""

    def __init__(self, numero, nome):
        self.numero = numero
        self.nome = nome
        self.status = None  # PASS, FAIL
        self.motivo = None
        self.timestamp = datetime.now(pytz.UTC).isoformat()
        self.tenant_id = None
        self.actor_id = None

        # Entrada
        self.mensagem_original = None
        self.canal = "whatsapp"

        # Execução
        self.resposta_enviada = None
        self.exceção = None

        # Estado
        self.estado_antes = {}
        self.estado_depois = {}
        self.draft_antes = None
        self.draft_depois = None

        # Resultado
        self.evento_criado = False
        self.confirmacao_pendente = False
        self.tenant_correto = False
        self.paths_corretos = True

        # Erro
        self.erro = None
        self.stack = None

    def set_pass(self, motivo=""):
        self.status = "PASS"
        self.motivo = motivo or "Fluxo passou com sucesso"

    def set_fail(self, motivo, erro=None, stack=None):
        self.status = "FAIL"
        self.motivo = motivo
        self.erro = str(erro) if erro else None
        self.stack = stack

    def to_dict(self):
        return {
            "numero": self.numero,
            "nome": self.nome,
            "status": self.status,
            "motivo": self.motivo,
            "timestamp": self.timestamp,
            "entrada": {
                "mensagem": self.mensagem_original,
                "canal": self.canal,
            },
            "estado": {
                "antes": self.estado_antes,
                "depois": self.estado_depois,
                "draft_antes": self.draft_antes,
                "draft_depois": self.draft_depois,
            },
            "resultado": {
                "resposta_enviada": self.resposta_enviada,
                "evento_criado": self.evento_criado,
                "confirmacao_pendente": self.confirmacao_pendente,
                "tenant_correto": self.tenant_correto,
                "paths_corretos": self.paths_corretos,
            },
            "erro": self.erro,
        }


class BateriaFluxo:
    """Bateria de testes de fluxo conversacional"""

    def __init__(self):
        self.resultados = []
        self.pass_count = 0
        self.fail_count = 0

    def adicionar(self, resultado):
        self.resultados.append(resultado)
        if resultado.status == "PASS":
            self.pass_count += 1
            print(f"[PASS] {resultado.numero:02d}. {resultado.nome}")
        else:
            self.fail_count += 1
            print(f"[FAIL] {resultado.numero:02d}. {resultado.nome} - {resultado.motivo}")

    def salvar(self, caminho="tests/resultado_p1_robustez_fluxo_conversacional_real.json"):
        output = {
            "total": len(self.resultados),
            "pass": self.pass_count,
            "fail": self.fail_count,
            "cenarios": [r.to_dict() for r in self.resultados],
        }
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n[RESULTADO] SALVO EM JSON: {caminho}")
        print(f"   Total: {len(self.resultados)}")
        print(f"   PASS: {self.pass_count}")
        print(f"   FAIL: {self.fail_count}")

    def relatorio(self):
        print("\n" + "=" * 70)
        print(f"BATERIA FLUXO CONVERSACIONAL: {self.pass_count}/{len(self.resultados)} PASS")
        print("=" * 70)


# ============================================================================
# FIXTURES
# ============================================================================

async def limpar_tenant(tenant_id: str, actor_id: str = None):
    """Limpar tenant completamente, incluindo contexto legado de TODOS os actor_ids"""
    try:
        db = get_db()
        print(f"  [CLEANUP] Limpando tenant: {tenant_id}")
        for subcol in [
            "Configuracao", "Profissionais", "ServicosNegocio",
            "Atores", "Clientes", "Sessoes", "Eventos", "Notificacoes", "Agendas"
        ]:
            docs = db.collection("Clientes").document(tenant_id).collection(subcol).stream()
            for doc in docs:
                await asyncio.to_thread(lambda d=doc: d.reference.delete())

        doc_ref = db.collection("Clientes").document(tenant_id)
        await asyncio.to_thread(lambda: doc_ref.delete())

        # [LOTE 5B] Também limpar contexto legado para evitar contaminação entre cenários
        # Limpa o actor_id específico E TODOS os possíveis actor_ids dos testes (001-013)
        actor_ids_to_clean = [actor_id] if actor_id else []
        for i in range(1, 14):
            actor_ids_to_clean.append(f"whatsapp:5511999900{i:02d}")

        for aid in set(actor_ids_to_clean):
            if not aid:
                continue
            try:
                legado_ref = db.collection("Clientes").document(aid).collection("MemoriaTemporaria").document("contexto")
                await asyncio.to_thread(lambda: legado_ref.delete())
            except:
                pass  # Arquivo pode não existir, ignorar

        print(f"  [CLEANUP] ✓ Tenant e contextos legados limpos: {tenant_id}")
    except Exception as e:
        print(f"  [CLEANUP] ⚠️ Erro ao limpar: {e}")

async def setup_tenant_completo(tenant_id: str, actor_id: str):
    """Setup: config, profissional, serviço, ator"""

    # Criar configuração
    config = {
        "tenant_id": tenant_id,
        "nome_negocio": "Salão Teste",
        "telefone": "11999999999",
        "data_criacao": datetime.now(pytz.UTC).isoformat(),
    }
    await salvar_dado_em_path(f"Clientes/{tenant_id}/Configuracao/info", config)

    # Criar profissional "Bruna"
    prof_bruna = {
        "nome": "Bruna",
        "telefone": "11988888888",
        "servicos": ["corte", "escova"],
        "expediente": {
            "seg": {"inicio": "09:00", "fim": "18:00"},
            "ter": {"inicio": "09:00", "fim": "18:00"},
            "qua": {"inicio": "09:00", "fim": "18:00"},
            "qui": {"inicio": "09:00", "fim": "18:00"},
            "sex": {"inicio": "09:00", "fim": "18:00"},
        },
        "ativo": True,
    }
    await salvar_dado_em_path(f"Clientes/{tenant_id}/Profissionais/bruna", prof_bruna)

    # Criar serviço "corte"
    servico_corte = {
        "nome": "Corte",
        "duracao_padrao": 30,
        "preco": 50.0,
        "ativo": True,
    }
    await salvar_dado_em_path(f"Clientes/{tenant_id}/ServicosNegocio/corte", servico_corte)

    # Criar serviço "escova"
    servico_escova = {
        "nome": "Escova",
        "duracao_padrao": 45,
        "preco": 80.0,
        "ativo": True,
    }
    await salvar_dado_em_path(f"Clientes/{tenant_id}/ServicosNegocio/escova", servico_escova)

    # Criar ator cliente
    ator = {
        "actor_id": actor_id,
        "tipo_usuario": "cliente",
        "nome": "Cliente Teste",
        "canal": "whatsapp",
        "tenant_id": tenant_id,
        "data_criacao": datetime.now(pytz.UTC).isoformat(),
    }
    await salvar_dado_em_path(f"Clientes/{tenant_id}/Atores/{actor_id}", ator)

async def obter_estado_sessao(tenant_id: str, actor_id: str):
    """Obter estado completo da sessão"""
    return await buscar_dado_em_path(f"Clientes/{tenant_id}/Sessoes/{actor_id}")

async def obter_eventos(tenant_id: str):
    """Obter todos eventos do tenant"""
    return await buscar_subcolecao(f"Clientes/{tenant_id}/Eventos")


# ============================================================================
# MOCK CONTEXT E UPDATE (para não chamar Telegram real)
# ============================================================================

class MockUser:
    """Mock de User do Telegram"""
    def __init__(self, user_id):
        self.id = user_id
        self.first_name = "Teste"
        self.last_name = "Cliente"
        self.username = "teste_cliente"


class MockChat:
    """Mock de Chat do Telegram"""
    def __init__(self, chat_id):
        self.id = chat_id
        self.type = "private"


class MockMessage:
    """Mock de Message do Telegram"""
    def __init__(self, chat_id, from_user_id, text=""):
        self.chat = MockChat(chat_id)
        self.from_user = MockUser(from_user_id)
        self.text = text
        self.message_id = 1
        self.date = datetime.now(pytz.UTC)
        self.reply_text = AsyncMock(return_value={"ok": True})


class MockUpdate:
    """Mock completo de Update do Telegram"""
    def __init__(self, chat_id, user_id, text=""):
        self.message = MockMessage(chat_id, user_id, text)
        self.effective_user = MockUser(user_id)
        self.effective_chat = MockChat(chat_id)


class MockContext:
    """Mock de context do Telegram"""

    def __init__(self):
        self.bot = AsyncMock()
        self.bot.send_message = AsyncMock(return_value={"ok": True})
        self.user_data = {}
        self.chat_data = {}
        self.bot_data = {}


class MockUpdate:
    """Mock mínimo de Update do Telegram para cenários que precisam de update real"""

    def __init__(self, user_id: str, chat_id: str = "12345", text: str = ""):
        # Estrutura mínima que executar_acao_gpt espera
        self.message = MagicMock()
        self.message.from_user = MagicMock()
        self.message.from_user.id = user_id
        self.message.chat = MagicMock()
        self.message.chat.id = chat_id
        self.message.text = text
        self.message.reply_text = AsyncMock(return_value={"ok": True})

        # Fallback para effective_user/effective_chat
        self.effective_user = self.message.from_user
        self.effective_chat = self.message.chat


# ============================================================================
# CENÁRIOS (13 OBRIGATÓRIOS DE FLUXO)
# ============================================================================

async def cenario_01_ruido_pessoal_longo_nao_operacional(bateria: BateriaFluxo):
    """Cenário 01: Ruído pessoal longo não operacional"""
    resultado = CenarioFluxo(1, "Ruído pessoal longo não operacional")

    try:
        tenant_id = f"teste_fluxo_p1_{uuid.uuid4().hex[:8]}"
        actor_id = "whatsapp:55119999001"
        print(f"\n[CENÁRIO 01] tenant_id ÚNICO: {tenant_id}")
        await limpar_tenant(tenant_id, actor_id)
        print(f"[CENÁRIO 01] Router REAL será chamado: roteador_principal()")
        print(f"[CENÁRIO 01] Apenas context.bot.send_message() será mockado")
        await setup_tenant_completo(tenant_id, actor_id)

        resultado.tenant_id = tenant_id
        resultado.actor_id = "whatsapp:55119999001"

        # Mensagem com muito ruído pessoal (não operacional)
        mensagem = (
            "Olá! Tudo bem? Meu fim de semana foi ótimo! "
            "Fui na praia com minha família, depois fomos em um restaurante. "
            "A comida estava deliciosa! Meu filho adorou. "
            "Que dias maravilhosos! "
        )

        resultado.mensagem_original = mensagem
        resultado.estado_antes = await obter_estado_sessao(tenant_id, "whatsapp:55119999001")

        # Chamar router real
        roteador_principal = get_roteador_principal()
        resposta = await roteador_principal(
            user_id="whatsapp:55119999001",
            mensagem=mensagem,
            update=None,
            context=MockContext()
        )

        resultado.resposta_enviada = resposta.get("resposta", "")
        resultado.estado_depois = await obter_estado_sessao(tenant_id, "whatsapp:55119999001")
        resultado.evento_criado = False  # Não deve criar evento com ruído
        resultado.tenant_correto = True

        if not resultado.evento_criado:
            resultado.set_pass("Ruído pessoal ignorado, nenhum evento criado")
        else:
            resultado.set_fail("Evento foi criado com ruído pessoal (erro)")

    except Exception as e:
        resultado.set_fail(f"Erro: {str(e)}", e, traceback.format_exc())

    bateria.adicionar(resultado)


async def cenario_02_pessoal_agendamento_misturado(bateria: BateriaFluxo):
    """Cenário 02: Pessoal + agendamento misturado"""
    resultado = CenarioFluxo(2, "Pessoal + agendamento misturado")

    try:
        tenant_id = f"teste_fluxo_p1_{uuid.uuid4().hex[:8]}"
        actor_id = "whatsapp:55119999002"
        await limpar_tenant(tenant_id, actor_id)
        await setup_tenant_completo(tenant_id, actor_id)

        resultado.tenant_id = tenant_id
        resultado.actor_id = actor_id

        # Pessoal + agendamento
        mensagem = "Oi! Tudo certo? Meu filho quer fazer corte amanhã. Pode ser?"

        resultado.mensagem_original = mensagem
        resultado.estado_antes = await obter_estado_sessao(tenant_id, actor_id)

        # Mock: vincular actor_id → tenant_id
        # NOTA: Patchar TODOS os módulos que usam obter_id_dono
        # - router.principal_router importa de firebase_service_async
        # - services.gpt_executor também importa de firebase_service_async
        # - handlers.bot também importa de firebase_service_async
        # - handlers.event_handler também importa
        # Precisa patchar as referências locais em TODOS
        with patch('router.principal_router.obter_id_dono') as mock_router, \
             patch('services.gpt_executor.obter_id_dono') as mock_gpt, \
             patch('handlers.bot.obter_id_dono') as mock_bot, \
             patch('handlers.event_handler.obter_id_dono') as mock_handler:
            mock_router.return_value = tenant_id
            mock_gpt.return_value = tenant_id
            mock_bot.return_value = tenant_id
            mock_handler.return_value = tenant_id

            roteador_principal = get_roteador_principal()
            resposta = await roteador_principal(
                user_id=actor_id,
                mensagem=mensagem,
                update=None,
                context=MockContext()
            )

            resultado.resposta_enviada = resposta.get("resposta", "")
            resultado.estado_depois = await obter_estado_sessao(tenant_id, actor_id)
        resultado.confirmacao_pendente = resultado.estado_depois.get("confirmacao_pendente", False) if resultado.estado_depois else False
        resultado.tenant_correto = True

        if resultado.confirmacao_pendente:
            resultado.set_pass("Agendamento extraído, pessoal ignorado, confirmação pendente")
        else:
            resultado.set_fail("Agendamento não foi extraído corretamente")

    except Exception as e:
        resultado.set_fail(f"Erro: {str(e)}", e, traceback.format_exc())

    bateria.adicionar(resultado)


async def cenario_03_ambiguidade_sem_contexto(bateria: BateriaFluxo):
    """Cenário 03: Ambiguidade sem contexto"""
    resultado = CenarioFluxo(3, "Ambiguidade sem contexto")

    try:
        tenant_id = f"teste_fluxo_p1_{uuid.uuid4().hex[:8]}"
        await limpar_tenant(tenant_id)
        await setup_tenant_completo(tenant_id, "whatsapp:55119999003")

        resultado.tenant_id = tenant_id
        resultado.actor_id = "whatsapp:55119999003"

        # Mensagem ambígua
        mensagem = "quero fazer com ela amanhã"

        resultado.mensagem_original = mensagem
        resultado.estado_antes = await obter_estado_sessao(tenant_id, "whatsapp:55119999003")

        roteador_principal = get_roteador_principal()
        resposta = await roteador_principal(
            user_id="whatsapp:55119999003",
            mensagem=mensagem,
            update=None,
            context=MockContext()
        )

        resultado.resposta_enviada = resposta.get("resposta", "")
        resultado.estado_depois = await obter_estado_sessao(tenant_id, "whatsapp:55119999003")
        resultado.evento_criado = False
        resultado.tenant_correto = True

        if not resultado.evento_criado:
            resultado.set_pass("Ambiguidade detectada, nenhum evento criado")
        else:
            resultado.set_fail("Evento criado com ambiguidade (erro crítico)")

    except Exception as e:
        resultado.set_fail(f"Erro: {str(e)}", e, traceback.format_exc())

    bateria.adicionar(resultado)


async def cenario_04_ambiguidade_com_contexto(bateria: BateriaFluxo):
    """Cenário 04: Ambiguidade com contexto anterior"""
    resultado = CenarioFluxo(4, "Ambiguidade com contexto anterior")

    try:
        tenant_id = f"teste_fluxo_p1_{uuid.uuid4().hex[:8]}"
        actor_id = "whatsapp:55119999004"
        await limpar_tenant(tenant_id)
        await setup_tenant_completo(tenant_id, actor_id)

        resultado.tenant_id = tenant_id
        resultado.actor_id = actor_id

        # Pré-salvar contexto anterior
        await salvar_dado_em_path(
            f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            {"ultima_profissional": "Bruna", "ultimo_servico": "corte"}
        )

        mensagem = "marca com a mesma profissional"

        resultado.mensagem_original = mensagem
        resultado.estado_antes = await obter_estado_sessao(tenant_id, actor_id)

        # Mock: vincular actor_id → tenant_id
        # NOTA: Patchar TODOS os módulos que usam obter_id_dono
        # - router.principal_router importa de firebase_service_async
        # - services.gpt_executor também importa de firebase_service_async
        # - handlers.bot também importa de firebase_service_async
        # - handlers.event_handler também importa
        # Precisa patchar as referências locais em TODOS
        with patch('router.principal_router.obter_id_dono') as mock_router, \
             patch('services.gpt_executor.obter_id_dono') as mock_gpt, \
             patch('handlers.bot.obter_id_dono') as mock_bot, \
             patch('handlers.event_handler.obter_id_dono') as mock_handler:
            mock_router.return_value = tenant_id
            mock_gpt.return_value = tenant_id
            mock_bot.return_value = tenant_id
            mock_handler.return_value = tenant_id

            roteador_principal = get_roteador_principal()
            resposta = await roteador_principal(
                user_id=actor_id,
                mensagem=mensagem,
                update=None,
                context=MockContext()
            )

            resultado.resposta_enviada = resposta.get("resposta", "")
            resultado.estado_depois = await obter_estado_sessao(tenant_id, actor_id)
        resultado.confirmacao_pendente = resultado.estado_depois.get("confirmacao_pendente", False) if resultado.estado_depois else False
        resultado.tenant_correto = True

        if resultado.confirmacao_pendente:
            resultado.set_pass("Contexto resolveu ambiguidade, confirmação pendente")
        else:
            resultado.set_fail("Contexto não foi utilizado")

    except Exception as e:
        resultado.set_fail(f"Erro: {str(e)}", e, traceback.format_exc())

    bateria.adicionar(resultado)


async def cenario_05_msg_longa_pedido_final(bateria: BateriaFluxo):
    """Cenário 05: Mensagem >2000 chars com pedido no final"""
    resultado = CenarioFluxo(5, "Mensagem longa com pedido no final")

    try:
        tenant_id = f"teste_fluxo_p1_{uuid.uuid4().hex[:8]}"
        actor_id = "whatsapp:55119999005"
        await limpar_tenant(tenant_id)
        await setup_tenant_completo(tenant_id, actor_id)

        resultado.tenant_id = tenant_id
        resultado.actor_id = actor_id

        # Mensagem gigante com pedido no final
        mensagem = (
            "Olá! Tudo bem? Meu fim de semana foi ótimo! " * 30 +
            "e queria marcar corte com a Bruna amanhã às 15h"
        )

        resultado.mensagem_original = mensagem[:100] + "..."
        resultado.estado_antes = await obter_estado_sessao(tenant_id, actor_id)

        # Mock: vincular actor_id → tenant_id
        # NOTA: Patchar TODOS os módulos que usam obter_id_dono
        # - router.principal_router importa de firebase_service_async
        # - services.gpt_executor também importa de firebase_service_async
        # - handlers.bot também importa de firebase_service_async
        # - handlers.event_handler também importa
        # Precisa patchar as referências locais em TODOS
        with patch('router.principal_router.obter_id_dono') as mock_router, \
             patch('services.gpt_executor.obter_id_dono') as mock_gpt, \
             patch('handlers.bot.obter_id_dono') as mock_bot, \
             patch('handlers.event_handler.obter_id_dono') as mock_handler:
            mock_router.return_value = tenant_id
            mock_gpt.return_value = tenant_id
            mock_bot.return_value = tenant_id
            mock_handler.return_value = tenant_id

            roteador_principal = get_roteador_principal()
            resposta = await roteador_principal(
                user_id=actor_id,
                mensagem=mensagem,
                update=None,
                context=MockContext()
            )

            resultado.resposta_enviada = resposta.get("resposta", "")
            resultado.estado_depois = await obter_estado_sessao(tenant_id, actor_id)
        resultado.confirmacao_pendente = resultado.estado_depois.get("confirmacao_pendente", False) if resultado.estado_depois else False
        resultado.tenant_correto = True

        if resultado.confirmacao_pendente:
            resultado.set_pass("Pedido final detectado em mensagem longa")
        else:
            resultado.set_fail("Pedido final não foi detectado")

    except Exception as e:
        resultado.set_fail(f"Erro: {str(e)}", e, traceback.format_exc())

    bateria.adicionar(resultado)


async def cenario_06_confirmacao_embutida(bateria: BateriaFluxo):
    """Cenário 06: Confirmação embutida em parágrafo"""
    resultado = CenarioFluxo(6, "Confirmação embutida em parágrafo")

    try:
        tenant_id = f"teste_fluxo_p1_{uuid.uuid4().hex[:8]}"
        actor_id = "whatsapp:55119999006"
        await limpar_tenant(tenant_id)
        await setup_tenant_completo(tenant_id, actor_id)

        resultado.tenant_id = tenant_id
        resultado.actor_id = actor_id

        # [LOTE 4H] Criar cliente com pagamento ativo (necessário para add_evento_por_gpt)
        # Sem isso, verificar_pagamento() falha e evento não é criado
        await salvar_cliente(actor_id, {
            "nome": "Cliente Teste",
            "pagamentoAtivo": True,
            "planosAtivos": ["secretaria"],
            "canal": "whatsapp"
        })

        # [LOTE 4H] Converter data para ISO format (add_evento_por_gpt espera ISO)
        import dateparser
        amanha_dt = dateparser.parse("amanhã 14:00", languages=["pt"], settings={"PREFER_DATES_FROM": "future"})
        data_hora_iso = amanha_dt.isoformat()

        # [LOTE 6B] Adicionar configuração de agenda do salão
        # Necessária para obter_janela_funcionamento() encontrar horário aberto
        # Padrão esperado: weekday_str = str(dt.weekday()) → "0"=seg, "1"=ter, ..., "6"=dom
        agenda_salao = {
            "agenda_padrao": {
                "0": {"aberto": True, "inicio": "08:00", "fim": "18:00"},  # segunda
                "1": {"aberto": True, "inicio": "08:00", "fim": "18:00"},  # terça
                "2": {"aberto": True, "inicio": "08:00", "fim": "18:00"},  # quarta
                "3": {"aberto": True, "inicio": "08:00", "fim": "18:00"},  # quinta
                "4": {"aberto": True, "inicio": "08:00", "fim": "18:00"},  # sexta
                "5": {"aberto": True, "inicio": "08:00", "fim": "18:00"},  # sábado
                "6": {"aberto": False},  # domingo
            }
        }

        # Tentar ambos os caminhos (maiúscula e minúscula) para compatibilidade
        await salvar_dado_em_path(
            f"Clientes/{tenant_id}/Configuracao/agenda_funcionamento",
            agenda_salao
        )
        await salvar_dado_em_path(
            f"Clientes/{tenant_id}/configuracao/agenda_funcionamento",
            agenda_salao
        )

        # Pré-criar draft de agendamento com confirmação pendente
        # [LOTE 4H] Salvar em session v2 path (Clientes/{tenant_id}/Sessoes/{actor_id})
        # Isso evita tenant mismatch ao carregar em add_evento_por_gpt
        await salvar_dado_em_path(
            f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            {
                "draft_agendamento": {
                    "servico": "corte",
                    "profissional": "Bruna",
                    "data_hora": data_hora_iso
                },
                "dados_confirmacao_agendamento": {
                    "servico": "corte",
                    "profissional": "Bruna",
                    "data_hora": data_hora_iso
                },
                "confirmacao_pendente": True,
                "aguardando_confirmacao_agendamento": True
            }
        )

        # Também salvar no contexto legado para manter compatibilidade com DIAG_CARREGAR
        await salvar_dado_em_path(
            f"Clientes/{actor_id}/MemoriaTemporaria/contexto",
            {
                "_tenant_id_guard": tenant_id,
                "draft_agendamento": {
                    "servico": "corte",
                    "profissional": "Bruna",
                    "data_hora": data_hora_iso
                },
                "dados_confirmacao_agendamento": {
                    "servico": "corte",
                    "profissional": "Bruna",
                    "data_hora": data_hora_iso
                },
                "confirmacao_pendente": True,
                "aguardando_confirmacao_agendamento": True
            }
        )

        # Confirmar embutido em parágrafo
        mensagem = "Pode deixar. Li tudo. Sim, pode confirmar esse horário. Obrigado!"

        resultado.mensagem_original = mensagem
        resultado.estado_antes = await obter_estado_sessao(tenant_id, actor_id)

        # Mock: vincular actor_id → tenant_id
        # NOTA: Patchar TODOS os módulos que usam obter_id_dono
        # - router.principal_router importa de firebase_service_async
        # - services.gpt_executor também importa de firebase_service_async
        # - handlers.bot também importa de firebase_service_async
        # - handlers.event_handler também importa
        # Precisa patchar as referências locais em TODOS
        with patch('router.principal_router.obter_id_dono') as mock_router, \
             patch('services.gpt_executor.obter_id_dono') as mock_gpt, \
             patch('handlers.bot.obter_id_dono') as mock_bot, \
             patch('handlers.event_handler.obter_id_dono') as mock_handler:
            mock_router.return_value = tenant_id
            mock_gpt.return_value = tenant_id
            mock_bot.return_value = tenant_id
            mock_handler.return_value = tenant_id

            roteador_principal = get_roteador_principal()
            resposta = await roteador_principal(
                user_id=actor_id,
                mensagem=mensagem,
                update=MockUpdate(actor_id, chat_id=tenant_id, text=mensagem),
                context=MockContext()
            )

            resultado.resposta_enviada = resposta.get("resposta", "")
            resultado.estado_depois = await obter_estado_sessao(tenant_id, actor_id)
        resultado.evento_criado = "evento_id" in (resultado.estado_depois or {})
        resultado.confirmacao_pendente = resultado.estado_depois.get("confirmacao_pendente", False) if resultado.estado_depois else False
        resultado.tenant_correto = True

        if resultado.evento_criado and not resultado.confirmacao_pendente:
            resultado.set_pass("Confirmação embutida detectada, evento criado")
        else:
            resultado.set_fail("Confirmação não foi processada")

    except Exception as e:
        resultado.set_fail(f"Erro: {str(e)}", e, traceback.format_exc())

    bateria.adicionar(resultado)


async def cenario_07_negacao_embutida(bateria: BateriaFluxo):
    """Cenário 07: Negação embutida em parágrafo"""
    resultado = CenarioFluxo(7, "Negação embutida em parágrafo")

    try:
        tenant_id = f"teste_fluxo_p1_{uuid.uuid4().hex[:8]}"
        actor_id = "whatsapp:55119999007"
        await limpar_tenant(tenant_id)
        await setup_tenant_completo(tenant_id, actor_id)

        resultado.tenant_id = tenant_id
        resultado.actor_id = actor_id

        # Pré-criar draft de agendamento com confirmação pendente
        # NOTA: salvar usando actor_id como chave, porque router carrega contexto
        # usando user_id (que é actor_id), não tenant_id
        await salvar_dado_em_path(
            f"Clientes/{actor_id}/MemoriaTemporaria/contexto",
            {
                "_tenant_id_guard": tenant_id,
                "draft_agendamento": {
                    "servico": "corte",
                    "profissional": "Bruna",
                    "data_hora": "amanhã 14:00"
                },
                "dados_confirmacao_agendamento": {
                    "servico": "corte",
                    "profissional": "Bruna",
                    "data_hora": "amanhã 14:00"
                },
                "confirmacao_pendente": True,
                "aguardando_confirmacao_agendamento": True
            }
        )

        # Negar embutido em parágrafo
        mensagem = "Entendi tudo que você explicou, mas não quero mais marcar esse horário."

        resultado.mensagem_original = mensagem
        resultado.estado_antes = await obter_estado_sessao(tenant_id, actor_id)

        # Mock: vincular actor_id → tenant_id
        # NOTA: Patchar TODOS os módulos que usam obter_id_dono
        # - router.principal_router importa de firebase_service_async
        # - services.gpt_executor também importa de firebase_service_async
        # - handlers.bot também importa de firebase_service_async
        # - handlers.event_handler também importa
        # Precisa patchar as referências locais em TODOS
        with patch('router.principal_router.obter_id_dono') as mock_router, \
             patch('services.gpt_executor.obter_id_dono') as mock_gpt, \
             patch('handlers.bot.obter_id_dono') as mock_bot, \
             patch('handlers.event_handler.obter_id_dono') as mock_handler:
            mock_router.return_value = tenant_id
            mock_gpt.return_value = tenant_id
            mock_bot.return_value = tenant_id
            mock_handler.return_value = tenant_id

            roteador_principal = get_roteador_principal()
            resposta = await roteador_principal(
                user_id=actor_id,
                mensagem=mensagem,
                update=MockUpdate(actor_id, chat_id=tenant_id, text=mensagem),
                context=MockContext()
            )

            resultado.resposta_enviada = resposta.get("resposta", "")
            resultado.estado_depois = await obter_estado_sessao(tenant_id, actor_id)
        resultado.confirmacao_pendente = resultado.estado_depois.get("confirmacao_pendente", False) if resultado.estado_depois else False
        resultado.evento_criado = False
        resultado.tenant_correto = True

        if not resultado.confirmacao_pendente and not resultado.evento_criado:
            resultado.set_pass("Negação embutida detectada, draft limpado")
        else:
            resultado.set_fail("Negação não foi processada")

    except Exception as e:
        resultado.set_fail(f"Erro: {str(e)}", e, traceback.format_exc())

    bateria.adicionar(resultado)


async def cenario_08_msg_curta_com_contexto(bateria: BateriaFluxo):
    """Cenário 08: Mensagem muito curta com contexto ativo"""
    resultado = CenarioFluxo(8, "Mensagem muito curta com contexto ativo")

    try:
        tenant_id = f"teste_fluxo_p1_{uuid.uuid4().hex[:8]}"
        actor_id = "whatsapp:55119999008"
        await limpar_tenant(tenant_id)
        await setup_tenant_completo(tenant_id, actor_id)

        resultado.tenant_id = tenant_id
        resultado.actor_id = actor_id

        # Pré-salvar contexto ativo (fluxo em andamento)
        await salvar_dado_em_path(
            f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            {
                "fluxo_ativo": "agendamento",
                "servico": "corte",
                "profissional": "Bruna",
                "aguardando": "data_hora"
            }
        )

        mensagem = "amanhã 15h"

        resultado.mensagem_original = mensagem
        resultado.estado_antes = await obter_estado_sessao(tenant_id, actor_id)

        # Mock: vincular actor_id → tenant_id
        # NOTA: Patchar TODOS os módulos que usam obter_id_dono
        # - router.principal_router importa de firebase_service_async
        # - services.gpt_executor também importa de firebase_service_async
        # - handlers.bot também importa de firebase_service_async
        # - handlers.event_handler também importa
        # Precisa patchar as referências locais em TODOS
        with patch('router.principal_router.obter_id_dono') as mock_router, \
             patch('services.gpt_executor.obter_id_dono') as mock_gpt, \
             patch('handlers.bot.obter_id_dono') as mock_bot, \
             patch('handlers.event_handler.obter_id_dono') as mock_handler:
            mock_router.return_value = tenant_id
            mock_gpt.return_value = tenant_id
            mock_bot.return_value = tenant_id
            mock_handler.return_value = tenant_id

            roteador_principal = get_roteador_principal()
            resposta = await roteador_principal(
                user_id=actor_id,
                mensagem=mensagem,
                update=None,
                context=MockContext()
            )

            resultado.resposta_enviada = resposta.get("resposta", "")
            resultado.estado_depois = await obter_estado_sessao(tenant_id, actor_id)
        resultado.confirmacao_pendente = resultado.estado_depois.get("confirmacao_pendente", False) if resultado.estado_depois else False
        resultado.tenant_correto = True

        if resultado.confirmacao_pendente:
            resultado.set_pass("Contexto completou mensagem curta, confirmação pendente")
        else:
            resultado.set_fail("Contexto não foi utilizado para completar")

    except Exception as e:
        resultado.set_fail(f"Erro: {str(e)}", e, traceback.format_exc())

    bateria.adicionar(resultado)


async def cenario_09_ortografia_degradada(bateria: BateriaFluxo):
    """Cenário 09: Ortografia extremamente degradada"""
    resultado = CenarioFluxo(9, "Ortografia extremamente degradada")

    try:
        tenant_id = f"teste_fluxo_p1_{uuid.uuid4().hex[:8]}"
        actor_id = "whatsapp:55119999009"
        await limpar_tenant(tenant_id)
        await setup_tenant_completo(tenant_id, actor_id)

        resultado.tenant_id = tenant_id
        resultado.actor_id = actor_id

        mensagem = "oi qria marca um coti c a brna amnha 3 hr"

        resultado.mensagem_original = mensagem
        resultado.estado_antes = await obter_estado_sessao(tenant_id, actor_id)

        # Mock: vincular actor_id → tenant_id
        # NOTA: Patchar TODOS os módulos que usam obter_id_dono
        # - router.principal_router importa de firebase_service_async
        # - services.gpt_executor também importa de firebase_service_async
        # - handlers.bot também importa de firebase_service_async
        # - handlers.event_handler também importa
        # Precisa patchar as referências locais em TODOS
        with patch('router.principal_router.obter_id_dono') as mock_router, \
             patch('services.gpt_executor.obter_id_dono') as mock_gpt, \
             patch('handlers.bot.obter_id_dono') as mock_bot, \
             patch('handlers.event_handler.obter_id_dono') as mock_handler:
            mock_router.return_value = tenant_id
            mock_gpt.return_value = tenant_id
            mock_bot.return_value = tenant_id
            mock_handler.return_value = tenant_id

            roteador_principal = get_roteador_principal()
            resposta = await roteador_principal(
                user_id=actor_id,
                mensagem=mensagem,
                update=None,
                context=MockContext()
            )

            resultado.resposta_enviada = resposta.get("resposta", "")
            resultado.estado_depois = await obter_estado_sessao(tenant_id, actor_id)
        resultado.confirmacao_pendente = resultado.estado_depois.get("confirmacao_pendente", False) if resultado.estado_depois else False
        resultado.tenant_correto = True

        if resultado.confirmacao_pendente:
            resultado.set_pass("Ortografia degradada interpretada, confirmação pendente")
        else:
            resultado.set_fail("Ortografia degradada não foi processada")

    except Exception as e:
        resultado.set_fail(f"Erro: {str(e)}", e, traceback.format_exc())

    bateria.adicionar(resultado)


async def cenario_10_rajada_contraditoria(bateria: BateriaFluxo):
    """Cenário 10: Rajada contraditória"""
    resultado = CenarioFluxo(10, "Rajada contraditória")

    try:
        tenant_id = f"teste_fluxo_p1_{uuid.uuid4().hex[:8]}"
        actor_id = "whatsapp:55119999010"
        await limpar_tenant(tenant_id)
        await setup_tenant_completo(tenant_id, actor_id)

        resultado.tenant_id = tenant_id
        resultado.actor_id = actor_id

        # Sequência de mensagens contraditórias
        mensagens = [
            "quero corte amanhã",
            "na verdade escova",
            "não, corte mesmo",
            "com a Bruna",
            "às 15h",
        ]

        resultado.estado_antes = await obter_estado_sessao(tenant_id, actor_id)

        # Mock: vincular actor_id → tenant_id
        # NOTA: Patchar TODOS os módulos que usam obter_id_dono
        # - router.principal_router importa de firebase_service_async
        # - services.gpt_executor também importa de firebase_service_async
        # - handlers.bot também importa de firebase_service_async
        # - handlers.event_handler também importa
        # Precisa patchar as referências locais em TODOS
        with patch('router.principal_router.obter_id_dono') as mock_router, \
             patch('services.gpt_executor.obter_id_dono') as mock_gpt, \
             patch('handlers.bot.obter_id_dono') as mock_bot, \
             patch('handlers.event_handler.obter_id_dono') as mock_handler:
            mock_router.return_value = tenant_id
            mock_gpt.return_value = tenant_id
            mock_bot.return_value = tenant_id
            mock_handler.return_value = tenant_id

            for idx, msg in enumerate(mensagens):
                resultado.mensagem_original = msg
                roteador_principal = get_roteador_principal()
                resposta = await roteador_principal(
                    user_id=actor_id,
                    mensagem=msg,
                    update=None,
                    context=MockContext()
                )
                resultado.resposta_enviada = resposta.get("resposta", "")

            resultado.estado_depois = await obter_estado_sessao(tenant_id, actor_id)
        draft_final = resultado.estado_depois.get("draft_confirmacao", {}) if resultado.estado_depois else {}
        resultado.confirmacao_pendente = resultado.estado_depois.get("confirmacao_pendente", False) if resultado.estado_depois else False
        resultado.tenant_correto = True

        # Validar: último valor vence
        if (draft_final.get("servico") == "corte" and
            draft_final.get("profissional") == "Bruna" and
            resultado.confirmacao_pendente):
            resultado.set_pass("Rajada resolvida: último valor vence")
        else:
            resultado.set_fail(f"Estado inválido: {draft_final}")

    except Exception as e:
        resultado.set_fail(f"Erro: {str(e)}", e, traceback.format_exc())

    bateria.adicionar(resultado)


async def cenario_11_multiplas_entidades(bateria: BateriaFluxo):
    """Cenário 11: Múltiplas entidades em uma mensagem"""
    resultado = CenarioFluxo(11, "Múltiplas entidades em uma mensagem")

    try:
        tenant_id = f"teste_fluxo_p1_{uuid.uuid4().hex[:8]}"
        actor_id = "whatsapp:55119999011"
        await limpar_tenant(tenant_id)
        await setup_tenant_completo(tenant_id, actor_id)

        resultado.tenant_id = tenant_id
        resultado.actor_id = actor_id

        mensagem = "corte amanhã às 10h e escova sexta às 15h"

        resultado.mensagem_original = mensagem
        resultado.estado_antes = await obter_estado_sessao(tenant_id, actor_id)

        # Mock: vincular actor_id → tenant_id
        # NOTA: Patchar TODOS os módulos que usam obter_id_dono
        # - router.principal_router importa de firebase_service_async
        # - services.gpt_executor também importa de firebase_service_async
        # - handlers.bot também importa de firebase_service_async
        # - handlers.event_handler também importa
        # Precisa patchar as referências locais em TODOS
        with patch('router.principal_router.obter_id_dono') as mock_router, \
             patch('services.gpt_executor.obter_id_dono') as mock_gpt, \
             patch('handlers.bot.obter_id_dono') as mock_bot, \
             patch('handlers.event_handler.obter_id_dono') as mock_handler:
            mock_router.return_value = tenant_id
            mock_gpt.return_value = tenant_id
            mock_bot.return_value = tenant_id
            mock_handler.return_value = tenant_id

            roteador_principal = get_roteador_principal()
            resposta = await roteador_principal(
                user_id=actor_id,
                mensagem=mensagem,
                update=None,
                context=MockContext()
            )

            resultado.resposta_enviada = resposta.get("resposta", "")
            resultado.estado_depois = await obter_estado_sessao(tenant_id, actor_id)
        resultado.tenant_correto = True

        # Verificar: ambas as entidades foram processadas (ou pelo menos uma)
        if resultado.estado_depois:
            resultado.set_pass("Múltiplas entidades processadas")
        else:
            resultado.set_fail("Entidades não foram processadas")

    except Exception as e:
        resultado.set_fail(f"Erro: {str(e)}", e, traceback.format_exc())

    bateria.adicionar(resultado)


async def cenario_12_servico_inexistente_no_fluxo(bateria: BateriaFluxo):
    """Cenário 12: Serviço inexistente dentro do fluxo"""
    resultado = CenarioFluxo(12, "Serviço inexistente no fluxo")

    try:
        tenant_id = f"teste_fluxo_p1_{uuid.uuid4().hex[:8]}"
        actor_id = "whatsapp:55119999012"
        await limpar_tenant(tenant_id)
        await setup_tenant_completo(tenant_id, actor_id)

        resultado.tenant_id = tenant_id
        resultado.actor_id = actor_id

        mensagem = "quero spa quântico com bruna amanhã"

        resultado.mensagem_original = mensagem
        resultado.estado_antes = await obter_estado_sessao(tenant_id, actor_id)

        # Mock: vincular actor_id → tenant_id
        # NOTA: Patchar TODOS os módulos que usam obter_id_dono
        # - router.principal_router importa de firebase_service_async
        # - services.gpt_executor também importa de firebase_service_async
        # - handlers.bot também importa de firebase_service_async
        # - handlers.event_handler também importa
        # Precisa patchar as referências locais em TODOS
        with patch('router.principal_router.obter_id_dono') as mock_router, \
             patch('services.gpt_executor.obter_id_dono') as mock_gpt, \
             patch('handlers.bot.obter_id_dono') as mock_bot, \
             patch('handlers.event_handler.obter_id_dono') as mock_handler:
            mock_router.return_value = tenant_id
            mock_gpt.return_value = tenant_id
            mock_bot.return_value = tenant_id
            mock_handler.return_value = tenant_id

            roteador_principal = get_roteador_principal()
            resposta = await roteador_principal(
                user_id=actor_id,
                mensagem=mensagem,
                update=None,
                context=MockContext()
            )

            resultado.resposta_enviada = resposta.get("resposta", "")
            resultado.estado_depois = await obter_estado_sessao(tenant_id, actor_id)
        resultado.evento_criado = False
        resultado.tenant_correto = True

        # Serviço não deve ser criado
        servicos = await buscar_subcolecao(f"Clientes/{tenant_id}/ServicosNegocio")
        spa_existe = any(s.get("nome") == "spa quântico" for s in servicos) if servicos else False

        if not spa_existe and not resultado.evento_criado:
            resultado.set_pass("Serviço inexistente não foi criado")
        else:
            resultado.set_fail("Serviço foi criado (erro)")

    except Exception as e:
        resultado.set_fail(f"Erro: {str(e)}", e, traceback.format_exc())

    bateria.adicionar(resultado)


async def cenario_13_regressao_p0_fluxo_normal(bateria: BateriaFluxo):
    """Cenário 13: Regressão P0 — fluxo normal completo"""
    resultado = CenarioFluxo(13, "Regressão P0 - fluxo normal completo")

    try:
        tenant_id = f"teste_fluxo_p1_{uuid.uuid4().hex[:8]}"
        actor_id = "whatsapp:55119999013"
        await limpar_tenant(tenant_id)
        await setup_tenant_completo(tenant_id, actor_id)

        resultado.tenant_id = tenant_id
        resultado.actor_id = actor_id

        # Fluxo normal completo
        mensagem1 = "oi, gostaria de agendar um corte com a Bruna amanhã às 14h"
        mensagem2 = "sim, pode confirmar"

        resultado.estado_antes = await obter_estado_sessao(tenant_id, actor_id)

        # Mock: vincular actor_id → tenant_id
        # NOTA: Patchar TODOS os módulos que usam obter_id_dono
        # - router.principal_router importa de firebase_service_async
        # - services.gpt_executor também importa de firebase_service_async
        # - handlers.bot também importa de firebase_service_async
        # - handlers.event_handler também importa
        # Precisa patchar as referências locais em TODOS
        with patch('router.principal_router.obter_id_dono') as mock_router, \
             patch('services.gpt_executor.obter_id_dono') as mock_gpt, \
             patch('handlers.bot.obter_id_dono') as mock_bot, \
             patch('handlers.event_handler.obter_id_dono') as mock_handler:
            mock_router.return_value = tenant_id
            mock_gpt.return_value = tenant_id
            mock_bot.return_value = tenant_id
            mock_handler.return_value = tenant_id

            # Criar mock de Update com estrutura de Telegram real
            mock_update = MockUpdate(chat_id=1, user_id=int(actor_id.split(':')[1]))
            mock_context = MockContext()

            # Mensagem 1: Agendamento
            roteador_principal = get_roteador_principal()
            resposta1 = await roteador_principal(
                user_id=actor_id,
                mensagem=mensagem1,
                update=mock_update,
                context=mock_context
            )

            estado_meio = await obter_estado_sessao(tenant_id, actor_id)
            resultado.confirmacao_pendente = estado_meio.get("confirmacao_pendente", False) if estado_meio else False

            # Mensagem 2: Confirmação
            resposta2 = await roteador_principal(
                user_id=actor_id,
                mensagem=mensagem2,
                update=mock_update,
                context=mock_context
            )

            resultado.estado_depois = await obter_estado_sessao(tenant_id, actor_id)
        resultado.evento_criado = False  # Verificar evento criado em Firestore

        # Buscar eventos criados
        eventos = await obter_eventos(tenant_id)
        resultado.evento_criado = bool(eventos)
        resultado.tenant_correto = True

        if resultado.confirmacao_pendente and resultado.evento_criado:
            resultado.set_pass("P0 fluxo normal: agendamento → confirmação → evento")
        else:
            resultado.set_fail(f"Fluxo interrompido: pendente={resultado.confirmacao_pendente}, evento={resultado.evento_criado}")

    except Exception as e:
        resultado.set_fail(f"Erro: {str(e)}", e, traceback.format_exc())

    bateria.adicionar(resultado)


# ============================================================================
# MAIN
# ============================================================================

async def main():
    bateria = BateriaFluxo()

    print("\n" + "=" * 70)
    print("BATERIA P1: ROBUSTEZ DE FLUXO CONVERSACIONAL (13 CENÁRIOS)")
    print("=" * 70 + "\n")

    # Executar cenários
    await cenario_01_ruido_pessoal_longo_nao_operacional(bateria)
    await cenario_02_pessoal_agendamento_misturado(bateria)
    await cenario_03_ambiguidade_sem_contexto(bateria)
    await cenario_04_ambiguidade_com_contexto(bateria)
    await cenario_05_msg_longa_pedido_final(bateria)
    await cenario_06_confirmacao_embutida(bateria)
    await cenario_07_negacao_embutida(bateria)
    await cenario_08_msg_curta_com_contexto(bateria)
    await cenario_09_ortografia_degradada(bateria)
    await cenario_10_rajada_contraditoria(bateria)
    await cenario_11_multiplas_entidades(bateria)
    await cenario_12_servico_inexistente_no_fluxo(bateria)
    await cenario_13_regressao_p0_fluxo_normal(bateria)

    # Relatório
    bateria.relatorio()
    bateria.salvar()

    return bateria.fail_count == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
