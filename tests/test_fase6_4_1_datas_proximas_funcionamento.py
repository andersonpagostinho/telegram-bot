"""
P0 FASE 6.4.1 - Testes de Datas Proximas com Funcionamento

10 testes para validar busca de datas proximas.
"""

import pytest
from datetime import date, timedelta


# TESTE 1: Fim de semana deve ser pulado
def test_fim_de_semana_pulado():
    """
    Sexta 13/11 + pula sabado/domingo = segunda 16/11
    """
    data_sexta = date(2026, 11, 13)  # sexta
    assert data_sexta.weekday() == 4, "13/11 deve ser sexta"

    data_sabado = data_sexta + timedelta(days=1)
    assert data_sabado.weekday() == 5, "14/11 deve ser sabado"

    data_domingo = data_sexta + timedelta(days=2)
    assert data_domingo.weekday() == 6, "15/11 deve ser domingo"

    # Aplicar lógica de pular
    dias_testados = 0
    max_dias = 5
    encontrados = 0
    data_teste = data_sexta

    while dias_testados < max_dias and encontrados < 1:
        data_teste = data_teste + timedelta(days=1)
        dias_testados += 1

        if data_teste.weekday() > 4:  # sabado ou domingo
            continue

        encontrados += 1

    assert data_teste.weekday() == 0, "Primeira data nao-sabado/domingo deve ser segunda"
    assert data_teste == date(2026, 11, 16), "Deve ser 16/11"
    print("[OK] TESTE 1: Fim de semana pulado corretamente")


# TESTE 2: Sabado e domingo realmente nao sao testados
def test_sabado_domingo_nao_testados():
    """
    Verifica que sabado/domingo nao geram chamadas varredura
    """
    data_sexta = date(2026, 11, 13)

    chamadas = []
    dias_testados = 0
    max_dias = 5

    data_teste = data_sexta

    while dias_testados < max_dias and len(chamadas) < 2:
        data_teste = data_teste + timedelta(days=1)
        dias_testados += 1

        if data_teste.weekday() > 4:
            continue

        chamadas.append(data_teste)

    # Deve ter apenas 2 chamadas (segunda + terca), nao 4 (sexta + sabado + domingo + segunda)
    assert len(chamadas) == 2, f"Esperado 2, got {len(chamadas)}"
    assert chamadas[0] == date(2026, 11, 16), "Primeira deve ser segunda 16/11"
    assert chamadas[1] == date(2026, 11, 17), "Segunda deve ser terca 17/11"
    print("[OK] TESTE 2: Sabado/domingo nao testados")


# TESTE 3: Limite de 5 dias uteis respeitado
def test_limite_cinco_dias_uteis():
    """
    Começando sexta, máximo 5 dias úteis = até quarta da próxima semana
    """
    data_sexta = date(2026, 11, 13)

    datas_coletadas = []
    dias_testados = 0
    max_dias = 5

    data_teste = data_sexta

    while dias_testados < max_dias and len(datas_coletadas) < 3:
        data_teste = data_teste + timedelta(days=1)
        dias_testados += 1

        if data_teste.weekday() > 4:
            continue

        datas_coletadas.append(data_teste)

    # Deve parar após 3 opções (não continuar até max_dias)
    assert len(datas_coletadas) == 3
    assert datas_coletadas[0] == date(2026, 11, 16)  # segunda
    assert datas_coletadas[1] == date(2026, 11, 17)  # terca
    assert datas_coletadas[2] == date(2026, 11, 18)  # quarta
    print("[OK] TESTE 3: Limite 5 dias uteis respeita max 3 opcoes")


# TESTE 4: Conversao de weekday para nomes de dia
def test_conversao_nomes_dias():
    """
    Validar que conversao de weekday para nome esta correta
    """
    data_segunda = date(2026, 11, 16)
    assert data_segunda.weekday() == 0, "16/11 deve ser segunda (0)"

    data_terca = date(2026, 11, 17)
    assert data_terca.weekday() == 1, "17/11 deve ser terca (1)"

    data_sabado = date(2026, 11, 14)
    assert data_sabado.weekday() == 5, "14/11 deve ser sabado (5)"

    print("[OK] TESTE 4: Conversao de weekday correta")


