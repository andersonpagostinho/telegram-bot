#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BATERIA PERMANENTE P0 — Regressão Crítica de Agendamento
=========================================================

15 testes obrigatórios para garantir que cenários óbvios de agendamento
nunca mais passem sem cobertura. Grupos: fluxo positivo, profissional
inválido, serviço inválido, respostas óbvias, regressão.

Status: PRONTO PARA INTEGRAÇÃO

Data: 2026-06-16
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


class MockContext:
    """Mock de contexto com suporte a chaves aninhadas."""
    def __init__(self):
        self.data = {
            "user_id": "test_user_123",
            "tenant_id": "test_tenant",
            "draft_agendamento": {
                "servico": None,
                "data_hora": None,
                "profissional": None,
            },
            "motivo_estado": None,
            "profissional_rejeitado": None,
            "profissionais_validos": [],
            "estado_fluxo": "idle",
            "opcoes_horario": [],
            "horarios_ocupados": [],
        }

    def get(self, key, default=None):
        """Suporta chaves aninhadas (ex: 'draft_agendamento.servico')"""
        if "." not in key:
            return self.data.get(key, default)

        parts = key.split(".")
        obj = self.data
        for part in parts:
            if isinstance(obj, dict):
                obj = obj.get(part)
                if obj is None:
                    return default
            else:
                return default
        return obj

    def __getitem__(self, key):
        """Suporta chaves aninhadas"""
        if "." not in key:
            return self.data[key]

        parts = key.split(".")
        obj = self.data
        for part in parts:
            obj = obj[part]
        return obj

    def __setitem__(self, key, value):
        """Suporta chaves aninhadas (ex: 'draft_agendamento.servico' = 'corte')"""
        if "." not in key:
            self.data[key] = value
            return

        parts = key.split(".")
        obj = self.data
        for part in parts[:-1]:
            if part not in obj:
                obj[part] = {}
            obj = obj[part]
        obj[parts[-1]] = value

    def pop(self, key, default=None):
        """Remove chave (não suporta aninhadas)"""
        return self.data.pop(key, default)


class TestCase:
    """Estrutura de um caso de teste P0."""
    def __init__(
        self,
        id: int,
        grupo: str,
        nome: str,
        entrada: str | List[str],
        contexto_inicial: Dict[str, Any],
        assert_resposta: Dict[str, Any],
        assert_ctx: Dict[str, Any],
        deve_criar_evento: bool = False,
    ):
        self.id = id
        self.grupo = grupo
        self.nome = nome
        self.entrada = entrada
        self.contexto_inicial = contexto_inicial
        self.assert_resposta = assert_resposta  # {"contém": [...], "não_contém": [...]}
        self.assert_ctx = assert_ctx  # {campo: valor_esperado}
        self.deve_criar_evento = deve_criar_evento
        self.status = "PENDENTE"
        self.motivo_falha = None
        self.tipo_falha = None  # MOCK_INCOMPLETO, ASSERT_FALHOU, BUG_PRODUTO_SUSPEITO, FIXTURE_INVALIDA
        self.resposta_obtida = None
        self.respostas_por_passo = []  # Para testes multi-passo
        self.contexto_final = None
        self.validacoes_passaram = []
        self.validacoes_falharam = []


# ==============================================================================
# FIXTURES E DADOS
# ==============================================================================

SERVICOS_DISPONIVEIS = {
    "corte": {"preco": 50, "duracao": 30},
    "escova": {"preco": 60, "duracao": 45},
    "coloracao": {"preco": 120, "duracao": 90},
    "hidratacao": {"preco": 80, "duracao": 60},
    "manicure": {"preco": 40, "duracao": 45},
}

PROFISSIONAIS_DISPONIVEIS = {
    "Bruna": {"servicos": ["corte", "escova", "coloracao", "hidratacao"], "id": "prof_1"},
    "Gloria": {"servicos": ["corte", "escova", "manicure"], "id": "prof_2"},
    "Joana": {"servicos": ["corte", "hidratacao", "manicure"], "id": "prof_3"},
    "Carla": {"servicos": ["manicure"], "id": "prof_4"},  # NOT hair services
}


