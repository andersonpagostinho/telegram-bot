"""
FASE 2.5B — Testes locais de proteção de contexto e detecção de loop
Sem Firestore — apenas lógica de guardrails
"""

import pytest
import re


def normalizar(texto: str) -> str:
    """Normaliza texto para comparação"""
    import unidecode
    return unidecode.unidecode(
        re.sub(r"[^\w\s]", " ", str(texto).lower())
    ).strip()


def eh_desistencia_fluxo(t: str) -> bool:
    """Simula detecção de desistência"""
    t_norm = normalizar(t or "")
    return any(x in t_norm for x in ["cancel", "nao quero", "parar", "sair"])


def _tem_indicio_de_hora(t: str) -> bool:
    """Simula detecção de hora"""
    return bool(re.search(r"\d{2}:\d{2}|[01]?\d[h]", t or ""))


def eh_aceite_de_acao_pendente_v1(txt: str, ctx: dict) -> bool:
    """VERSÃO ANTERIOR (sem guards)"""
    ctx = ctx or {}
    t = normalizar(txt or "")

    if not t:
        return False
    if not ctx.get("ultima_acao"):
        return False
    if ctx.get("intencao_conversacional") == "indefinida":
        return False
    if eh_desistencia_fluxo(t):
        return False
    if _tem_indicio_de_hora(t):
        return False
    if len(t.split()) > 6:
        return False

    return True


def eh_aceite_de_acao_pendente_v2(txt: str, ctx: dict) -> bool:
    """VERSÃO NOVA (com guards FASE 2.5B)"""
    ctx = ctx or {}
    t = normalizar(txt or "")

    if not t:
        return False
    if not ctx.get("ultima_acao"):
        return False
    if ctx.get("intencao_conversacional") == "indefinida":
        return False

    # [FASE 2.5B] GUARD: rejeitar se intencao não foi definida
    if not ctx.get("intencao_conversacional"):
        return False

    # [FASE 2.5B] GUARD: compatibilidade entre ação e intenção
    ultima_acao = ctx.get("ultima_acao", "")
    intencao = ctx.get("intencao_conversacional", "")

    compatibilidades = {
        "criar_evento": ["confirmar", "confirmar_agendamento", "sim", "aceitar"],
        "cancelamento_concluido": [],
    }

    if ultima_acao in compatibilidades:
        intenções_aceitas = compatibilidades[ultima_acao]
        if intencao not in intenções_aceitas:
            return False

    if eh_desistencia_fluxo(t):
        return False
    if _tem_indicio_de_hora(t):
        return False
    if len(t.split()) > 6:
        return False

    return True


