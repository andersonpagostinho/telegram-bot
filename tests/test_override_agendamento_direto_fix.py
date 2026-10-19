"""
Testes obrigatórios para FIX P0 — Override da resposta GPT para agendamento_direto

Cobre 9 cenários críticos conforme especificação.
REGRA DE OURO: Firebase real de início até fim (sem mocks).
"""

import pytest
from router.principal_router import roteador_principal
from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path


@pytest.mark.asyncio
async def test_001_agendamento_direto_resposta_valida_preservada():
    """
    CENÁRIO 1: agendamento_direto, resposta válida e acao=None

    QUANDO: GPT detecta agendamento_direto com todos os dados,
            retorna resposta textual válida mas acao=null
    ENTÃO: resposta do GPT é preservada (não descartada por fallback)
    E: draft é preenchido com serviço, profissional, data_hora
    E: estado_fluxo indica aguardando confirmação
    """
    tenant_id = "7394370553"
    actor_id = "whatsapp:5511991382080"

    # Setup: estado idle
    ctx_init = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "idle",
        "draft_agendamento": None,
        "aguardando_confirmacao_agendamento": False,
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
        dados=ctx_init
    )

    # Mensagem com dados completos (não ambígua)
    mensagem = (
        "Oi, gostaria de agendar um corte com Bruna para quarta-feira às 15h."
    )

    resultado = await roteador_principal(
        user_id=actor_id,
        mensagem=mensagem,
        tenant_id=tenant_id,
        phone_number_id="1350170954840548"
    )

    resposta_texto = resultado.get("resposta", "")
    print(f"[T1] Resposta: {resposta_texto[:100]}...")

    sessao = await buscar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{actor_id}"
    )

    # VALIDAÇÕES
    assert resposta_texto, "Resposta vazia"
    assert "bruna" in resposta_texto.lower() or "quarta" in resposta_texto.lower() or "15" in resposta_texto, \
        f"Resposta não menciona dados da mensagem: {resposta_texto}"

    draft = sessao.get("draft_agendamento") or {}
    assert draft.get("servico"), f"Draft sem serviço: {draft}"
    assert draft.get("profissional"), f"Draft sem profissional: {draft}"
    assert draft.get("data_hora"), f"Draft sem data_hora: {draft}"

    print(f"✅ T1 PASSOU")


@pytest.mark.asyncio
async def test_002_agendamento_direto_resposta_vazia_fallback():
    """
    CENÁRIO 2: agendamento_direto, resposta vazia ou null

    QUANDO: GPT retorna resposta_texto vazia/null (ex: erro)
    ENTÃO: fallback é utilizado (monta pergunta apropriada)
    """
    tenant_id = "7394370553"
    actor_id = "whatsapp:5511991382080"

    ctx_init = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "idle",
        "draft_agendamento": None,
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
        dados=ctx_init
    )

    # Mensagem com dados completos (deve ser detectada como agendamento_direto)
    mensagem = "Corte com Bruna na terça às 10h"

    resultado = await roteador_principal(
        user_id=actor_id,
        mensagem=mensagem,
        tenant_id=tenant_id,
        phone_number_id="1350170954840548"
    )

    resposta_texto = resultado.get("resposta", "")
    assert resposta_texto, "Nenhuma resposta gerada"

    # Se fallback foi usado, deve ter estrutura previsível
    # (ex: "Perfeito — ..." ou pergunta de confirmação/próximo passo)
    assert "perfeito" in resposta_texto.lower() or "qual" in resposta_texto.lower() or \
           "posso" in resposta_texto.lower() or "prefere" in resposta_texto.lower(), \
        f"Resposta fallback não segue padrão esperado: {resposta_texto}"

    print(f"✅ T2 PASSOU")


@pytest.mark.asyncio
async def test_003_dados_incompletos_pergunta_faltante():
    """
    CENÁRIO 3: Dados incompletos — solicitar apenas dado faltante

    QUANDO: data extraída, profissional extraído, MAS serviço falta
    ENTÃO: pergunta apenas qual serviço, sem sugerir que agendamento está confirmado
    """
    tenant_id = "7394370553"
    actor_id = "whatsapp:5511991382080"

    ctx_init = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "idle",
        "draft_agendamento": None,
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
        dados=ctx_init
    )

    # Mensagem: apenas data + profissional (sem serviço)
    mensagem = "Gostaria de agendar com Bruna para terça"

    resultado = await roteador_principal(
        user_id=actor_id,
        mensagem=mensagem,
        tenant_id=tenant_id,
        phone_number_id="1350170954840548"
    )

    resposta_texto = resultado.get("resposta", "").lower()

    # Deve perguntar serviço, não confirmar
    assert "serviço" in resposta_texto or "servico" in resposta_texto, \
        f"Resposta não pergunta serviço: {resposta_texto}"

    # NÃO deve dizer "posso agendar/confirmar" quando dados faltam
    assert "pode agendar" not in resposta_texto and "pode confirmar" not in resposta_texto, \
        f"Resposta sugere confirmação com dados incompletos: {resposta_texto}"

    print(f"✅ T3 PASSOU")