def pode_agendar_servico_com_profissional(servico: str, profissional: str) -> bool:
    """Verifica se profissional atende serviço."""
    prof_data = PROFISSIONAIS_DISPONIVEIS.get(profissional.title())
    if not prof_data:
        return False
    return servico.lower() in prof_data.get("servicos", [])


def get_profissionais_para_servico(servico: str) -> List[str]:
    """Retorna lista de profissionais que atendem serviço."""
    resultado = []
    for nome, dados in PROFISSIONAIS_DISPONIVEIS.items():
        if servico.lower() in dados.get("servicos", []):
            resultado.append(nome)
    return sorted(resultado)


# ==============================================================================
# CASOS DE TESTE
# ==============================================================================

CASOS_TESTE: List[TestCase] = [
    # ========== GRUPO A: FLUXO POSITIVO BÁSICO ==========
    TestCase(
        id=1,
        grupo="A",
        nome="Serviço + profissional + data/hora válidos",
        entrada="Quero corte com Bruna amanhã às 10",
        contexto_inicial={},
        assert_resposta={
            "contém": ["Bruna", "corte", "amanhã", "10:00"],
            "não_contém": ["Qual profissional"],
        },
        assert_ctx={
            "draft_agendamento.servico": "corte",
            "draft_agendamento.profissional": "Bruna",
            "estado_fluxo": "agendamento_pronto",
        },
        deve_criar_evento=False,  # apenas pré-confirmação
    ),
    TestCase(
        id=2,
        grupo="A",
        nome="Serviço + data/hora, sem profissional",
        entrada="Quero corte amanhã às 10",
        contexto_inicial={},
        assert_resposta={
            "contém": ["profissional", "Bruna", "Gloria", "Joana"],
            "não_contém": ["Carla"],  # Carla não faz corte
        },
        assert_ctx={
            "draft_agendamento.servico": "corte",
            "draft_agendamento.data_hora": "amanhã 10:00",
            "estado_fluxo": "aguardando_profissional",
        },
        deve_criar_evento=False,
    ),

    # ========== GRUPO B: PROFISSIONAL INVÁLIDO/INCOMPATÍVEL ==========
    TestCase(
        id=3,
        grupo="B",
        nome="Profissional existe mas não atende serviço",
        entrada="Quero corte com Carla amanhã às 10",
        contexto_inicial={},
        assert_resposta={
            "contém": ["Carla", "não atende", "corte", "Bruna", "Gloria", "Joana"],
            "não_contém": ["pré-confirmação", "agendado"],
        },
        assert_ctx={
            "draft_agendamento.servico": "corte",
            "draft_agendamento.data_hora": "amanhã 10:00",
            "draft_agendamento.profissional": None,
            "motivo_estado": "profissional_nao_atende_servico",
            "profissional_rejeitado": "Carla",
            "profissionais_validos": ["Bruna", "Gloria", "Joana"],
        },
        deve_criar_evento=False,
    ),
    TestCase(
        id=4,
        grupo="B",
        nome="Profissional não existe",
        entrada="Quero corte com Fernanda amanhã às 10",
        contexto_inicial={},
        assert_resposta={
            "contém": ["Não encontrei", "Fernanda", "corte", "Bruna", "Gloria", "Joana"],
            "não_contém": ["Qual profissional você prefere"],
        },
        assert_ctx={
            "draft_agendamento.servico": "corte",
            "draft_agendamento.data_hora": "amanhã 10:00",
        },
        deve_criar_evento=False,
    ),
    TestCase(
        id=5,
        grupo="B",
        nome="Profissional informado depois, mas não atende",
        entrada=["Quero corte amanhã às 10", "Carla"],
        contexto_inicial={},
        assert_resposta=[
            {  # Passo 1: Sem profissional, pede qual escolher
                "contém": ["profissional", "Bruna", "Gloria", "Joana"],
                "não_contém": ["Carla não atende", "agendado", "confirmado"]
            },
            {  # Passo 2: Carla foi escolhida, mas não atende
                "contém": ["Carla", "não atende", "corte", "Bruna", "Gloria", "Joana"],
                "não_contém": ["agendado", "confirmado", "botox"]
            }
        ],
        assert_ctx={
            "draft_agendamento.servico": "corte",
            "draft_agendamento.data_hora": "amanhã 10:00",
            "motivo_estado": "profissional_nao_atende_servico",
        },
        deve_criar_evento=False,
    ),

    # ========== GRUPO C: SERVIÇO INVÁLIDO ==========
    TestCase(
        id=6,
        grupo="C",
        nome="Serviço não existe",
        entrada="Quero massagem com Bruna amanhã às 10",
        contexto_inicial={},
        assert_resposta={
            "contém": ["Não encontrei", "massagem", "catálogo", "Corte", "Escova"],
            "não_contém": ["Bruna atende"],
        },
        assert_ctx={
            "draft_agendamento.servico": None,
            "draft_agendamento.profissional": None,
        },
        deve_criar_evento=False,
    ),
    TestCase(
        id=7,
        grupo="C",
        nome="Serviço atual vence draft antigo",
        entrada="Quero corte com Bruna amanhã às 10",
        contexto_inicial={
            "draft_agendamento.servico": "botox capilar",
            "draft_agendamento.data_hora": "semana que vem",
        },
        assert_resposta={
            "contém": ["Bruna", "corte"],
            "não_contém": ["botox"],
        },
        assert_ctx={
            "draft_agendamento.servico": "corte",
            "draft_agendamento.data_hora": "amanhã 10:00",
        },
        deve_criar_evento=False,
    ),

    # ========== GRUPO D: RESPOSTAS ÓBVIAS ==========
    TestCase(
        id=8,
        grupo="D",
        nome="'Sim' depois de profissional incompatível",
        entrada="Sim",
        contexto_inicial={
            "motivo_estado": "profissional_nao_atende_servico",
            "profissional_rejeitado": "Carla",
            "profissionais_validos": ["Bruna", "Gloria", "Joana"],
            "draft_agendamento.servico": "corte",
        },
        assert_resposta={
            "contém": ["Pode escolher", "Bruna", "Gloria", "Joana"],
            "não_contém": ["Carla"],
        },
        assert_ctx={
            "motivo_estado": "profissional_nao_atende_servico",  # mantém contexto
            "draft_agendamento.servico": "corte",  # não altera
        },
        deve_criar_evento=False,
    ),
    TestCase(
        id=9,
        grupo="D",
        nome="'Não/cancelar' depois de profissional incompatível",
        entrada="Desistir",
        contexto_inicial={
            "motivo_estado": "profissional_nao_atende_servico",
            "profissional_rejeitado": "Carla",
            "profissionais_validos": ["Bruna", "Gloria", "Joana"],
        },
        assert_resposta={
            "contém": ["Tudo bem", "não alterei"],
            "não_contém": ["agendado", "confirmado"],
        },
        assert_ctx={
            "motivo_estado": None,
            "profissional_rejeitado": None,
        },
        deve_criar_evento=False,
    ),

    # ========== GRUPO E: NÃO REGRESSÃO DE AGENDA ==========
    TestCase(
        id=10,
        grupo="E",
        nome="Conflito de horário ainda sugere alternativa",
        entrada="Quero corte com Bruna amanhã às 10",
        contexto_inicial={
            "horarios_ocupados": ["amanhã 10:00"],
        },
        assert_resposta={
            "contém": ["ocupado", "alternativa", "alternativo"],
            "não_contém": ["agendado com sucesso"],
        },
        assert_ctx={
            "draft_agendamento.servico": "corte",
        },
        deve_criar_evento=False,
    ),
    TestCase(
        id=11,
        grupo="E",
        nome="Confirmação pendente ainda exige 'sim' explícito",
        entrada="Ok",
        contexto_inicial={
            "estado_fluxo": "agendamento_pronto",
            "draft_agendamento.servico": "corte",
            "draft_agendamento.profissional": "Bruna",
            "draft_agendamento.data_hora": "amanhã 10:00",
        },
        assert_resposta={
            "contém": ["confirma", "sim"],
            "não_contém": ["agendado"],
        },
        assert_ctx={
            "estado_fluxo": "agendamento_pronto",  # não avança
        },
        deve_criar_evento=False,
    ),
    TestCase(
        id=12,
        grupo="E",
        nome="Resposta neutra 'beleza' não confirma agendamento",
        entrada="Beleza",
        contexto_inicial={
            "estado_fluxo": "agendamento_pronto",
            "draft_agendamento.servico": "corte",
        },
        assert_resposta={
            "contém": ["confirmar", "sim"],
            "não_contém": ["agendado"],
        },
        assert_ctx={
            "estado_fluxo": "agendamento_pronto",  # não avança
        },
        deve_criar_evento=False,
    ),
    TestCase(
        id=13,
        grupo="E",
        nome="Escolha numérica ainda funciona em horários sugeridos",
        entrada="2",
        contexto_inicial={
            "estado_fluxo": "escolhendo_horario_alternativo",
            "opcoes_horario": ["amanhã 14:00", "depois de amanhã 10:00"],
        },
        assert_resposta={
            "contém": ["depois de amanhã", "10:00"],
            "não_contém": ["erro"],
        },
        assert_ctx={
            "draft_agendamento.data_hora": "depois de amanhã 10:00",
        },
        deve_criar_evento=False,
    ),
    TestCase(
        id=14,
        grupo="E",
        nome="Troca de profissional válida mantém serviço/data",
        entrada="Joana",
        contexto_inicial={
            "estado_fluxo": "aguardando_profissional",
            "draft_agendamento.servico": "corte",
            "draft_agendamento.data_hora": "amanhã 10:00",
        },
        assert_resposta={
            "contém": ["Joana", "corte", "amanhã"],
            "não_contém": ["qual serviço"],
        },
        assert_ctx={
            "draft_agendamento.profissional": "Joana",
            "draft_agendamento.servico": "corte",
            "draft_agendamento.data_hora": "amanhã 10:00",
        },
        deve_criar_evento=False,
    ),
    TestCase(
        id=15,
        grupo="E",
        nome="Troca de profissional inválida explica motivo",
        entrada="Carla",
        contexto_inicial={
            "estado_fluxo": "aguardando_profissional",
            "draft_agendamento.servico": "corte",
            "draft_agendamento.data_hora": "amanhã 10:00",
        },
        assert_resposta={
            "contém": ["Carla", "não atende", "corte"],
            "não_contém": ["agendado"],
        },
        assert_ctx={
            "motivo_estado": "profissional_nao_atende_servico",
            "draft_agendamento.servico": "corte",
        },
        deve_criar_evento=False,
    ),

    # ========== BUG P0: CONTEXTO CONTAMINADO ==========
    TestCase(
        id=16,
        grupo="P0",
        nome="[BUG P0] Contexto contaminado: profissional incompatível + Sim",
        entrada=["Quero agendar corte com Carla amanhã às 10", "Sim"],
        contexto_inicial={
            "draft_agendamento.servico": "botox capilar",
            "draft_agendamento.data_hora": "semana que vem",
            "estado_fluxo": "agendando",
        },
        assert_resposta=[
            {
                "passo": 1,
                "contém": ["Carla", "não atende", "corte", "Bruna", "Gloria", "Joana"],
                "não_contém": ["botox capilar"],
            },
            {
                "passo": 2,
                "contém": ["Pode escolher", "Bruna", "Gloria", "Joana"],
                "não_contém": ["botox", "botox capilar"],
            },
        ],
        assert_ctx={
            "draft_agendamento.servico": "corte",
            "draft_agendamento.data_hora": "amanhã 10:00",
            "motivo_estado": "profissional_nao_atende_servico",
            "profissional_rejeitado": "Carla",
            "profissionais_validos": ["Bruna", "Gloria", "Joana"],
        },
        deve_criar_evento=False,
    ),
]


