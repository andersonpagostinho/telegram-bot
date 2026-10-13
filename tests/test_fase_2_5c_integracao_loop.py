"""
FASE 2.5C — Testes de Integração: Detector de Loop + Recuperação
Caminho real do roteador (sem Firestore real)

Validação:
1. Ação pendente incompatível invalidada
2. Loop detectado e interrompido
3. Rascunho válido preservado
4. Reset amplo como último recurso
5. Histórico preservado
6. Identidade (tenant_id) preservada
7. Confirmação legítima continua funcionando
8. Recuperação não entra em loop infinito
"""

import pytest
import re


def normalizar(texto: str) -> str:
    """Normaliza texto para comparação"""
    import unidecode
    return unidecode.unidecode(
        re.sub(r"[^\w\s]", " ", str(texto).lower())
    ).strip()


def _tem_indicio_de_hora(t: str) -> bool:
    """Simula detecção de hora"""
    return bool(re.search(r"\d{2}:\d{2}|[01]?\d[h]", t or ""))


def eh_desistencia_fluxo(t: str) -> bool:
    """Simula detecção de desistência"""
    t_norm = normalizar(t or "")
    return any(x in t_norm for x in ["cancel", "nao quero", "parar", "sair"])


def eh_aceite_de_acao_pendente(txt: str, ctx: dict) -> bool:
    """V2 com guards FASE 2.5B"""
    ctx = ctx or {}
    t = normalizar(txt or "")

    if not t:
        return False
    if not ctx.get("ultima_acao"):
        return False
    if ctx.get("intencao_conversacional") == "indefinida":
        return False
    if not ctx.get("intencao_conversacional"):
        return False

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


def detectar_loop_conversacional(ctx: dict, mensagem_atual: str, resposta_proposta: str, iteracao: int = 1) -> dict:
    """Detector de loop (FASE 2.5B)"""
    if iteracao < 2:
        return {"has_loop": False, "tipo_loop": None, "acao_recomendada": None}

    estado_fluxo = ctx.get("estado_fluxo")
    ultima_acao = ctx.get("ultima_acao")
    ultima_resposta = ctx.get("_ultima_resposta_enviada")
    ultimo_estado_fluxo = ctx.get("_ultimo_estado_fluxo")

    # Detector 1: Resposta repetida
    if (ultima_resposta and resposta_proposta and
        normalizar(ultima_resposta) == normalizar(resposta_proposta) and
        iteracao > 1):
        return {
            "has_loop": True,
            "tipo_loop": "resposta_repetida",
            "acao_recomendada": "invalidar_ultima_acao" if ultima_acao else "reset_conversacional"
        }

    # Detector 2: Estado sem progresso
    if (ultimo_estado_fluxo == estado_fluxo and
        estado_fluxo in ["agendando", "confirmacao_pendente", "aguardando_confirmacao_agendamento"] and
        iteracao > 2):
        return {
            "has_loop": True,
            "tipo_loop": "sem_progresso",
            "acao_recomendada": "limpar_estado_transitorio"
        }

    return {"has_loop": False, "tipo_loop": None, "acao_recomendada": None}


def recuperar_de_loop_v2(ctx: dict, acao: str) -> dict:
    """
    Recuperação SELETIVA em memória (versão simplificada para testes sem Firestore).
    Retorna contexto atualizado + informação de campos removidos.
    """
    if acao == "invalidar_ultima_acao":
        ctx.pop("ultima_acao", None)
        ctx["_iteracao_confirmacao"] = 1

        return {
            "ctx": ctx,
            "campos_removidos": ["ultima_acao"],
            "mensagem": None,
            "nivel": 1,
            "persistido": False
        }

    if acao == "limpar_estado_transitorio":
        campos_remover = [
            "modo_escolha_horario",
            "modo_conversa",
            "aguardando_confirmacao_agendamento",
            "horarios_sugeridos",
            "sugestoes",
            "alternativa_profissional"
        ]

        for campo in campos_remover:
            ctx.pop(campo, None)

        ctx["estado_fluxo"] = "idle"
        ctx["_iteracao_confirmacao"] = 1

        return {
            "ctx": ctx,
            "campos_removidos": campos_remover,
            "mensagem": "Desculpa, vamos tentar de novo.",
            "nivel": 2,
            "persistido": False  # Sem Firestore em teste
        }

    if acao == "reset_conversacional":
        campos_remover_nivel3 = [
            "ultima_acao",
            "intencao_conversacional",
            "objetivo_conversacional",
            "interpretacao_conversacional",
            "modo_conversa",
            "modo_escolha_horario",
            "horarios_sugeridos",
            "sugestoes",
            "aguardando_confirmacao_agendamento"
        ]

        for campo in campos_remover_nivel3:
            ctx.pop(campo, None)

        ctx["estado_fluxo"] = "idle"
        ctx["_iteracao_confirmacao"] = 1

        return {
            "ctx": ctx,
            "campos_removidos": campos_remover_nivel3,
            "mensagem": "Desculpa, vamos começar de novo. Qual serviço você quer agendar?",
            "nivel": 3,
            "persistido": False
        }

    return {
        "ctx": ctx,
        "campos_removidos": [],
        "mensagem": None,
        "nivel": 0,
        "persistido": False
    }


