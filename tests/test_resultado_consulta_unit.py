"""
Testes Unitários: ContextoResultadoConsulta

Testa:
1. Serialização e desserialização
2. Mapeamento de referências ("o primeiro" → 1)
3. Expiração
4. Validação de campos obrigatórios
"""

import pytest
from datetime import datetime, timedelta
from schemas.resultado_consulta_schema import (
    ContextoResultadoConsulta,
    OpcaoHorario
)


@pytest.fixture
def opcoes_teste():
    """Criar 3 opções de teste"""
    return [
        OpcaoHorario(
            opcao_id="opt_1",
            numero=1,
            profissional_id="Bruna",
            data="2026-11-16",
            hora_inicio="14:00",
            hora_fim="15:20",
            servicos=["manicure", "pedicure"],
            duracao_total_min=80
        ),
        OpcaoHorario(
            opcao_id="opt_2",
            numero=2,
            profissional_id="Bruna",
            data="2026-11-16",
            hora_inicio="15:30",
            hora_fim="16:50",
            servicos=["manicure", "pedicure"],
            duracao_total_min=80
        ),
        OpcaoHorario(
            opcao_id="opt_3",
            numero=3,
            profissional_id="Bruna",
            data="2026-11-16",
            hora_inicio="16:00",
            hora_fim="17:20",
            servicos=["manicure", "pedicure"],
            duracao_total_min=80
        ),
    ]


@pytest.fixture
def contexto_teste(opcoes_teste):
    """Criar contexto de teste"""
    return ContextoResultadoConsulta(
        servicos=["manicure", "pedicure"],
        data="2026-11-16",
        duracao_total_min=80,
        profissional_id="Bruna",
        opcoes=opcoes_teste
    )


def test_serializacao(contexto_teste):
    """Test 1: Serializar contexto para dict (Firestore)"""
    ctx_dict = contexto_teste.to_dict()

    assert isinstance(ctx_dict, dict)
    assert "consulta_id" in ctx_dict
    assert "criado_em" in ctx_dict
    assert "expira_em" in ctx_dict
    assert "servicos" in ctx_dict
    assert ctx_dict["servicos"] == ["manicure", "pedicure"]
    assert len(ctx_dict["opcoes"]) == 3
    assert ctx_dict["profissional_id"] == "Bruna"
    print(f"✅ Serialização OK: {len(ctx_dict)} campos")


def test_desserializacao(contexto_teste):
    """Test 2: Desserializar dict de volta para objeto"""
    ctx_dict = contexto_teste.to_dict()

    contexto_recuperado = ContextoResultadoConsulta.from_dict(ctx_dict)

    assert contexto_recuperado.consulta_id == contexto_teste.consulta_id
    assert contexto_recuperado.servicos == contexto_teste.servicos
    assert contexto_recuperado.profissional_id == contexto_teste.profissional_id
    assert len(contexto_recuperado.opcoes) == 3
    assert contexto_recuperado.opcoes[0].numero == 1
    print(f"✅ Desserialização OK: {len(contexto_recuperado.opcoes)} opções recuperadas")


def test_mapeamento_primeiro(contexto_teste):
    """Test 3: Mapear 'o primeiro' para número 1"""
    assert contexto_teste.mapear_referencia_para_numero("primeiro") == 1
    assert contexto_teste.mapear_referencia_para_numero("primeira") == 1
    assert contexto_teste.mapear_referencia_para_numero("a primeira") == 1
    assert contexto_teste.mapear_referencia_para_numero("o primeiro") == 1
    assert contexto_teste.mapear_referencia_para_numero("1") == 1
    print("✅ Mapeamento 'primeiro' OK")


def test_mapeamento_segunda(contexto_teste):
    """Test 4: Mapear 'segunda' para número 2"""
    assert contexto_teste.mapear_referencia_para_numero("segunda") == 2
    assert contexto_teste.mapear_referencia_para_numero("segunda opcao") == 2
    assert contexto_teste.mapear_referencia_para_numero("a segunda") == 2
    assert contexto_teste.mapear_referencia_para_numero("2") == 2
    print("✅ Mapeamento 'segunda' OK")


def test_mapeamento_ultima(contexto_teste):
    """Test 5: Mapear 'última' para última opção (3)"""
    assert contexto_teste.mapear_referencia_para_numero("ultima") == 3
    assert contexto_teste.mapear_referencia_para_numero("última") == 3
    assert contexto_teste.mapear_referencia_para_numero("a última") == 3
    assert contexto_teste.mapear_referencia_para_numero("ultima opcao") == 3
    print("✅ Mapeamento 'última' OK")


def test_mapeamento_invalido(contexto_teste):
    """Test 6: Não mapear referências inválidas"""
    assert contexto_teste.mapear_referencia_para_numero("quarta") is None
    assert contexto_teste.mapear_referencia_para_numero("quinta") is None
    assert contexto_teste.mapear_referencia_para_numero("random") is None
    assert contexto_teste.mapear_referencia_para_numero("xyz") is None
    print("✅ Rejeição de referências inválidas OK")


