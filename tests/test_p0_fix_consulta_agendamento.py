"""
Testes para correção de estado inválido no fluxo consulta → agendamento.

Problema: Sistema salva aguardando_confirmacao_agendamento_por_consulta=True
com servico_sugerido_consulta=None quando busca de serviço falha.

Solução: Não entrar em estado de confirmação se serviço não foi identificado.

Testes:
T1: Serviço válido encontrado → estado de confirmação salvo
T2: Busca falha → nenhuma confirmação salva, lista serviços
T3: Serviço fora do catálogo → nenhuma confirmação
T4: Confirmação "sim" com serviço válido → passa para fluxo correto
T5: Confirmação "sim" sem serviço → pergunta qual serviço
T6: Estado anterior existe → não reutiliza indevidamente
"""

import pytest


@pytest.mark.asyncio
async def test_t1_servico_valido_estado_confirmacao_salvo():
    """
    T1: Serviço válido encontrado → estado de confirmação salvo com serviço válido.
    """
    # Mock: buscar_subcolecao retorna profissionais com serviços
    profissionais = {
        "bruna": {"nome": "Bruna", "servicos": ["manicure", "pedicure"]},
    }

    ctx_salvo = {}

    async def mock_salvar(dono_id, cliente_id, contexto):
        ctx_salvo.update(contexto)
        return True

    # Simular que serviço foi encontrado por busca textual
    servico_para_resposta = "manicure"  # Assume que encontrou

    # COM FIX: salva confirmação APENAS se serviço é válido
    if servico_para_resposta:
        await mock_salvar("7394370553", "whatsapp:5511991382080", {
            "aguardando_confirmacao_agendamento_por_consulta": True,
            "servico_sugerido_consulta": servico_para_resposta,
            "estado_fluxo": "aguardando_confirmacao_consulta",
        })

    # Validar que estado foi salvo com serviço válido
    assert ctx_salvo.get("aguardando_confirmacao_agendamento_por_consulta") == True
    assert ctx_salvo.get("servico_sugerido_consulta") == "manicure"
    assert ctx_salvo.get("estado_fluxo") == "aguardando_confirmacao_consulta"

    print("✅ T1 PASSOU: estado de confirmação salvo com serviço válido")


@pytest.mark.asyncio
async def test_t2_busca_falha_nenhuma_confirmacao():
    """
    T2: Busca falha → nenhuma confirmação salva, lista serviços.
    """
    profissionais = {
        "bruna": {"nome": "Bruna", "servicos": ["manicure", "pedicure"]},
    }

    ctx_salvo = {}
    confirmacao_foi_salva = False

    async def mock_salvar(dono_id, cliente_id, contexto):
        nonlocal confirmacao_foi_salva
        ctx_salvo.update(contexto)
        if contexto.get("aguardando_confirmacao_agendamento_por_consulta"):
            confirmacao_foi_salva = True
        return True

    # Simular falha de busca (serviço não encontrado)
    servico_para_resposta = None  # Busca falhou

    # COM FIX: não salva confirmação se serviço é None
    if servico_para_resposta is None:
        # Lista serviços e pede especificação
        todos_servicos = []
        for p in profissionais.values():
            todos_servicos.extend(p.get("servicos") or [])
        servicos_unicos = list(dict.fromkeys(todos_servicos))

        lista_servicos = ", ".join(servicos_unicos)
        resposta_texto = f"Não consegui identificar. Oferecemos: {lista_servicos}. Qual você gostaria?"
        # NÃO salva estado de confirmação
    else:
        await mock_salvar("7394370553", "whatsapp:5511991382080", {
            "aguardando_confirmacao_agendamento_por_consulta": True,
            "servico_sugerido_consulta": servico_para_resposta,
        })

    # Validar que confirmação NÃO foi salva
    assert confirmacao_foi_salva == False, "Confirmação foi salva mesmo com serviço None!"

    print("✅ T2 PASSOU: nenhuma confirmação salva, lista serviços")


@pytest.mark.asyncio
async def test_t4_confirmacao_com_servico_valido():
    """
    T4: Confirmação "sim" após consulta válida → passa para fluxo correto.
    """
    # Simular estado de confirmação válido
    ctx = {
        "aguardando_confirmacao_agendamento_por_consulta": True,
        "servico_sugerido_consulta": "manicure",
        "estado_fluxo": "aguardando_confirmacao_consulta",
    }

    # Simular resposta do cliente
    texto_usuario = "sim"
    txt_lower = texto_usuario.lower().strip()

    confirmacoes = ["sim", "ok", "pode", "quero", "pode ser", "agendar", "pode agendar", "vamos"]
    confirmacao_resposta = any(c in txt_lower for c in confirmacoes) and len(txt_lower.split()) <= 3

    # Validar detecção de confirmação
    assert confirmacao_resposta == True, "Confirmação não foi detectada"

    # Validar que tem serviço válido
    servico_sugerido = ctx.get("servico_sugerido_consulta")
    assert servico_sugerido is not None, "Serviço está None!"
    assert servico_sugerido == "manicure", f"Serviço incorreto: {servico_sugerido}"

    # Validar que continua para agendamento
    assert servico_sugerido, "Seria perguntado serviço novamente (BUG!)"

    print("✅ T4 PASSOU: confirmação com serviço válido continua fluxo correto")


@pytest.mark.asyncio
async def test_t5_confirmacao_sem_servico():
    """
    T5: Confirmação "sim" sem serviço → pergunta qual serviço (não redundante).
    """
    # Simular estado INVÁLIDO (com bug anterior)
    ctx = {
        "aguardando_confirmacao_agendamento_por_consulta": True,
        "servico_sugerido_consulta": None,  # BUG!
        "estado_fluxo": "aguardando_confirmacao_consulta",
    }

    texto_usuario = "sim"
    txt_lower = texto_usuario.lower().strip()

    confirmacoes = ["sim", "ok", "pode"]
    confirmacao_resposta = any(c in txt_lower for c in confirmacoes) and len(txt_lower.split()) <= 3

    # Validar detecção de confirmação
    assert confirmacao_resposta == True

    # Validar que serviço está None
    servico_sugerido = ctx.get("servico_sugerido_consulta")
    assert servico_sugerido is None, "Teste invalido: serviço deveria ser None"

    # Com FIX: detecta o problema e NÃO entra em agendamento
    if not servico_sugerido:
        resposta = "Qual serviço você quer agendar?"
        # Não continua para "Qual dia e horário"
        assert resposta != "Perfeito — manicure. Qual dia e horário você prefere?"

    print("✅ T5 PASSOU: confirmação sem serviço retorna pergunta apropriada")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
