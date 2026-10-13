"""
FASE 4.2 — Teste de Regressão P0.1: Mudança de Profissional Durante Confirmação Pendente
Ambiente: Local isolado, sem Firestore, sem envio de mensagens reais
Objetivo: Validar que a sequência "confirmacao pendente + 'outra profissional'"
apresenta menu com alternativas, não reapresenta confirmação antiga
"""

import pytest
import re


def normalizar(texto: str) -> str:
    """Normaliza texto para comparação (cópia idêntica de principal_router)"""
    import unidecode
    return unidecode.unidecode(
        re.sub(r"[^\w\s]", " ", str(texto).lower())
    ).strip()


def formatar_data_hora_br(data_hora: str) -> str:
    """Simula formatação para português"""
    # Simplificado para teste: apenas retorna a data como está
    return data_hora or "data desconhecida"


def detectar_mudanca_profissional_generica(
    texto_usuario: str,
    ctx: dict,
    draft_agendamento: dict = None
) -> dict:
    """
    Lógica P0.1 extraída de router/principal_router.py linhas 6254-6284

    Detecta "outra profissional" genérica durante confirmacao pendente
    Retorna: {
        detectado: bool,
        msg_menu: str ou None,
        alternativas_usadas: list,
        validacoes_passaram: dict
    }
    """

    # Passo 1: Normalizar e detectar "outra" + "profissional"
    texto_norm_alt = normalizar(texto_usuario or "")
    eh_pedido_generico = "outra" in texto_norm_alt and "profissional" in texto_norm_alt

    if not eh_pedido_generico:
        return {
            "detectado": False,
            "msg_menu": None,
            "alternativas_usadas": [],
            "validacoes_passaram": {"deteccao": False}
        }

    # Passo 2: Buscar dados de referência
    draft = draft_agendamento or ctx.get("draft_agendamento") or {}
    data_hora_ref = draft.get("data_hora") or ctx.get("data_hora")
    servico_ref = draft.get("servico") or ctx.get("servico")
    profissional_atual = draft.get("profissional") or ctx.get("profissional_escolhido")

    # Passo 3: Buscar alternativas
    alternativas = ctx.get("alternativa_profissional") or ctx.get("ultima_opcao_profissionais") or []

    if isinstance(alternativas, str):
        alternativas = [alternativas]

    # Passo 4: Filtrar profissionais diferentes da atual
    alternativas_validas = [
        p for p in alternativas
        if p and normalizar(p) != normalizar(profissional_atual or "")
    ]

    # Passo 5: Validar precondições
    validacoes = {
        "deteccao": True,
        "tem_alternativas": bool(alternativas_validas),
        "tem_data_hora": bool(data_hora_ref),
        "tem_servico": bool(servico_ref),
        "profissional_diferente": len(alternativas_validas) > 0
    }

    # Passo 6: Gerar menu se passou nas validações
    if alternativas_validas and data_hora_ref and servico_ref:
        opcoes_fmt = "\n".join([f"  • {nome}" for nome in alternativas_validas])
        msg_menu = (
            f"Perfeito! Para manter *{data_hora_ref}* com *{servico_ref}*, "
            f"estas profissionais estão disponíveis:\n\n{opcoes_fmt}\n\n"
            f"Qual você prefere?"
        )

        return {
            "detectado": True,
            "msg_menu": msg_menu,
            "alternativas_usadas": alternativas_validas,
            "validacoes_passaram": validacoes
        }
    else:
        # Falhou em alguma validação
        return {
            "detectado": False,
            "msg_menu": None,
            "alternativas_usadas": [],
            "validacoes_passaram": validacoes
        }