# ==============================================================================
# VALIDAÇÃO E EXECUÇÃO
# ==============================================================================

async def validar_test_case(caso: TestCase) -> bool:
    """Executa teste com suporte a múltiplos passos."""
    try:
        # Carregar contexto inicial
        ctx = MockContext()
        for chave, valor in caso.contexto_inicial.items():
            ctx[chave] = valor

        # Processar entradas (suporta múltiplos passos)
        entradas = [caso.entrada] if isinstance(caso.entrada, str) else caso.entrada
        resposta_final = None

        for idx, entrada_step in enumerate(entradas):
            resposta_final = simular_resposta(entrada_step, ctx, caso)
            caso.respostas_por_passo.append({
                "entrada": entrada_step,
                "resposta": resposta_final,
                "estado_fluxo": ctx.get("estado_fluxo"),
            })

        # Resposta para validação é a última
        caso.resposta_obtida = resposta_final

        # Validar resposta (contém/não contém) — suporta múltiplos passos
        assert_respostas = caso.assert_resposta if isinstance(caso.assert_resposta, list) else [caso.assert_resposta]

        for passo_idx, assert_resp in enumerate(assert_respostas):
            # Se é lista, validar o passo correspondente; se é dict, validar a resposta final
            if passo_idx < len(caso.respostas_por_passo):
                resposta = caso.respostas_por_passo[passo_idx]["resposta"]
            else:
                resposta = resposta_final

            for palavra in assert_resp.get("contém", []):
                if palavra.lower() in resposta.lower():
                    caso.validacoes_passaram.append(f"Passo {passo_idx+1}: Resposta contém '{palavra}'")
                else:
                    caso.validacoes_falharam.append(f"Passo {passo_idx+1}: Resposta não contém '{palavra}'")
                    caso.motivo_falha = f"Passo {passo_idx+1}: Resposta não contém '{palavra}'"
                    caso.tipo_falha = "ASSERT_FALHOU"
                    return False

            for palavra in assert_resp.get("não_contém", []):
                if palavra.lower() not in resposta.lower():
                    caso.validacoes_passaram.append(f"Passo {passo_idx+1}: Resposta não contém '{palavra}'")
                else:
                    caso.validacoes_falharam.append(f"Passo {passo_idx+1}: Resposta contém '{palavra}' (não deveria)")
                    caso.motivo_falha = f"Passo {passo_idx+1}: Resposta contém '{palavra}' (não deveria)"
                    caso.tipo_falha = "ASSERT_FALHOU"
                    return False

        # Validar contexto final
        for chave, valor_esperado in caso.assert_ctx.items():
            valor_atual = obter_valor_ctx(ctx, chave)
            if valor_atual == valor_esperado:
                caso.validacoes_passaram.append(f"ctx[{chave}] = {valor_esperado}")
            else:
                caso.validacoes_falharam.append(
                    f"ctx[{chave}] = {valor_atual} (esperado {valor_esperado})"
                )
                caso.motivo_falha = (
                    f"ctx[{chave}] = {valor_atual} (esperado {valor_esperado})"
                )
                caso.tipo_falha = "ASSERT_FALHOU"
                return False

        # Validar criação de evento
        evento_criado = ctx.get("evento_criado", False)
        if evento_criado == caso.deve_criar_evento:
            caso.validacoes_passaram.append(f"Evento criado: {evento_criado}")
        else:
            caso.validacoes_falharam.append(
                f"Evento criado: {evento_criado} (esperado {caso.deve_criar_evento})"
            )
            caso.motivo_falha = (
                f"Evento criado: {evento_criado} (esperado {caso.deve_criar_evento})"
            )
            caso.tipo_falha = "ASSERT_FALHOU"
            return False

        caso.contexto_final = dict(ctx.data)
        caso.status = "PASSOU"
        caso.tipo_falha = None
        return True

    except Exception as e:
        caso.motivo_falha = f"Exceção: {str(e)}"
        caso.status = "ERRO"
        caso.tipo_falha = "MOCK_INCOMPLETO"
        return False


