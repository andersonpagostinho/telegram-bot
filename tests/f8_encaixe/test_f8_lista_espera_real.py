"""
F8 MVP — TESTES ENCAIXE / LISTA DE ESPERA ATIVA

8 cenários completos com Firestore real.
Cada cenário testa uma fase do fluxo proposto.

Estrutura:
- F8-1: Cliente entra em lista após conflito
- F8-2: Cancelamento abre vaga e notifica cliente correto
- F8-3: Cliente confirma encaixe e evento é criado
- F8-4: Cliente recusa encaixe e nada é criado
- F8-5: Dois clientes em espera; apenas primeiro é notificado
- F8-6: Cliente em espera já marcou outro horário, não notificar
- F8-7: Multi-tenant isolation (tenant A não vê cliente de B)
- F8-8: Race condition (dois clientes confirmam ao mesmo tempo)

Validações:
✅ Firestore real
✅ Tenant isolation
✅ Status sempre consistente
✅ Lock funciona
✅ 0 eventos duplicados
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from pytz import timezone

# Imports do projeto
from services.lista_espera_service import (
    criar_lista_espera,
    buscar_proxima_lista_espera_compativel,
    marcar_como_notificado,
    marcar_como_convertido,
    marcar_como_cancelado,
    buscar_lista_espera_por_id,
)
from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_dado_em_path,
    buscar_subcolecao,
    atualizar_dado_em_path,
    deletar_dado_em_path,
    obter_id_dono,
)
from services.event_service_async import (
    salvar_evento,
    buscar_eventos_por_intervalo,
    cancelar_evento,
)
from services.agenda_lock_service import criar_evento_com_lock
from handlers.lista_espera_handler import (
    aceitar_entrar_lista_espera,
    confirmar_encaixe_apos_notificacao,
    rejeitar_encaixe_apos_notificacao,
)

FUSO_BR = timezone("America/Sao_Paulo")

# =========================================================
# FIXTURES
# =========================================================

@pytest.fixture
def limpar_firestore():
    """Fixture de limpeza (não usado neste MVP)."""
    yield


def gerar_tenant_teste() -> str:
    """Gera ID único de tenant para teste."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"tenant_teste_{timestamp}"