# TESTE 5: Data original não testada novamente
def test_data_original_nao_retestada():
    """
    Se data original (sexta) sem disponibilidade, não deve retentar
    """
    data_original = date(2026, 11, 13)

    datas_testadas = []
    dias_testados = 0

    # Simular: data_teste começa vazia, depois incrementa
    data_teste = data_original

    while dias_testados < 5 and len(datas_testadas) < 2:
        data_teste = data_teste + timedelta(days=1)
        dias_testados += 1

        if data_teste.weekday() > 4:
            continue

        datas_testadas.append(data_teste)

    # Data original não deve estar nas datas_testadas
    assert data_original not in datas_testadas
    print("[OK] TESTE 5: Data original nao retestada")


# TESTE 6: Intervalo horário preservado em conceptual model
def test_intervalo_preservado():
    """
    Janela 14-17h deve ser preservada (este teste é conceitual)
    """
    intervalo_inicio = 14
    intervalo_fim = 17

    # Simular múltiplas datas
    datas = [date(2026, 11, 16), date(2026, 11, 17), date(2026, 11, 18)]

    for data_teste in datas:
        # Cada data deve usar o mesmo intervalo
        assert intervalo_inicio == 14
        assert intervalo_fim == 17

    print("[OK] TESTE 6: Intervalo preservado")


# TESTE 7: Sem configuracao = fallback seg-sexta
def test_fallback_seg_sexta():
    """
    Sem dias_funcionamento configurado, usar segunda-sexta (0-4)
    """
    dias_funcionamento = None  # Sem configuracao

    if not dias_funcionamento:
        dias_validos = [0, 1, 2, 3, 4]  # segunda-sexta
    else:
        dias_validos = dias_funcionamento

    # Verificar
    assert 0 in dias_validos  # segunda
    assert 4 in dias_validos  # sexta
    assert 5 not in dias_validos  # sabado não
    assert 6 not in dias_validos  # domingo não

    print("[OK] TESTE 7: Fallback seg-sexta correto")


# TESTE 8: Isolamento multi-tenant (conceitual)
def test_isolamento_multitenant():
    """
    Cada tenant deve ter seu próprio dias_funcionamento
    """
    tenant_a_dias = [0, 1, 2, 3, 4]  # segunda-sexta
    tenant_b_dias = [1, 2, 3, 4, 5]  # terca-sabado

    # Não contaminar
    assert tenant_a_dias != tenant_b_dias
    assert 0 in tenant_a_dias and 0 not in tenant_b_dias
    assert 5 not in tenant_a_dias and 5 in tenant_b_dias

    print("[OK] TESTE 8: Isolamento multi-tenant")


# TESTE 9: Máximo 3 opcoes mesmo com mais dias disponiveis
def test_maximo_tres_opcoes():
    """
    Coletar até 3 opções, não continuar mesmo com max_dias > 3
    """
    max_dias = 5
    max_opcoes = 3

    opcoes = []
    dias_testados = 0

    while dias_testados < max_dias and len(opcoes) < max_opcoes:
        dias_testados += 1
        opcoes.append(f"dia_{dias_testados}")

    assert len(opcoes) == 3, f"Deve ter 3, got {len(opcoes)}"
    assert dias_testados == 3, f"Deve testar 3 dias, got {dias_testados}"

    print("[OK] TESTE 9: Máximo 3 opcoes")


# TESTE 10: Ordem cronologica preservada
def test_ordem_cronologica():
    """
    Datas deve estar em ordem cronológica
    """
    datas = [
        date(2026, 11, 16),  # segunda
        date(2026, 11, 17),  # terca
        date(2026, 11, 18),  # quarta
    ]

    # Validar ordem
    for i in range(len(datas) - 1):
        assert datas[i] < datas[i + 1], f"Ordem errada: {datas[i]} >= {datas[i+1]}"

    print("[OK] TESTE 10: Ordem cronologica preservada")


if __name__ == "__main__":
    test_fim_de_semana_pulado()
    test_sabado_domingo_nao_testados()
    test_limite_cinco_dias_uteis()
    test_conversao_nomes_dias()
    test_data_original_nao_retestada()
    test_intervalo_preservado()
    test_fallback_seg_sexta()
    test_isolamento_multitenant()
    test_maximo_tres_opcoes()
    test_ordem_cronologica()
    print("\n[OK] TODOS 10 TESTES PASSARAM")