class TestP01ConfirmacaoPendenteOutraProf:
    """Testes do fluxo P0.1: confirmacao pendente + 'outra profissional'"""

    def test_1_deteccao_outra_profissional_basica(self):
        """Cenário 1: Detecção básica de 'outra profissional' durante confirmacao pendente"""
        ctx = {
            "estado_fluxo": "agendando",
            "aguardando_confirmacao_agendamento": True,
            "ultima_acao": "criar_evento",
            "draft_agendamento": {
                "data_hora": "14/10 14:30",
                "servico": "Corte Masculino",
                "profissional": "Bruna"
            },
            "alternativa_profissional": ["Joana", "Maria"]
        }

        texto_usuario = "manter o horario com outra profissional"

        resultado = detectar_mudanca_profissional_generica(texto_usuario, ctx)

        assert resultado["detectado"] is True, "Deve detectar 'outra profissional'"
        assert resultado["msg_menu"] is not None, "Deve gerar menu"
        assert "Joana" in resultado["msg_menu"], "Menu deve conter Joana"
        assert "Maria" in resultado["msg_menu"], "Menu deve conter Maria"
        assert "14/10 14:30" in resultado["msg_menu"], "Menu deve preservar data/hora"
        assert "Corte Masculino" in resultado["msg_menu"], "Menu deve preservar serviço"

    def test_2_alternativas_validas_filtra_profissional_atual(self):
        """Cenário 2: Profissional atual é filtrada das alternativas"""
        ctx = {
            "draft_agendamento": {
                "data_hora": "14/10 14:30",
                "servico": "Corte",
                "profissional": "Bruna"
            },
            "alternativa_profissional": ["Bruna", "Joana", "Maria"]  # Bruna está aqui
        }

        resultado = detectar_mudanca_profissional_generica("outra profissional", ctx)

        assert resultado["detectado"] is True
        assert "Bruna" not in resultado["alternativas_usadas"], "Bruna não deve aparecer nas alternativas"
        assert "Joana" in resultado["alternativas_usadas"]
        assert "Maria" in resultado["alternativas_usadas"]

    def test_3_menu_preserva_data_hora_exata(self):
        """Cenário 3: Data e hora são preservadas exatamente como estavam"""
        ctx = {
            "draft_agendamento": {
                "data_hora": "15/11 19:45",
                "servico": "Escova",
                "profissional": "Carla"
            },
            "alternativa_profissional": ["Bruna", "Joana"]
        }

        resultado = detectar_mudanca_profissional_generica("outra profissional", ctx)

        assert "*15/11 19:45*" in resultado["msg_menu"], "Data/hora preservada com formatação"
        assert "*Escova*" in resultado["msg_menu"], "Serviço preservado"

    def test_4_sem_alternativas_nao_apresenta_menu(self):
        """Cenário 4: Se não há alternativas, não apresenta menu"""
        ctx = {
            "draft_agendamento": {
                "data_hora": "14/10 14:30",
                "servico": "Corte",
                "profissional": "Bruna"
            },
            "alternativa_profissional": []  # Vazio
        }

        resultado = detectar_mudanca_profissional_generica("outra profissional", ctx)

        assert resultado["detectado"] is False, "Não deve detectar sem alternativas"
        assert resultado["msg_menu"] is None, "Não deve gerar menu"

    def test_5_sem_data_nao_apresenta_menu(self):
        """Cenário 5: Se não há data, não apresenta menu"""
        ctx = {
            "draft_agendamento": {
                "servico": "Corte",
                "profissional": "Bruna"
                # Falta data_hora
            },
            "alternativa_profissional": ["Joana"]
        }

        resultado = detectar_mudanca_profissional_generica("outra profissional", ctx)

        assert resultado["detectado"] is False, "Deve falhar sem data"
        assert resultado["validacoes_passaram"]["tem_data_hora"] is False

    def test_6_sem_servico_nao_apresenta_menu(self):
        """Cenário 6: Se não há serviço, não apresenta menu"""
        ctx = {
            "draft_agendamento": {
                "data_hora": "14/10 14:30",
                "profissional": "Bruna"
                # Falta servico
            },
            "alternativa_profissional": ["Joana"]
        }

        resultado = detectar_mudanca_profissional_generica("outra profissional", ctx)

        assert resultado["detectado"] is False, "Deve falhar sem serviço"
        assert resultado["validacoes_passaram"]["tem_servico"] is False

    def test_7_fallback_contexto_se_draft_vazio(self):
        """Cenário 7: Se draft vazio, buscar no contexto direto"""
        ctx = {
            "data_hora": "14/10 14:30",  # No contexto, não no draft
            "servico": "Corte",
            "profissional_escolhido": "Bruna",  # Nome diferente
            "alternativa_profissional": ["Joana"]
        }

        resultado = detectar_mudanca_profissional_generica("outra profissional", ctx)

        assert resultado["detectado"] is True, "Deve usar valores do contexto como fallback"
        assert "14/10 14:30" in resultado["msg_menu"]

    def test_8_alternativa_profissional_como_string(self):
        """Cenário 8: Se alternativa_profissional é string em vez de lista, converter"""
        ctx = {
            "draft_agendamento": {
                "data_hora": "14/10 14:30",
                "servico": "Corte",
                "profissional": "Bruna"
            },
            "alternativa_profissional": "Joana"  # String, não lista
        }

        resultado = detectar_mudanca_profissional_generica("outra profissional", ctx)

        assert resultado["detectado"] is True, "Deve converter string para lista"
        assert "Joana" in resultado["msg_menu"]

    def test_9_nao_detecta_sem_palavra_chave_outra(self):
        """Cenário 9: Mensagem sem 'outra' não ativa o fluxo"""
        ctx = {
            "draft_agendamento": {
                "data_hora": "14/10 14:30",
                "servico": "Corte",
                "profissional": "Bruna"
            },
            "alternativa_profissional": ["Joana"]
        }

        resultado = detectar_mudanca_profissional_generica("pode trocar a profissional?", ctx)

        assert resultado["detectado"] is False, "Não deve detectar sem 'outra'"

    def test_10_nao_detecta_sem_palavra_chave_profissional(self):
        """Cenário 10: Mensagem sem 'profissional' não ativa o fluxo"""
        ctx = {
            "draft_agendamento": {
                "data_hora": "14/10 14:30",
                "servico": "Corte",
                "profissional": "Bruna"
            },
            "alternativa_profissional": ["Joana"]
        }

        resultado = detectar_mudanca_profissional_generica("quero outra pessoa", ctx)

        assert resultado["detectado"] is False, "Não deve detectar sem 'profissional'"

    def test_11_normalizacao_acentos(self):
        """Cenário 11: Normalização funciona com acentos"""
        ctx = {
            "draft_agendamento": {
                "data_hora": "14/10 14:30",
                "servico": "Corte",
                "profissional": "Marília"
            },
            "alternativa_profissional": ["Bruna", "Joana"]
        }

        # Mensagem com acentos diferentes
        resultado = detectar_mudanca_profissional_generica(
            "manter o horário com outra profissional",  # acentuado
            ctx
        )

        assert resultado["detectado"] is True, "Normalização deve ignorar acentos na detecção"

    def test_12_menu_formato_correto(self):
        """Cenário 12: Menu tem formato esperado"""
        ctx = {
            "draft_agendamento": {
                "data_hora": "14/10 14:30",
                "servico": "Corte Masculino",
                "profissional": "Bruna"
            },
            "alternativa_profissional": ["Joana", "Maria"]
        }

        resultado = detectar_mudanca_profissional_generica("outra profissional", ctx)
        msg = resultado["msg_menu"]

        # Validar estrutura do menu
        assert msg.startswith("Perfeito!"), "Menu deve começar com 'Perfeito!'"
        assert "Para manter" in msg, "Menu deve mencionar 'Para manter'"
        assert "• Joana" in msg, "Menu deve listar Joana com bullet"
        assert "• Maria" in msg, "Menu deve listar Maria com bullet"
        assert "Qual você prefere?" in msg, "Menu deve perguntar qual prefere"

    def test_13_ultima_opcao_profissionais_como_fallback(self):
        """Cenário 13: Usar ultima_opcao_profissionais se alternativa_profissional vazio"""
        ctx = {
            "draft_agendamento": {
                "data_hora": "14/10 14:30",
                "servico": "Corte",
                "profissional": "Bruna"
            },
            "alternativa_profissional": None,  # Vazio
            "ultima_opcao_profissionais": ["Joana", "Maria"]  # Fallback
        }

        resultado = detectar_mudanca_profissional_generica("outra profissional", ctx)

        assert resultado["detectado"] is True, "Deve usar ultima_opcao_profissionais como fallback"
        assert "Joana" in resultado["msg_menu"]

    def test_14_confirmacao_normal_sem_outra_profissional(self):
        """Cenário 14: Confirmação normal ('sim') não ativa P0.1"""
        ctx = {
            "draft_agendamento": {
                "data_hora": "14/10 14:30",
                "servico": "Corte",
                "profissional": "Bruna"
            },
            "alternativa_profissional": ["Joana"]
        }

        resultado = detectar_mudanca_profissional_generica("sim", ctx)

        assert resultado["detectado"] is False, "Não deve ativar P0.1 para 'sim'"

    def test_15_validacoes_completas(self):
        """Cenário 15: Todas as validações devem ser documentadas"""
        ctx = {
            "draft_agendamento": {
                "data_hora": "14/10 14:30",
                "servico": "Corte",
                "profissional": "Bruna"
            },
            "alternativa_profissional": ["Joana", "Maria"]
        }

        resultado = detectar_mudanca_profissional_generica("outra profissional", ctx)

        # Todas as validações devem estar True
        assert resultado["validacoes_passaram"]["deteccao"] is True
        assert resultado["validacoes_passaram"]["tem_alternativas"] is True
        assert resultado["validacoes_passaram"]["tem_data_hora"] is True
        assert resultado["validacoes_passaram"]["tem_servico"] is True
        assert resultado["validacoes_passaram"]["profissional_diferente"] is True