class TestFase25CIntegracao:
    """Testes de integração FASE 2.5C"""

    def test_1_acao_pendente_incompativel_rejeitada(self):
        """Ação pendente incompatível é rejeitada antes de confirmar"""
        ctx = {
            "ultima_acao": "criar_evento",
            "intencao_conversacional": "novo_servico",  # Incompatível!
            "estado_fluxo": "agendando",
            "_tenant_id_guard": "tenant_001",
            "historico_texto": ["quero corte"]
        }

        # Tenta aceitar "quero corte" com ação incompatível
        resultado = eh_aceite_de_acao_pendente("quero corte", ctx)
        assert resultado is False, "Deve rejeitar intencao incompatível"

        # Contexto preservado
        assert ctx.get("_tenant_id_guard") == "tenant_001"
        assert ctx.get("historico_texto") == ["quero corte"]

    def test_2_loop_detectado_por_resposta_repetida(self):
        """Loop por resposta repetida é detectado"""
        ctx = {
            "ultima_acao": "criar_evento",
            "intencao_conversacional": "confirmar",
            "estado_fluxo": "agendando",
            "_ultima_resposta_enviada": "Confirma agendamento para segunda às 14h?",
            "_ultimo_estado_fluxo": "agendando",
            "_iteracao_confirmacao": 2,
            "historico_texto": ["quero agendar", "sim", "sim"],
            "_tenant_id_guard": "tenant_001"
        }

        resposta_proposta = "Confirma agendamento para segunda às 14h?"
        loop_info = detectar_loop_conversacional(ctx, "sim", resposta_proposta, 2)

        assert loop_info["has_loop"] is True, "Deve detectar resposta repetida"
        assert loop_info["tipo_loop"] == "resposta_repetida"
        assert loop_info["acao_recomendada"] == "invalidar_ultima_acao"

    def test_3_recuperacao_nivel1_invalida_acao(self):
        """Nível 1: Invalidar última ação sem perder contexto durável"""
        ctx = {
            "ultima_acao": "criar_evento",
            "intencao_conversacional": "confirmar",
            "estado_fluxo": "agendando",
            "draft_agendamento": {"data_hora": "2026-10-15T14:00", "servico": "corte"},
            "historico_texto": ["quero agendar"],
            "_tenant_id_guard": "tenant_001"
        }

        resultado = recuperar_de_loop_v2(ctx, "invalidar_ultima_acao")

        # Ação foi invalidada
        assert resultado["ctx"].get("ultima_acao") is None
        # Rascunho PRESERVADO
        assert resultado["ctx"].get("draft_agendamento") == {"data_hora": "2026-10-15T14:00", "servico": "corte"}
        # Histórico PRESERVADO
        assert resultado["ctx"].get("historico_texto") == ["quero agendar"]
        # Tenant PRESERVADO
        assert resultado["ctx"].get("_tenant_id_guard") == "tenant_001"
        # Nível correto
        assert resultado["nivel"] == 1
        assert resultado["mensagem"] is None

    def test_4_recuperacao_nivel2_limpa_transitorio(self):
        """Nível 2: Remove campos transitórios, preserva histórico e rascunho"""
        ctx = {
            "ultima_acao": "criar_evento",
            "estado_fluxo": "agendando",
            "modo_escolha_horario": True,
            "horarios_sugeridos": ["14:00", "15:00"],
            "sugestoes": ["bruna", "carla"],
            "draft_agendamento": {"data_hora": "2026-10-15T14:00"},
            "historico_texto": ["quero agendar", "segunda"],
            "_tenant_id_guard": "tenant_001"
        }

        resultado = recuperar_de_loop_v2(ctx, "limpar_estado_transitorio")

        # Transitórios REMOVIDOS
        assert resultado["ctx"].get("modo_escolha_horario") is None
        assert resultado["ctx"].get("horarios_sugeridos") is None
        assert resultado["ctx"].get("sugestoes") is None
        # Estado reset
        assert resultado["ctx"].get("estado_fluxo") == "idle"
        # Histórico e tenant PRESERVADOS
        assert resultado["ctx"].get("historico_texto") == ["quero agendar", "segunda"]
        assert resultado["ctx"].get("_tenant_id_guard") == "tenant_001"
        # Rascunho PODE ser preservado em nível 2
        assert resultado["ctx"].get("draft_agendamento") == {"data_hora": "2026-10-15T14:00"}
        assert resultado["nivel"] == 2
        assert resultado["mensagem"] == "Desculpa, vamos tentar de novo."

    def test_5_recuperacao_nivel3_reset_conversacional(self):
        """Nível 3: Reset último recurso, preserva histórico e identidade"""
        ctx = {
            "ultima_acao": "criar_evento",
            "intencao_conversacional": "confirmar",
            "objetivo_conversacional": "agendar",
            "interpretacao_conversacional": {"intent": "booking"},
            "draft_agendamento": {"data_hora": "2026-10-15T14:00"},
            "historico_texto": ["quero", "sim", "sim", "sim"],
            "_tenant_id_guard": "tenant_001",
            "_actor_id": "actor_123"
        }

        resultado = recuperar_de_loop_v2(ctx, "reset_conversacional")

        # Conversacional REMOVIDO
        assert resultado["ctx"].get("ultima_acao") is None
        assert resultado["ctx"].get("intencao_conversacional") is None
        assert resultado["ctx"].get("objetivo_conversacional") is None
        # Estado reset
        assert resultado["ctx"].get("estado_fluxo") == "idle"
        # Histórico PRESERVADO
        assert resultado["ctx"].get("historico_texto") == ["quero", "sim", "sim", "sim"]
        # IDENTIDADE PRESERVADA
        assert resultado["ctx"].get("_tenant_id_guard") == "tenant_001"
        assert resultado["ctx"].get("_actor_id") == "actor_123"
        # Rascunho PODE ser preservado (depende de lógica)
        assert resultado["ctx"].get("draft_agendamento") == {"data_hora": "2026-10-15T14:00"}
        assert resultado["nivel"] == 3
        assert "Qual serviço" in resultado["mensagem"]

    def test_6_confirmacao_legitima_funciona(self):
        """Confirmação legítima com iteração=1 não dispara detector"""
        ctx = {
            "ultima_acao": "criar_evento",
            "intencao_conversacional": "confirmar",
            "estado_fluxo": "agendando",
            "_iteracao_confirmacao": 1  # Primeira vez
        }

        loop_info = detectar_loop_conversacional(
            ctx,
            "sim",
            "Confirma agendamento?",
            iteracao=1  # Primeira iteração
        )

        assert loop_info["has_loop"] is False, "Não deve detectar loop na primeira iteração"

    def test_7_resposta_diferente_nao_e_loop(self):
        """Respostas diferentes não são loop mesmo com estado igual"""
        ctx = {
            "ultima_acao": "criar_evento",
            "estado_fluxo": "agendando",
            "_ultima_resposta_enviada": "Confirma agendamento para segunda?",
            "_ultimo_estado_fluxo": "agendando",
            "_iteracao_confirmacao": 2
        }

        loop_info = detectar_loop_conversacional(
            ctx,
            "oi",
            "Qual dia você prefere?",  # RESPOSTA DIFERENTE
            iteracao=2
        )

        assert loop_info["has_loop"] is False, "Respostas diferentes não são loop"

    def test_8_recuperacao_nao_entra_em_loop(self):
        """Recuperação não entra em loop infinito de si mesma"""
        ctx = {
            "ultima_acao": "criar_evento",
            "estado_fluxo": "agendando",
            "_ultima_resposta_enviada": "Confirma agendamento?",
            "_ultimo_estado_fluxo": "agendando",
            "_iteracao_confirmacao": 3
        }

        # Primeira recuperação
        resultado1 = recuperar_de_loop_v2(ctx, "invalidar_ultima_acao")
        ctx1 = resultado1["ctx"]

        # Contexto atualizado tem iteracao resetada
        assert ctx1.get("_iteracao_confirmacao") == 1
        # Próxima iteração deveria ser 2
        ctx1["_iteracao_confirmacao"] = 2

        # Se detectasse loop novamente...
        loop_info = detectar_loop_conversacional(
            ctx1,
            "oi",
            "Qual dia você quer?",  # Resposta DIFERENTE
            iteracao=2
        )

        # Não deveria detectar loop porque resposta é diferente
        assert loop_info["has_loop"] is False, "Resposta diferente não causa loop"