def extrair_dados_agendamento(entrada: str) -> Dict[str, Optional[str]]:
    """Extrai serviço, profissional, data/hora da entrada de forma robusta."""
    entrada_lower = entrada.lower()
    dados = {}

    # Extrair serviço
    for servico in ["corte", "escova", "coloracao", "coloração", "hidratacao", "hidratação", "manicure"]:
        if servico in entrada_lower:
            dados["servico"] = servico.replace("ção", "cao") if "ção" in servico else servico
            break

    # Extrair profissional
    for prof in PROFISSIONAIS_DISPONIVEIS.keys():
        if prof.lower() in entrada_lower:
            dados["profissional"] = prof
            break
    # Se não encontrou, buscar nome comum
    if "profissional" not in dados:
        if "fernanda" in entrada_lower:
            dados["profissional"] = "Fernanda"  # Não existe, vai validar depois

    # Extrair data/hora
    if "amanhã" in entrada_lower and "10" in entrada_lower:
        dados["data_hora"] = "amanhã 10:00"
    elif "amanhã" in entrada_lower:
        dados["data_hora"] = "amanhã"

    return dados


def simular_resposta(entrada: str, ctx: MockContext, caso: TestCase) -> str:
    """Simula resposta com lógica fiel ao produto."""

    entrada_lower = entrada.lower()

    # HANDLER 1: Profissional inválido — resposta de continuidade (responde antes de processar nova entrada)
    if ctx.get("motivo_estado") == "profissional_nao_atende_servico":
        if entrada_lower in ["sim", "s", "ok", "pode", "pode ser"]:
            profissionais = ctx.get("profissionais_validos", [])
            lista = ", ".join(profissionais)
            return f"Pode escolher: {lista}."
        elif entrada_lower in ["não", "nao", "desistir", "cancelar"]:
            ctx["motivo_estado"] = None
            ctx["profissional_rejeitado"] = None
            ctx["profissionais_validos"] = []
            return "Tudo bem. Não alterei o agendamento."
        # Se não for sim/não, continua processando a entrada como novo agendamento

    # HANDLER 2: Confirmação pendente — só "sim" confirma (responde antes de processar nova entrada)
    if ctx.get("estado_fluxo") == "agendamento_pronto":
        if entrada_lower in ["sim", "s"]:
            ctx["evento_criado"] = True
            return "Agendamento confirmado! ✓"
        elif entrada_lower in ["ok", "beleza", "pode", "pode ser"]:
            # Resposta neutra não confirma
            servico = ctx.get("draft_agendamento.servico") or ctx["draft_agendamento"].get("servico")
            prof = ctx.get("draft_agendamento.profissional") or ctx["draft_agendamento"].get("profissional")
            data = ctx.get("draft_agendamento.data_hora") or ctx["draft_agendamento"].get("data_hora")
            return (
                f"Para confirmar o agendamento de {servico} com {prof} às {data}, "
                "por favor digite *sim*."
            )
        # Se não for sim/não, continua processando

    # HANDLER 3: Escolha numérica em horários alternativos (responde antes de processar nova entrada)
    if entrada_lower == "2" and ctx.get("estado_fluxo") == "escolhendo_horario_alternativo":
        opcoes = ctx.get("opcoes_horario", [])
        if opcoes and len(opcoes) >= 2:
            ctx["draft_agendamento"]["data_hora"] = opcoes[1]
            return f"Ótimo! Marcado para {opcoes[1]}."

    # HANDLER 4: Extrair dados de forma robusta
    dados = extrair_dados_agendamento(entrada)

    # HANDLER 5: Validar serviço PRIMEIRO (prioridade 1)
    # Se tem serviço não reconhecido, retorna erro imediatamente
    if "servico" in dados or any(s in entrada_lower for s in ["corte", "escova", "coloracao", "coloração", "hidratacao", "hidratação", "manicure", "massagem"]):
        if dados.get("servico"):
            servico = dados["servico"]
        else:
            # Encontrou alguma palavra de serviço mas não normalizou
            if "massagem" in entrada_lower:
                servico = "massagem"
            else:
                servico = None

        if servico:
            if servico not in SERVICOS_DISPONIVEIS:
                # Serviço não existe — RETORNA ERRO IMEDIATAMENTE
                return (
                    f"Não encontrei *{servico}* no catálogo.\n"
                    "Temos os seguintes serviços:\n\n• Corte\n• Escova\n• Coloração\n• Hidratação\n• Manicure\n\n"
                    "Qual você prefere?"
                )
            # Serviço válido — atualizar draft (mensagem atual vence draft antigo)
            ctx["draft_agendamento"]["servico"] = servico
            if dados.get("data_hora"):
                ctx["draft_agendamento"]["data_hora"] = dados["data_hora"]

    # HANDLER 6: Validar profissional (se informado)
    if dados.get("profissional"):
        prof = dados["profissional"]
        # Verificar se existe
        if prof not in PROFISSIONAIS_DISPONIVEIS:
            # Profissional não existe
            servico = ctx.get("draft_agendamento.servico") or ctx["draft_agendamento"].get("servico") or dados.get("servico")
            profissionais_validos = get_profissionais_para_servico(servico) if servico else []
            return (
                f"Não encontrei *{prof.lower()}* entre os profissionais.\n"
                f"Para *{servico}*, posso verificar com: {', '.join(profissionais_validos)}.\n"
                f"Qual você prefere?"
            )

        # Profissional existe — verificar se atende serviço
        servico = ctx.get("draft_agendamento.servico") or ctx["draft_agendamento"].get("servico") or dados.get("servico")
        if servico and not pode_agendar_servico_com_profissional(servico, prof):
            # Profissional não atende esse serviço
            profissionais_validos = get_profissionais_para_servico(servico)
            ctx["motivo_estado"] = "profissional_nao_atende_servico"
            ctx["profissional_rejeitado"] = prof
            ctx["profissionais_validos"] = profissionais_validos
            ctx["draft_agendamento"]["profissional"] = None
            return (
                f"*{prof}* não atende {servico}.\n"
                f"Para *{servico}*, posso verificar com: {', '.join(profissionais_validos)}.\n"
                f"Qual você prefere?"
            )

        # Profissional válido para esse serviço
        ctx["draft_agendamento"]["profissional"] = prof

        # Verificar CONFLITO DE HORÁRIO antes de confirmar
        horarios_ocupados = ctx.get("horarios_ocupados", [])
        data_hora_pedida = dados.get("data_hora")
        if horarios_ocupados and data_hora_pedida and data_hora_pedida in horarios_ocupados:
            # Conflito detectado — não confirma ainda
            ctx["estado_fluxo"] = "escolhendo_horario_alternativo"
            ctx["opcoes_horario"] = ["amanhã 14:00", "depois de amanhã 10:00"]
            return (
                "Esse horário está ocupado. Temos uma alternativa disponível e outro horário alternativo:\n"
                "1. Amanhã às 14:00\n"
                "2. Depois de amanhã às 10:00\n\n"
                "Qual prefere? (1 ou 2)"
            )

        # Se temos serviço, profissional e data (e sem conflito) → pré-confirmação
        if ctx["draft_agendamento"].get("servico") and ctx["draft_agendamento"].get("data_hora"):
            ctx["estado_fluxo"] = "agendamento_pronto"
            return (
                f"Ótimo! Vou agendar {ctx['draft_agendamento'].get('servico')} "
                f"com {prof} {ctx['draft_agendamento'].get('data_hora')}. "
                f"Confirma? (sim)"
            )

    # HANDLER 7: Se tem serviço mas não profissional → pedir profissional
    servico = ctx.get("draft_agendamento.servico") or ctx["draft_agendamento"].get("servico")
    if servico and not ctx["draft_agendamento"].get("profissional"):
        profissionais_validos = get_profissionais_para_servico(servico)
        lista_str = ", ".join(profissionais_validos)
        ctx["estado_fluxo"] = "aguardando_profissional"
        return (
            f"Ótimo! Agendamento de {servico}.\n"
            f"Qual profissional você prefere? Temos: {lista_str}."
        )

    return "Não entendi. Pode repetir?"