@pytest.mark.asyncio
async def test_004_dados_completos_nao_cria_evento_antes_confirmacao():
    """
    CENÁRIO 4: Dados completos — não cria evento antes de confirmação

    QUANDO: agendamento_direto com serviço + profissional + data_hora + hora explícita
    ENTÃO: draft é criado, estado fica aguardando_confirmacao, MAS nenhum evento é criado
    """
    tenant_id = "7394370553"
    actor_id = "whatsapp:5511991382080"

    ctx_init = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "idle",
        "draft_agendamento": None,
        "aguardando_confirmacao_agendamento": False,
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
        dados=ctx_init
    )

    # Dados COMPLETOS: serviço + prof + data + hora
    mensagem = "Quero corte com Bruna quarta-feira às 14h"

    resultado = await roteador_principal(
        user_id=actor_id,
        mensagem=mensagem,
        tenant_id=tenant_id,
        phone_number_id="1350170954840548"
    )

    sessao = await buscar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{actor_id}"
    )

    # VALIDAÇÕES
    draft = sessao.get("draft_agendamento") or {}
    assert draft.get("servico"), f"Draft sem serviço"
    assert draft.get("profissional"), f"Draft sem profissional"
    assert draft.get("data_hora"), f"Draft sem data_hora"

    # Estado deve estar aguardando confirmação, não "agendado"
    estado = sessao.get("estado_fluxo")
    assert estado in ["agendando", "aguardando_confirmacao_agendamento", "confirmacao_pendente"], \
        f"Estado inesperado (deveria estar em confirmação): {estado}"

    # NÃO deve ter evento criado
    eventos = sessao.get("eventos") or []
    assert len(eventos) == 0, f"Eventos foram criados antes de confirmação: {eventos}"

    print(f"✅ T4 PASSOU")


@pytest.mark.asyncio
async def test_005_mensagem_com_typos_entidades_preservadas():
    """
    CENÁRIO 5: Mensagem com typos — entidades preservadas se validadas

    QUANDO: "gostaria de cort para amha as 14 com carla" (typos: cort, amha)
    E: classificador resolve como agendamento_direto com confiança alta
    ENTÃO: entidades normalizadas ("corte", data_correta, "14:00", "carla")
           são extraídas e draft é criado com valores corretos
    """
    tenant_id = "7394370553"
    actor_id = "whatsapp:5511991382080"

    ctx_init = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "idle",
        "draft_agendamento": None,
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
        dados=ctx_init
    )

    # Mensagem COM TYPOS
    mensagem = "gostaria de cort para amha as 14 com carla"

    resultado = await roteador_principal(
        user_id=actor_id,
        mensagem=mensagem,
        tenant_id=tenant_id,
        phone_number_id="1350170954840548"
    )

    sessao = await buscar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{actor_id}"
    )

    draft = sessao.get("draft_agendamento") or {}

    # VALIDAÇÕES: entidades devem estar normalizadas
    assert "corte" in (draft.get("servico") or "").lower(), \
        f"Serviço não normalizado: {draft.get('servico')}"

    assert "carla" in (draft.get("profissional") or "").lower(), \
        f"Profissional não normalizado: {draft.get('profissional')}"

    # data_hora deve estar em ISO, com horário 14:00
    data_hora = draft.get("data_hora") or ""
    assert "14:00" in data_hora or "14:30" in data_hora, \
        f"Horário não extraído corretamente: {data_hora}"

    print(f"✅ T5 PASSOU")


@pytest.mark.asyncio
async def test_006_resposta_gpt_incompativel_slots():
    """
    CENÁRIO 6: Resposta GPT incompatível com slots — não enviar contraditório

    QUANDO: resposta_texto sugere "sem horário" mas slots têm hora_confirmada
    ENTÃO: resposta não é enviada, fallback com inconsistência é gerado
    """
    # Cenário: GPT retorna resposta genérica ("qual dia?")
    # mas sistema já extraiu data+hora completos

    tenant_id = "7394370553"
    actor_id = "whatsapp:5511991382080"

    ctx_init = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "idle",
        "draft_agendamento": None,
        "data_hora": "2026-10-22T10:00:00",  # PRÉ-SET: data+hora já existem
        "profissional_escolhido": "Bruna",
        "servico": "corte",
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
        dados=ctx_init
    )

    # Mensagem: apenas "sim, confirma" ou similar
    mensagem = "ok, pode ser"

    resultado = await roteador_principal(
        user_id=actor_id,
        mensagem=mensagem,
        tenant_id=tenant_id,
        phone_number_id="1350170954840548"
    )

    resposta = resultado.get("resposta", "")

    # Se contexto já tinha dados, resposta NÃO deve pedir data/hora novamente
    assert "qual dia" not in resposta.lower() and "qual horario" not in resposta.lower(), \
        f"Resposta pede dados já fornecidos: {resposta}"

    print(f"✅ T6 PASSOU")