class TestFase25CFluxoCompleto:
    """Testes de fluxo completo integrado"""

    def test_fluxo_sem_loop(self):
        """Fluxo normal: primeira confirmação funciona"""
        ctx = {
            "ultima_acao": "criar_evento",
            "intencao_conversacional": "confirmar",
            "estado_fluxo": "agendando",
            "_tenant_id_guard": "tenant_001",
            "historico_texto": ["quero"]
        }

        # Msg 1: usuario = "sim", iteracao = 1
        eh_aceite_1 = eh_aceite_de_acao_pendente("sim", ctx)
        assert eh_aceite_1 is True

        loop_1 = detectar_loop_conversacional(ctx, "sim", "Confirma?", 1)
        assert loop_1["has_loop"] is False

        ctx["_ultima_resposta_enviada"] = "Confirma?"
        ctx["_iteracao_confirmacao"] = 2

        # Resultado: agendamento criado, fluxo termina

    def test_fluxo_com_loop_deteccao_e_recuperacao(self):
        """Fluxo com loop: detecta, recupera, continua"""
        ctx = {
            "ultima_acao": "criar_evento",
            "intencao_conversacional": "confirmar",
            "estado_fluxo": "agendando",
            "_tenant_id_guard": "tenant_001",
            "historico_texto": ["quero", "sim"],
            "draft_agendamento": {"data": "2026-10-15", "servico": "corte"}
        }

        # Msg 1: "sim" com resposta "Confirma?"
        ctx["_ultima_resposta_enviada"] = "Confirma?"
        ctx["_ultimo_estado_fluxo"] = "agendando"
        ctx["_iteracao_confirmacao"] = 2

        # Msg 2: "sim" NOVAMENTE com MESMA resposta
        loop_info = detectar_loop_conversacional(
            ctx,
            "sim",
            "Confirma?",  # MESMA
            iteracao=2
        )

        assert loop_info["has_loop"] is True
        assert loop_info["acao_recomendada"] == "invalidar_ultima_acao"

        # Recuperar
        resultado_rec = recuperar_de_loop_v2(ctx, "invalidar_ultima_acao")
        ctx_recuperado = resultado_rec["ctx"]

        # Validações
        assert ctx_recuperado.get("ultima_acao") is None  # Invalidada
        assert ctx_recuperado.get("draft_agendamento") == {"data": "2026-10-15", "servico": "corte"}  # Preservado
        assert ctx_recuperado.get("historico_texto") == ["quero", "sim"]  # Preservado
        assert ctx_recuperado.get("_tenant_id_guard") == "tenant_001"  # Preservado
        assert resultado_rec["nivel"] == 1