class TestP01ProtecaoConfirmacao:
    """Testes de proteção: confirmação normal continua funcionando"""

    def test_1_confirmacao_sim_nao_ativa_p01(self):
        """Proteção 1: 'sim' simples não ativa P0.1"""
        ctx = {
            "draft_agendamento": {
                "data_hora": "14/10 14:30",
                "servico": "Corte",
                "profissional": "Bruna"
            },
            "alternativa_profissional": ["Joana"]
        }

        resultado = detectar_mudanca_profissional_generica("sim", ctx)
        assert resultado["detectado"] is False

    def test_2_confirmacao_aceitar_nao_ativa_p01(self):
        """Proteção 2: 'aceitar' não ativa P0.1"""
        resultado = detectar_mudanca_profissional_generica(
            "aceitar",
            {"alternativa_profissional": ["X"]}
        )
        assert resultado["detectado"] is False

    def test_3_contexto_sem_alternativas_invalido(self):
        """Proteção 3: Contexto sem alternativas não gera menu"""
        ctx = {
            "draft_agendamento": {
                "data_hora": "14/10 14:30",
                "servico": "Corte",
                "profissional": "Bruna"
            }
            # Sem alternativa_profissional
        }

        resultado = detectar_mudanca_profissional_generica("outra profissional", ctx)
        assert resultado["detectado"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