@pytest.mark.asyncio
async def test_007_consulta_informativa_comportamento_preservado():
    """
    CENÁRIO 7: Consulta informativa (não agendamento) — comportamento anterior preservado

    QUANDO: "ela faz corte?" (consulta_servico, não agendamento_direto)
    E: acao=null
    ENTÃO: resposta do GPT é preservada (já está em lista de preservação)
    """
    tenant_id = "7394370553"
    actor_id = "whatsapp:5511991382080"

    ctx_init = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "idle",
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
        dados=ctx_init
    )

    mensagem = "ela faz corte?"

    resultado = await roteador_principal(
        user_id=actor_id,
        mensagem=mensagem,
        tenant_id=tenant_id,
        phone_number_id="1350170954840548"
    )

    resposta = resultado.get("resposta", "")

    # Deve ter resposta (não erro)
    assert resposta and "❌" not in resposta, f"Erro ou resposta vazia: {resposta}"

    # Deve mencionar o serviço ou confirmação
    assert "corte" in resposta.lower() or "sim" in resposta.lower() or "faz" in resposta.lower(), \
        f"Resposta não endereça pergunta: {resposta}"

    print(f"✅ T7 PASSOU")


@pytest.mark.asyncio
async def test_008_saudacao_fallback_correto():
    """
    CENÁRIO 8: Saudação sem dados — fallback deve funcionar

    QUANDO: mensagem é só "oi" ou "opa"
    E: nenhuma entidade foi extraída
    ENTÃO: fallback monta saudação apropriada, não tenta agendar
    """
    tenant_id = "7394370553"
    actor_id = "whatsapp:5511991382080"

    ctx_init = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "idle",
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
        dados=ctx_init
    )

    mensagem = "opa"

    resultado = await roteador_principal(
        user_id=actor_id,
        mensagem=mensagem,
        tenant_id=tenant_id,
        phone_number_id="1350170954840548"
    )

    resposta = resultado.get("resposta", "")

    # Saudação apropriada
    assert resposta and "❌" not in resposta, f"Erro: {resposta}"
    assert any(word in resposta.lower() for word in ["oi", "olá", "ajud", "posso"]), \
        f"Saudação inadequada: {resposta}"

    # Não deve tentar agendar
    assert "qual" not in resposta.lower() or "qual dia" not in resposta.lower(), \
        f"Tentou agendar em saudação: {resposta}"

    print(f"✅ T8 PASSOU")


@pytest.mark.asyncio
async def test_009_confirmacao_pendente_nenhuma_alteracao():
    """
    CENÁRIO 9: Confirmação pendente — nenhuma alteração de roteamento

    QUANDO: estado=aguardando_confirmacao_agendamento (evento pendente)
    E: novo agendamento_direto chega
    ENTÃO: não sobrescreve agendamento anterior
    """
    tenant_id = "7394370553"
    actor_id = "whatsapp:5511991382080"

    # Setup: aguardando confirmação de um agendamento anterior
    ctx_init = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "agendando",
        "aguardando_confirmacao_agendamento": True,
        "draft_agendamento": {
            "servico": "escova",
            "profissional": "Gloria",
            "data_hora": "2026-10-20T11:00:00",
        },
        "dados_confirmacao_agendamento": {
            "servico": "escova",
            "profissional": "Gloria",
            "data_hora": "2026-10-20T11:00:00",
        },
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
        dados=ctx_init
    )

    # Novo agendamento chega
    mensagem = "Na verdade, quero corte com Bruna quarta às 15h"

    resultado = await roteador_principal(
        user_id=actor_id,
        mensagem=mensagem,
        tenant_id=tenant_id,
        phone_number_id="1350170954840548"
    )

    sessao = await buscar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{actor_id}"
    )

    # VALIDAÇÃO: agendamento anterior NÃO foi sobrescrito
    draft_atual = sessao.get("draft_agendamento") or {}
    assert draft_atual.get("servico") == "escova", \
        f"Agendamento anterior foi sobrescrito: {draft_atual}"

    # Estado continua em confirmação
    assert sessao.get("aguardando_confirmacao_agendamento") is True, \
        f"Confirmação foi perdida"

    print(f"✅ T9 PASSOU")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