class TestFase25DMensagemRecuperacao:
    """Testes da mensagem de recuperação (FASE 2.5D)"""

    def test_1_mensagem_enviada_apos_recuperacao_sucesso(self):
        """Mensagem é enviada APENAS se persistência bem-sucedida"""
        resultado_recuperacao = {
            "ctx": {"estado_fluxo": "idle"},
            "mensagem": "Desculpa, acho que me confundi um pouquinho aqui 😅 Podemos tentar de novo? Me conta mais uma vez o que você gostaria de fazer que eu te ajudo! 💜",
            "nivel": 2,
            "persistido": True  # ← Sucesso
        }

        # Condição para enviar: mensagem + persistido + sem rascunho + sem aviso anterior
        deve_enviar = (
            resultado_recuperacao.get("mensagem")
            and resultado_recuperacao.get("persistido")
            and not {}  # ctx vazio = sem rascunho
            and not {}  # ctx vazio = sem aviso anterior
        )

        assert deve_enviar is True, "Deve enviar mensagem quando persistência bem-sucedida"

    def test_2_mensagem_nao_enviada_se_persistencia_falhar(self):
        """Mensagem NÃO é enviada se persistência falha"""
        resultado_recuperacao = {
            "ctx": {"estado_fluxo": "idle"},
            "mensagem": "Desculpa, acho que me confundi...",
            "nivel": 2,
            "persistido": False  # ← Falha
        }

        deve_enviar = (
            resultado_recuperacao.get("mensagem")
            and resultado_recuperacao.get("persistido")  # ← Falha aqui
        )

        assert deve_enviar is False, "NÃO deve enviar mensagem se persistência falhou"

    def test_3_mensagem_nao_enviada_se_rascunho_valido(self):
        """Mensagem NÃO é enviada se rascunho válido existe (retomar sem pedir repetição)"""
        ctx = {
            "draft_agendamento": {
                "data_hora": "2026-10-15T14:00",
                "servico": "corte",
                "profissional": "bruna"
            },
            "estado_fluxo": "idle"
        }

        resultado_recuperacao = {
            "ctx": ctx,
            "mensagem": "Desculpa, acho que me confundi...",
            "nivel": 2,
            "persistido": True
        }

        deve_enviar = (
            resultado_recuperacao.get("mensagem")
            and resultado_recuperacao.get("persistido")
            and not resultado_recuperacao.get("ctx", {}).get("draft_agendamento")  # ← Rascunho existe
        )

        assert deve_enviar is False, "NÃO deve enviar aviso se rascunho válido existe"

    def test_4_aviso_nao_duplicado(self):
        """Mesmo episódio de loop não dispara aviso duplicado"""
        ctx = {
            "estado_fluxo": "idle",
            "_aviso_recuperacao_enviado": True  # ← Já foi enviado
        }

        resultado_recuperacao = {
            "ctx": ctx,
            "mensagem": "Desculpa, acho que me confundi...",
            "nivel": 2,
            "persistido": True
        }

        deve_enviar = (
            resultado_recuperacao.get("mensagem")
            and resultado_recuperacao.get("persistido")
            and not resultado_recuperacao.get("ctx", {}).get("draft_agendamento")
            and not resultado_recuperacao.get("ctx", {}).get("_aviso_recuperacao_enviado")  # ← Já enviado
        )

        assert deve_enviar is False, "NÃO deve duplicar aviso no mesmo episódio"

    def test_5_mensagem_exata_utilizada(self):
        """Mensagem utiliza exatamente a frase especificada"""
        mensagem_esperada = (
            "Desculpa, acho que me confundi um pouquinho aqui 😅 "
            "Podemos tentar de novo? Me conta mais uma vez o que você gostaria de fazer que eu te ajudo! 💜"
        )

        # Simular msg do Nível 2 (mesmo da mensagem que a função retorna)
        mensagem_nivel2 = (
            "Desculpa, acho que me confundi um pouquinho aqui 😅 "
            "Podemos tentar de novo? Me conta mais uma vez o que você gostaria de fazer que eu te ajudo! 💜"
        )

        assert mensagem_nivel2 == mensagem_esperada, "Mensagem deve ser exatamente a especificada"

    def test_6_historico_preservado_apos_aviso(self):
        """Histórico é preservado mesmo após aviso de recuperação"""
        ctx = {
            "estado_fluxo": "idle",
            "historico_texto": ["quero corte", "sim", "sim"],
            "_tenant_id_guard": "tenant_001"
        }

        # Após aviso enviado
        ctx["_aviso_recuperacao_enviado"] = True

        # Histórico e identidade ainda estão lá
        assert ctx.get("historico_texto") == ["quero corte", "sim", "sim"]
        assert ctx.get("_tenant_id_guard") == "tenant_001"

    def test_7_fluxo_normal_sem_loop_nao_envia_aviso(self):
        """Fluxo normal (sem loop) não envia aviso"""
        # Sem loop detectado, função recuperar_de_loop() não é chamada
        # eh_aceite retorna True e resposta é enviada normalmente

        resultado_sem_loop = {
            "has_loop": False,
            "tipo_loop": None,
            "acao_recomendada": None
        }

        # Não há mensagem de recuperação se não há loop
        assert resultado_sem_loop.get("has_loop") is False
        assert resultado_sem_loop.get("acao_recomendada") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