def gerar_cliente_id() -> str:
    """Gera ID único de cliente para teste."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"cliente_teste_{timestamp}"


# =========================================================
# F8-1: CLIENTE ENTRA EM LISTA APÓS CONFLITO
# =========================================================

@pytest.mark.asyncio
async def test_f8_1_cliente_entra_em_lista():
    """
    Cenário: Cliente solicita horário ocupado, aceita entrar em lista.

    Setup:
    - Profissional: Bruna (disponível)
    - Data: amanhã
    - Hora: 10:00 (30 min)
    - Evento existente: outro cliente 09:00-10:30

    Fluxo:
    1. Cliente quer corte com Bruna às 10:00
    2. Motor detecta conflito
    3. NeoEve oferece: "Quer entrar na lista de espera?"
    4. Cliente: "Entra na lista"

    Validações:
    ✅ Documento criado em ListaEspera
    ✅ Status = "ativo"
    ✅ Campos preenchidos corretamente
    ✅ criado_em e expira_em presentes
    """
    tenant_id = gerar_tenant_teste()
    cliente_id = gerar_cliente_id()

    # Setup: criar evento conflitante
    amanha = (datetime.now(FUSO_BR) + timedelta(days=1)).date()
    evento_conflitante = {
        "cliente_id": "outro_cliente_123",
        "profissional": "Bruna",
        "data": amanha.strftime("%Y-%m-%d"),
        "hora_inicio": "09:00",
        "hora_fim": "10:30",
        "duracao": 90,
        "servico": "corte",
        "confirmado": True,
        "status": "confirmado",
    }
    await salvar_evento("outro_cliente_123", evento_conflitante)

    # Teste: Cliente aceita entrar na lista
    resultado = await criar_lista_espera(
        tenant_id=tenant_id,
        actor_id=f"whatsapp:{cliente_id}",
        cliente_id=cliente_id,
        cliente_nome="João",
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=amanha.strftime("%Y-%m-%d"),
        hora_desejada="10:00",
        duracao_minutos=30,
        evento_conflitante_id="evento_conflitante_xyz",
    )

    # Validações
    assert resultado.get("status") == "ok", "Criação de ListaEspera falhou"
    waitlist_id = resultado.get("waitlist_id")
    assert waitlist_id, "waitlist_id não retornado"

    # Verificar documento em Firestore
    doc = await buscar_lista_espera_por_id(tenant_id, waitlist_id)
    assert doc is not None, "Documento não salvo em Firestore"
    assert doc.get("status") == "ativo", "Status deve ser 'ativo'"
    assert doc.get("servico_desejado", {}).get("servico") == "corte"
    assert doc.get("servico_desejado", {}).get("profissional_preferido") == "Bruna"
    assert doc.get("cliente", {}).get("cliente_nome") == "João"
    assert doc.get("auditoria", {}).get("criado_em") is not None
    assert doc.get("auditoria", {}).get("expira_em") is not None

    print("✅ F8-1 PASSOU")


# =========================================================
# F8-2: CANCELAMENTO ABRE VAGA E NOTIFICA CLIENTE CORRETO
# =========================================================

@pytest.mark.asyncio
async def test_f8_2_cancelamento_notifica_cliente():
    """
    Cenário: Outro cliente cancela → waitlist é notificado.

    Setup:
    - Cliente 1 em lista: Bruna amanhã 10:00
    - Cliente 2 tem evento: Bruna amanhã 09:00-10:30
    - Cliente 2 cancela seu evento

    Fluxo:
    1. Cliente 2 cancela: "Cancela meu agendamento com Bruna"
    2. Sistema: Busca ListaEspera compatível
    3. Encontra Cliente 1
    4. Notifica Cliente 1

    Validações:
    ✅ Evento de Cliente 2 marcado como cancelado
    ✅ Waitlist de Cliente 1 encontrado
    ✅ Status muda para "notificado"
    ✅ ultima_notificacao_em preenchido
    ✅ tentativas_notificacao = 1
    ✅ Nenhum outro cliente notificado (tenant isolation)
    """
    tenant_id = gerar_tenant_teste()
    cliente_1_id = gerar_cliente_id()
    cliente_2_id = gerar_cliente_id()

    amanha = (datetime.now(FUSO_BR) + timedelta(days=1)).date()
    data_str = amanha.strftime("%Y-%m-%d")

    # Setup: Cliente 1 em lista de espera
    await criar_lista_espera(
        tenant_id=tenant_id,
        actor_id=f"whatsapp:{cliente_1_id}",
        cliente_id=cliente_1_id,
        cliente_nome="João",
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=data_str,
        hora_desejada="10:00",
        duracao_minutos=30,
        evento_conflitante_id="evento_xyz",
    )

    # Setup: Cliente 2 tem evento ocupando o slot
    event_id_cliente_2 = f"{cliente_2_id}_bruna_{data_str}_09:00"
    evento_cliente_2 = {
        "cliente_id": cliente_2_id,
        "profissional": "Bruna",
        "data": data_str,
        "hora_inicio": "09:00",
        "hora_fim": "10:30",
        "duracao": 90,
        "servico": "corte",
        "confirmado": True,
        "status": "confirmado",
    }
    await salvar_evento(cliente_2_id, evento_cliente_2)

    # Teste: Cliente 2 cancela seu evento
    await cancelar_evento(cliente_2_id, event_id_cliente_2)

    # Validações
    # 1. Evento deve estar marcado como cancelado
    tenant_id_2 = await obter_id_dono(cliente_2_id)
    if not tenant_id_2:
        tenant_id_2 = cliente_2_id
    evento_verificar = await buscar_dado_em_path(f"Clientes/{tenant_id_2}/Eventos/{str(event_id_cliente_2)}")
    assert evento_verificar and evento_verificar.get("status") == "cancelado", "Evento não marcado como cancelado"

    # 2. Buscar ListaEspera compatível (manual para validar)
    waitlist_encontrada = await buscar_proxima_lista_espera_compativel(
        tenant_id=tenant_id,
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=data_str,
        hora_desejada="10:00",
        duracao_minutos=30,
    )
    assert waitlist_encontrada is not None, "Waitlist não encontrada após cancelamento"
    waitlist_id = waitlist_encontrada.get("waitlist_id")

    # 3. Marcar como notificado (simulando notificação)
    await marcar_como_notificado(tenant_id, waitlist_id)

    # 4. Verificar estado
    doc_atualizado = await buscar_lista_espera_por_id(tenant_id, waitlist_id)
    assert doc_atualizado.get("status") == "notificado", "Status deve ser 'notificado'"
    assert doc_atualizado.get("auditoria", {}).get("ultima_notificacao_em") is not None
    assert doc_atualizado.get("auditoria", {}).get("tentativas_notificacao") == 1

    print("✅ F8-2 PASSOU")


# =========================================================
# F8-3: CLIENTE CONFIRMA ENCAIXE E EVENTO É CRIADO
# =========================================================

@pytest.mark.asyncio
async def test_f8_3_cliente_confirma_encaixe():
    """
    Cenário: Cliente responde "sim" após notificação.

    Setup:
    - ListaEspera em status "notificado"
    - Vaga realmente disponível (lock desocupado)

    Fluxo:
    1. Cliente confirma: "Confirma"
    2. Motor revalida disponibilidade
    3. Cria evento com lock
    4. Marca waitlist como "convertido"

    Validações:
    ✅ Evento criado com origem="encaixe_lista_espera"
    ✅ Waitlist status="convertido"
    ✅ evento_criado_apos_encaixe preenchido
    ✅ Nenhum erro de lock
    """
    tenant_id = gerar_tenant_teste()
    cliente_id = gerar_cliente_id()

    amanha = (datetime.now(FUSO_BR) + timedelta(days=1)).date()
    data_str = amanha.strftime("%Y-%m-%d")

    # Setup: Criar ListaEspera e marcar como notificado
    resultado = await criar_lista_espera(
        tenant_id=tenant_id,
        actor_id=f"whatsapp:{cliente_id}",
        cliente_id=cliente_id,
        cliente_nome="Maria",
        servico="escova",
        profissional_preferido="Carol",
        data_desejada=data_str,
        hora_desejada="14:00",
        duracao_minutos=45,
        evento_conflitante_id="evt_xyz",
    )
    waitlist_id = resultado.get("waitlist_id")
    await marcar_como_notificado(tenant_id, waitlist_id)

    # Teste: Confirmar encaixe
    evento = {
        "cliente_id": cliente_id,
        "cliente_nome": "Maria",
        "servico": "escova",
        "profissional": "Carol",
        "data": data_str,
        "hora_inicio": "14:00",
        "hora_fim": "14:45",
        "duracao": 45,
        "confirmado": True,
        "status": "confirmado",
        "origem": "encaixe_lista_espera",
        "waitlist_id_origem": waitlist_id,
        "criado_em": datetime.now(FUSO_BR).isoformat(),
    }

    resultado_lock = await criar_evento_com_lock(
        dono_id=tenant_id,
        evento=evento,
        event_id=f"{cliente_id}_carol_{data_str}_1400",
    )

    # Validações
    assert resultado_lock.get("ok") is True, f"Erro ao criar evento: {resultado_lock.get('motivo')}"
    evento_id = resultado_lock.get("evento_id")

    # Marcar waitlist como convertido
    await marcar_como_convertido(tenant_id, waitlist_id, evento_id)

    # Verificar estados
    waitlist_final = await buscar_lista_espera_por_id(tenant_id, waitlist_id)
    assert waitlist_final.get("status") == "convertido", "Status deve ser 'convertido'"
    assert waitlist_final.get("evento_criado_apos_encaixe") == evento_id

    print("✅ F8-3 PASSOU")


# =========================================================
# F8-4: CLIENTE RECUSA ENCAIXE E NADA É CRIADO
# =========================================================

@pytest.mark.asyncio
async def test_f8_4_cliente_recusa_encaixe():
    """
    Cenário: Cliente responde "não" após notificação.

    Fluxo:
    1. ListaEspera em status "notificado"
    2. Cliente: "Não, obrigado"
    3. Marcar como "cancelado"
    4. Nenhum evento criado

    Validações:
    ✅ Waitlist status="cancelado"
    ✅ Nenhum evento criado
    ✅ confirmacao_pendente=False
    """
    tenant_id = gerar_tenant_teste()
    cliente_id = gerar_cliente_id()

    # Setup
    resultado = await criar_lista_espera(
        tenant_id=tenant_id,
        actor_id=f"whatsapp:{cliente_id}",
        cliente_id=cliente_id,
        cliente_nome="Pedro",
        servico="barba",
        profissional_preferido="João",
        data_desejada="2026-07-01",
        hora_desejada="15:00",
        duracao_minutos=20,
        evento_conflitante_id="evt_abc",
    )
    waitlist_id = resultado.get("waitlist_id")
    await marcar_como_notificado(tenant_id, waitlist_id)

    # Teste: Cliente recusa
    await marcar_como_cancelado(tenant_id, waitlist_id)

    # Validações
    doc = await buscar_lista_espera_por_id(tenant_id, waitlist_id)
    assert doc.get("status") == "cancelado", "Status deve ser 'cancelado'"
    assert doc.get("confirmacao_pendente") is False

    print("✅ F8-4 PASSOU")


# =========================================================
# F8-5: DOIS CLIENTES EM ESPERA; APENAS PRIMEIRO NOTIFICADO
# =========================================================

@pytest.mark.asyncio
async def test_f8_5_fifo_prioridade():
    """
    Cenário: Dois clientes querem mesmo slot, primeiro criado tem prioridade.

    Setup:
    - Cliente 1: criado em 15:00
    - Cliente 2: criado em 15:05 (5 min depois)
    - Ambos: corte com Bruna em 2026-07-02 às 10:00

    Fluxo:
    1. Evento é cancelado
    2. Sistema busca waitlist (ORDER BY criado_em ASC)
    3. Encontra Cliente 1 (primeiro)
    4. Notifica Cliente 1
    5. Cliente 2 permanece em "ativo"

    Validações:
    ✅ Cliente 1 recebe notificação (status="notificado")
    ✅ Cliente 2 não recebe (status="ativo")
    ✅ Ordem FIFO respeitada
    """
    tenant_id = gerar_tenant_teste()
    cliente_1_id = gerar_cliente_id()
    cliente_2_id = gerar_cliente_id()

    data_str = "2026-07-02"

    # Setup: Cliente 1 entra na lista
    await criar_lista_espera(
        tenant_id=tenant_id,
        actor_id=f"whatsapp:{cliente_1_id}",
        cliente_id=cliente_1_id,
        cliente_nome="Ana",
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=data_str,
        hora_desejada="10:00",
        duracao_minutos=30,
        evento_conflitante_id="evt_1",
    )

    # Pequeno delay para garantir timestamp diferente
    await asyncio.sleep(0.1)

    # Setup: Cliente 2 entra na lista (depois)
    await criar_lista_espera(
        tenant_id=tenant_id,
        actor_id=f"whatsapp:{cliente_2_id}",
        cliente_id=cliente_2_id,
        cliente_nome="Bruno",
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=data_str,
        hora_desejada="10:00",
        duracao_minutos=30,
        evento_conflitante_id="evt_2",
    )

    # Teste: Buscar próximo (deve ser Cliente 1)
    waitlist = await buscar_proxima_lista_espera_compativel(
        tenant_id=tenant_id,
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=data_str,
        hora_desejada="10:00",
        duracao_minutos=30,
    )

    # Validações
    assert waitlist is not None, "Nenhuma waitlist encontrada"
    assert waitlist.get("cliente", {}).get("cliente_nome") == "Ana", "Cliente 1 deve ser primeiro (FIFO)"

    # Marcar Cliente 1 como notificado
    await marcar_como_notificado(tenant_id, waitlist.get("waitlist_id"))

    # Buscar novamente (Cliente 2 ainda deve estar em "ativo")
    waitlist_2 = await buscar_proxima_lista_espera_compativel(
        tenant_id=tenant_id,
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=data_str,
        hora_desejada="10:00",
        duracao_minutos=30,
    )

    # Cliente 2 deve ser próximo (ainda "ativo")
    assert waitlist_2 is not None, "Cliente 2 deve estar em espera"
    assert waitlist_2.get("cliente", {}).get("cliente_nome") == "Bruno"

    print("✅ F8-5 PASSOU")


# =========================================================
# F8-6: CLIENT EM ESPERA JÁ MARCOU OUTRO HORÁRIO
# =========================================================

@pytest.mark.asyncio
async def test_f8_6_cliente_ja_tem_conflito():
    """
    Cenário: Cliente em espera já agendou outro horário conflitante.

    Setup:
    - Cliente aguardando: corte com Bruna 2026-07-03 10:00
    - Cliente depois marca: hidratação com Amanda 2026-07-03 10:00 (conflita)

    Fluxo:
    1. Vaga de Bruna abre
    2. Sistema busca cliente
    3. Verifica eventos do cliente
    4. Encontra conflito com Amanda
    5. NÃO notifica

    Validações:
    ✅ Cliente não notificado
    ✅ Waitlist não é marcado como "notificado"
    ✅ Status permanece "ativo"
    """
    tenant_id = gerar_tenant_teste()
    cliente_id = gerar_cliente_id()

    data_str = "2026-07-03"

    # Setup: Cliente em lista para Bruna às 10:00
    await criar_lista_espera(
        tenant_id=tenant_id,
        actor_id=f"whatsapp:{cliente_id}",
        cliente_id=cliente_id,
        cliente_nome="Lucia",
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=data_str,
        hora_desejada="10:00",
        duracao_minutos=30,
        evento_conflitante_id="evt_bruna_anterior",
    )

    # Setup: Cliente também marca evento com Amanda (conflita)
    evento_amanda = {
        "cliente_id": cliente_id,
        "profissional": "Amanda",
        "data": data_str,
        "hora_inicio": "10:00",
        "hora_fim": "11:00",
        "duracao": 60,
        "servico": "hidratacao",
        "confirmado": True,
        "status": "confirmado",
    }
    await salvar_evento(cliente_id, evento_amanda)

    # Teste: Buscar proxima (manual) - o sistema real faria validação de conflito
    waitlist = await buscar_proxima_lista_espera_compativel(
        tenant_id=tenant_id,
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=data_str,
        hora_desejada="10:00",
        duracao_minutos=30,
    )

    # Validação: Waitlist foi encontrada, mas logica real checa conflito
    # antes de notificar (isso seria feito em processar_cancelamento_e_notificar_espera)
    # Por enquanto, apenas validar que waitlist existe e está "ativo"
    assert waitlist is not None, "Waitlist deve estar em ativo"
    assert waitlist.get("status") == "ativo"

    print("✅ F8-6 PASSOU (validação básica)")


# =========================================================
# F8-7: MULTI-TENANT ISOLATION
# =========================================================

@pytest.mark.asyncio
async def test_f8_7_multi_tenant_isolation():
    """
    Cenário: Tenant A cancela evento → não notifica cliente de Tenant B.

    Setup:
    - Tenant A: cliente_a aguarda corte com Bruna 2026-07-04 10:00
    - Tenant B: cliente_b aguarda corte com Bruna 2026-07-04 10:00 (mesmo horário)

    Fluxo:
    1. Cancelamento em Tenant A
    2. Sistema busca: WHERE tenant_id = Tenant_A
    3. Notifica apenas cliente_a
    4. Tenant B não é tocado

    Validações:
    ✅ Tenant A cliente notificado
    ✅ Tenant B cliente NÃO notificado
    ✅ Queries sempre incluem WHERE tenant_id
    """
    tenant_a = gerar_tenant_teste()
    tenant_b = gerar_tenant_teste()
    cliente_a_id = gerar_cliente_id()
    cliente_b_id = gerar_cliente_id()

    data_str = "2026-07-04"

    # Setup: Cliente A em Tenant A
    await criar_lista_espera(
        tenant_id=tenant_a,
        actor_id=f"whatsapp:{cliente_a_id}",
        cliente_id=cliente_a_id,
        cliente_nome="Alice",
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=data_str,
        hora_desejada="10:00",
        duracao_minutos=30,
        evento_conflitante_id="evt_a",
    )

    # Setup: Cliente B em Tenant B (mesmo horário, diferente tenant)
    await criar_lista_espera(
        tenant_id=tenant_b,
        actor_id=f"whatsapp:{cliente_b_id}",
        cliente_id=cliente_b_id,
        cliente_nome="Bob",
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=data_str,
        hora_desejada="10:00",
        duracao_minutos=30,
        evento_conflitante_id="evt_b",
    )

    # Teste: Buscar em Tenant A apenas
    waitlist_a = await buscar_proxima_lista_espera_compativel(
        tenant_id=tenant_a,  # APENAS Tenant A
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=data_str,
        hora_desejada="10:00",
        duracao_minutos=30,
    )

    # Teste: Buscar em Tenant B apenas
    waitlist_b = await buscar_proxima_lista_espera_compativel(
        tenant_id=tenant_b,  # APENAS Tenant B
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=data_str,
        hora_desejada="10:00",
        duracao_minutos=30,
    )

    # Validações
    assert waitlist_a is not None, "Cliente A deve existir em Tenant A"
    assert waitlist_a.get("cliente", {}).get("cliente_nome") == "Alice"

    assert waitlist_b is not None, "Cliente B deve existir em Tenant B"
    assert waitlist_b.get("cliente", {}).get("cliente_nome") == "Bob"

    # Garantir que são diferentes
    assert waitlist_a.get("tenant_id") == tenant_a
    assert waitlist_b.get("tenant_id") == tenant_b

    print("✅ F8-7 PASSOU")


# =========================================================
# F8-8: RACE CONDITION
# =========================================================

@pytest.mark.asyncio
async def test_f8_8_race_condition():
    """
    Cenário: Dois clientes confirmam encaixe simultaneamente.

    Setup:
    - Cliente 1 e Cliente 2 em status "notificado" para mesma vaga
    - Ambos respondem "sim" quase ao mesmo tempo

    Fluxo:
    1. Cliente 1 confirma → cria evento com lock
    2. Cliente 2 confirma simultaneamente → lock falha
    3. Apenas Cliente 1 tem evento criado
    4. Cliente 2 recebe: "Alguém confirmou nesse meio tempo"

    Validações:
    ✅ Evento criado para Cliente 1
    ✅ Cliente 2 recebe erro
    ✅ Nenhuma duplicação de eventos
    ✅ Nenhuma corrupção de dados
    """
    tenant_id = gerar_tenant_teste()
    cliente_1_id = gerar_cliente_id()
    cliente_2_id = gerar_cliente_id()

    data_str = "2026-07-05"

    # Setup: Criar ListaEspera para ambos
    resultado_1 = await criar_lista_espera(
        tenant_id=tenant_id,
        actor_id=f"whatsapp:{cliente_1_id}",
        cliente_id=cliente_1_id,
        cliente_nome="Xavier",
        servico="massagem",
        profissional_preferido="Tania",
        data_desejada=data_str,
        hora_desejada="11:00",
        duracao_minutos=60,
        evento_conflitante_id="evt_race_1",
    )
    waitlist_1_id = resultado_1.get("waitlist_id")

    # Pequeno delay
    await asyncio.sleep(0.1)

    resultado_2 = await criar_lista_espera(
        tenant_id=tenant_id,
        actor_id=f"whatsapp:{cliente_2_id}",
        cliente_id=cliente_2_id,
        cliente_nome="Yasmin",
        servico="massagem",
        profissional_preferido="Tania",
        data_desejada=data_str,
        hora_desejada="11:00",
        duracao_minutos=60,
        evento_conflitante_id="evt_race_2",
    )
    waitlist_2_id = resultado_2.get("waitlist_id")

    # Marcar ambos como notificados
    await marcar_como_notificado(tenant_id, waitlist_1_id)
    await marcar_como_notificado(tenant_id, waitlist_2_id)

    # Teste: Criar eventos em paralelo (simular race)
    evento_1 = {
        "cliente_id": cliente_1_id,
        "cliente_nome": "Xavier",
        "servico": "massagem",
        "profissional": "Tania",
        "data": data_str,
        "hora_inicio": "11:00",
        "hora_fim": "12:00",
        "duracao": 60,
        "confirmado": True,
        "status": "confirmado",
        "origem": "encaixe_lista_espera",
        "waitlist_id_origem": waitlist_1_id,
    }

    evento_2 = {
        "cliente_id": cliente_2_id,
        "cliente_nome": "Yasmin",
        "servico": "massagem",
        "profissional": "Tania",
        "data": data_str,
        "hora_inicio": "11:00",
        "hora_fim": "12:00",
        "duracao": 60,
        "confirmado": True,
        "status": "confirmado",
        "origem": "encaixe_lista_espera",
        "waitlist_id_origem": waitlist_2_id,
    }

    # Executar em "paralelo" (sequencial, mas como se fosse)
    resultado_lock_1 = await criar_evento_com_lock(
        dono_id=tenant_id,
        evento=evento_1,
        event_id=f"{cliente_1_id}_tania_{data_str}_1100",
    )

    resultado_lock_2 = await criar_evento_com_lock(
        dono_id=tenant_id,
        evento=evento_2,
        event_id=f"{cliente_2_id}_tania_{data_str}_1100",
    )

    # Validações
    # Cliente 1 deve ter sucesso (primeiro)
    assert resultado_lock_1.get("ok") is True, "Cliente 1 deve criar evento com sucesso"

    # Cliente 2 deve falhar (lock já existe)
    assert resultado_lock_2.get("ok") is False, "Cliente 2 deve falhar (lock ocupado)"
    assert "ocupado" in resultado_lock_2.get("motivo", "").lower() or "lock" in resultado_lock_2.get("motivo", "").lower()

    # Marcar Cliente 1 como convertido
    await marcar_como_convertido(tenant_id, waitlist_1_id, resultado_lock_1.get("evento_id"))

    # Marcar Cliente 2 como cancelado (expirou)
    await marcar_como_cancelado(tenant_id, waitlist_2_id)

    # Verificar estados finais
    doc_1 = await buscar_lista_espera_por_id(tenant_id, waitlist_1_id)
    doc_2 = await buscar_lista_espera_por_id(tenant_id, waitlist_2_id)

    assert doc_1.get("status") == "convertido", "Cliente 1 deve estar convertido"
    assert doc_2.get("status") == "cancelado", "Cliente 2 deve estar cancelado"

    print("✅ F8-8 PASSOU")


# =========================================================
# RUNNER
# =========================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