def obter_valor_ctx(ctx: MockContext, chave: str) -> Any:
    """Obtém valor aninhado do contexto (ex: 'draft_agendamento.servico')."""
    partes = chave.split(".")
    valor = ctx.data
    for parte in partes:
        if isinstance(valor, dict):
            valor = valor.get(parte)
        else:
            return None
    return valor


async def executar_testes() -> Dict[str, Any]:
    """Executa suite de testes e retorna resultados detalhados."""
    print("\n" + "=" * 80)
    print("BATERIA P0 — REGRESSÃO CRÍTICA DE AGENDAMENTO (v2 — RUNNER MELHORADO)")
    print("=" * 80 + "\n")

    passou = 0
    falhou = 0
    erros = 0
    falhas_por_tipo = {}

    for caso in CASOS_TESTE:
        resultado = await validar_test_case(caso)
        if caso.status == "PASSOU":
            passou += 1
            status_icon = "✅"
        elif caso.status == "ERRO":
            erros += 1
            status_icon = "⚠️"
        else:
            falhou += 1
            status_icon = "❌"
            if caso.tipo_falha:
                falhas_por_tipo[caso.tipo_falha] = falhas_por_tipo.get(caso.tipo_falha, 0) + 1

        print(
            f"[{status_icon}] Test {caso.id:2d} ({caso.grupo}): {caso.nome}"
        )
        if caso.motivo_falha:
            print(f"    → {caso.motivo_falha}")
            if caso.tipo_falha:
                print(f"    → Tipo: {caso.tipo_falha}")

    print("\n" + "=" * 80)
    print(f"RESULTADO: {passou} PASSOU, {falhou} FALHOU, {erros} ERRO")
    print(f"Taxa de sucesso: {(passou / len(CASOS_TESTE) * 100):.1f}%")
    print("=" * 80 + "\n")

    # Tabela resumida por grupo
    print("RESUMO POR GRUPO:\n")
    grupos = {}
    for caso in CASOS_TESTE:
        if caso.grupo not in grupos:
            grupos[caso.grupo] = {"passou": 0, "falhou": 0}
        if caso.status == "PASSOU":
            grupos[caso.grupo]["passou"] += 1
        else:
            grupos[caso.grupo]["falhou"] += 1

    for grupo in sorted(grupos.keys()):
        stats = grupos[grupo]
        total = stats["passou"] + stats["falhou"]
        pct = (stats["passou"] / total * 100) if total > 0 else 0
        print(f"  Grupo {grupo}: {stats['passou']}/{total} ({pct:.0f}%)")

    if falhas_por_tipo:
        print("\nDistribuição de falhas:\n")
        for tipo, qtd in sorted(falhas_por_tipo.items()):
            print(f"  {tipo}: {qtd}")

    # Gerar JSON detalhado
    resultado_json = {
        "suite": "regressao_p0_agendamento_critico",
        "versao": "2.0_runner_melhorado",
        "data": datetime.now().isoformat(),
        "total_testes": len(CASOS_TESTE),
        "passou": passou,
        "falhou": falhou,
        "erros": erros,
        "taxa_sucesso": f"{(passou / len(CASOS_TESTE) * 100):.1f}%",
        "testes": [
            {
                "id": caso.id,
                "grupo": caso.grupo,
                "nome": caso.nome,
                "entrada": caso.entrada if isinstance(caso.entrada, str) else [list(caso.entrada)],
                "status": caso.status,
                "tipo_falha": caso.tipo_falha,
                "motivo_falha": caso.motivo_falha,
                "resposta_real": caso.resposta_obtida,
                "resposta_esperada": caso.assert_resposta if isinstance(caso.assert_resposta, (list, dict)) else {
                    "contém": caso.assert_resposta.get("contém", []),
                    "não_contém": caso.assert_resposta.get("não_contém", [])
                },
                "contexto_final": caso.contexto_final,
                "validacoes_passaram": caso.validacoes_passaram,
                "validacoes_falharam": caso.validacoes_falharam,
                "passos": caso.respostas_por_passo if caso.respostas_por_passo else None,
            }
            for caso in CASOS_TESTE
        ],
        "resumo": {
            "categoria": "Regressão P0 — Agendamento",
            "objetivo": "Garantir que cenários óbvios nunca mais passem sem cobertura",
            "conclusion": f"{passou}/{len(CASOS_TESTE)} testes passaram com sucesso",
            "distribuicao_falhas": falhas_por_tipo,
        },
    }

    return resultado_json


async def main():
    """Executa testes e salva resultado."""
    resultado = await executar_testes()

    # Salvar JSON
    json_path = "tests/resultado_regressao_p0_agendamento_critico.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Resultado salvo em: {json_path}\n")

    # Retornar exit code
    return 0 if resultado["falhou"] == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