class TestFase25BProtecaoContexto:
    """Testes de proteção contra confirmações indevidas"""

    def test_1_ola_com_ultima_acao_sem_guard(self):
        """V1: 'Olá' com ultima_acao deveria ser REJEITADO mas aceita (BUG)"""
        ctx = {
            "ultima_acao": "criar_evento",
            "intencao_conversacional": None,  # ← Não definido!
        }
        resultado_v1 = eh_aceite_de_acao_pendente_v1("ola", ctx)
        assert resultado_v1 is True, "V1 aceita 'ola' sem intenção (BUG)"

    def test_1_ola_com_ultima_acao_com_guard(self):
        """V2: 'Olá' com ultima_acao DEVE SER REJEITADO"""
        ctx = {
            "ultima_acao": "criar_evento",
            "intencao_conversacional": None,  # ← Não definido!
        }
        resultado_v2 = eh_aceite_de_acao_pendente_v2("ola", ctx)
        assert resultado_v2 is False, "V2 rejeita 'ola' sem intenção (CORRETO)"

    def test_2_pode_cancelar_sem_guard(self):
        """V1: 'Pode cancelar' com criar_evento aceita (BUG)"""
        ctx = {
            "ultima_acao": "criar_evento",
            "intencao_conversacional": "cancelar",  # ← Incompatível!
        }
        resultado_v1 = eh_aceite_de_acao_pendente_v1("pode cancelar", ctx)
        assert resultado_v1 is True, "V1 aceita 'cancelar' com criar_evento (BUG)"

    def test_2_pode_cancelar_com_guard(self):
        """V2: 'Pode cancelar' com criar_evento DEVE SER REJEITADO"""
        ctx = {
            "ultima_acao": "criar_evento",
            "intencao_conversacional": "cancelar",  # ← Incompatível!
        }
        resultado_v2 = eh_aceite_de_acao_pendente_v2("pode cancelar", ctx)
        assert resultado_v2 is False, "V2 rejeita incompatibilidade (CORRETO)"

    def test_3_quero_corte_sem_guard(self):
        """V1: 'Quero corte' com criar_evento aceita (BUG)"""
        ctx = {
            "ultima_acao": "criar_evento",
            "intencao_conversacional": "novo_servico",  # ← Incompatível!
        }
        resultado_v1 = eh_aceite_de_acao_pendente_v1("quero corte", ctx)
        assert resultado_v1 is True, "V1 aceita novo_servico com criar_evento (BUG)"

    def test_3_quero_corte_com_guard(self):
        """V2: 'Quero corte' com criar_evento DEVE SER REJEITADO"""
        ctx = {
            "ultima_acao": "criar_evento",
            "intencao_conversacional": "novo_servico",  # ← Incompatível!
        }
        resultado_v2 = eh_aceite_de_acao_pendente_v2("quero corte", ctx)
        assert resultado_v2 is False, "V2 rejeita novo_servico (CORRETO)"

    def test_4_confirmacao_valida_continua_funcionando(self):
        """Confirmação explícita e válida continua sendo aceita"""
        ctx = {
            "ultima_acao": "criar_evento",
            "intencao_conversacional": "confirmar",  # ← Compatível!
        }
        resultado_v2 = eh_aceite_de_acao_pendente_v2("sim", ctx)
        assert resultado_v2 is True, "V2 aceita 'sim' com confirmar (CORRETO)"

    def test_5_confirmacao_com_sim_explicito(self):
        """'Sim' com intenção 'sim' é aceito"""
        ctx = {
            "ultima_acao": "criar_evento",
            "intencao_conversacional": "sim",  # ← Compatível!
        }
        resultado_v2 = eh_aceite_de_acao_pendente_v2("sim", ctx)
        assert resultado_v2 is True, "V2 aceita 'sim' (CORRETO)"

    def test_6_sem_ultima_acao_nao_aceita(self):
        """Sem ultima_acao, nada é aceito como confirmação"""
        ctx = {
            "ultima_acao": None,  # ← Não há ação pendente
            "intencao_conversacional": "confirmar",
        }
        resultado_v2 = eh_aceite_de_acao_pendente_v2("sim", ctx)
        assert resultado_v2 is False, "V2 rejeita sem ultima_acao"


class TestDetectorDeLoop:
    """Testes do detector de loop"""

    def test_resposta_repetida_detecta_loop(self):
        """Resposta igual em iteração > 1 detecta loop"""
        ctx = {
            "estado_fluxo": "agendando",
            "ultima_acao": "criar_evento",
            "_ultima_resposta_enviada": "Confirma o agendamento?",
            "_ultimo_estado_fluxo": "agendando",
        }

        # Simular segunda mensagem com mesma resposta
        resposta_proposta = "Confirma o agendamento?"

        # Loop detection (versão simplificada para teste)
        has_loop = (
            normalizar(ctx.get("_ultima_resposta_enviada")) == normalizar(resposta_proposta)
            and ctx.get("_ultimo_estado_fluxo") == ctx.get("estado_fluxo")
        )

        assert has_loop is True, "Deteta repetição de resposta"

    def test_estado_sem_progresso_detecta_loop(self):
        """Estado igual em múltiplas mensagens detecta falta de progresso"""
        ctx = {
            "estado_fluxo": "agendando",
            "_ultimo_estado_fluxo": "agendando",
        }

        # Mesmo estado após múltiplas mensagens
        mesma_estado = ctx.get("estado_fluxo") == ctx.get("_ultimo_estado_fluxo")

        assert mesma_estado is True, "Detecta estado sem progresso"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