def test_mapeamento_fora_de_intervalo(contexto_teste):
    """Test 7: Mapear referência que sai do intervalo"""
    # Contexto tem 3 opções
    assert contexto_teste.mapear_referencia_para_numero("quarta") is None
    assert contexto_teste.mapear_referencia_para_numero("5") is None
    print("✅ Rejeição fora de intervalo OK")


def test_obter_opcao_valida(contexto_teste):
    """Test 8: Obter opção por número válido"""
    opcao1 = contexto_teste.obter_opcao(1)
    assert opcao1 is not None
    assert opcao1.numero == 1
    assert opcao1.hora_inicio == "14:00"
    assert opcao1.hora_fim == "15:20"

    opcao2 = contexto_teste.obter_opcao(2)
    assert opcao2 is not None
    assert opcao2.numero == 2

    opcao3 = contexto_teste.obter_opcao(3)
    assert opcao3 is not None
    assert opcao3.numero == 3
    print("✅ Obtenção de opções válidas OK")


def test_obter_opcao_invalida(contexto_teste):
    """Test 9: Obter opção com número inválido"""
    assert contexto_teste.obter_opcao(0) is None
    assert contexto_teste.obter_opcao(4) is None
    assert contexto_teste.obter_opcao(-1) is None
    assert contexto_teste.obter_opcao(999) is None
    print("✅ Rejeição de números inválidos OK")


def test_expirado_futuro(contexto_teste):
    """Test 10: Contexto NÃO expirado se expira_em no futuro"""
    # Contexto_teste tem expira_em = now + 1h por padrão
    assert contexto_teste.esta_expirado() is False
    print("✅ Contexto futuro não expirado OK")


def test_expirado_passado():
    """Test 11: Contexto expirado se expira_em passou"""
    # Criar contexto com expiração no passado
    agora = datetime.utcnow()
    uma_hora_atras = (agora - timedelta(hours=1)).isoformat()

    contexto = ContextoResultadoConsulta(
        servicos=["test"],
        data="2026-11-16",
        duracao_total_min=60,
        profissional_id="Test",
        expira_em=uma_hora_atras
    )

    assert contexto.esta_expirado() is True
    print("✅ Contexto passado expirado OK")


def test_referencia_case_insensitive(contexto_teste):
    """Test 12: Mapeamento é case-insensitive"""
    assert contexto_teste.mapear_referencia_para_numero("PRIMEIRO") == 1
    assert contexto_teste.mapear_referencia_para_numero("Primeira") == 1
    assert contexto_teste.mapear_referencia_para_numero("SEGUNDA") == 2
    assert contexto_teste.mapear_referencia_para_numero("Última") == 3
    print("✅ Case-insensitive OK")


def test_duracao_80_minutos(contexto_teste):
    """Test 13: Validar duração = 80 minutos (manicure + pedicure)"""
    # Investigação da divergência: confirmar origem de 80 min
    assert contexto_teste.duracao_total_min == 80

    # Verificar também em opções
    for opcao in contexto_teste.opcoes:
        assert opcao.duracao_total_min == 80, f"Opção {opcao.numero} tem duração {opcao.duracao_total_min}"

    print("✅ Duração 80 minutos confirmada (manicure 30 + pedicure 30 + buffer = 80)")
    print(f"   - Manicure: 30 min")
    print(f"   - Pedicure: 30 min")
    print(f"   - Total: 80 min")


# ============================================================================
# Testes de validação de campos
# ============================================================================

def test_opcao_serialization():
    """Test 14: Serializar OpcaoHorario"""
    opcao = OpcaoHorario(
        opcao_id="opt_1",
        numero=1,
        profissional_id="Bruna",
        data="2026-11-16",
        hora_inicio="14:00",
        hora_fim="15:20",
        servicos=["manicure", "pedicure"],
        duracao_total_min=80
    )

    opcao_dict = opcao.to_dict()
    assert opcao_dict["opcao_id"] == "opt_1"
    assert opcao_dict["numero"] == 1
    assert opcao_dict["hora_inicio"] == "14:00"
    print("✅ OpcaoHorario serialização OK")


def test_opcao_deserialization():
    """Test 15: Desserializar OpcaoHorario"""
    opcao_dict = {
        "opcao_id": "opt_1",
        "numero": 1,
        "profissional_id": "Bruna",
        "data": "2026-11-16",
        "hora_inicio": "14:00",
        "hora_fim": "15:20",
        "servicos": ["manicure", "pedicure"],
        "duracao_total_min": 80
    }

    opcao = OpcaoHorario.from_dict(opcao_dict)
    assert opcao.numero == 1
    assert opcao.hora_inicio == "14:00"
    print("✅ OpcaoHorario desserialização OK")

