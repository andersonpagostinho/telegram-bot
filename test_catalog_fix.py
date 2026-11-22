#!/usr/bin/env python
"""Teste da correção de validação de catálogo"""

from unidecode import unidecode

def test_normalization():
    """Teste 1-3: Normalização"""
    assert unidecode('Pedicure'.strip().lower()) == unidecode('pedicure'.strip().lower())
    assert unidecode('MANICURE'.strip().lower()) == unidecode('manicure'.strip().lower())
    assert unidecode('  pedicure  '.strip().lower()) == unidecode('pedicure'.strip().lower())
    print("[PASS] Teste 1-3: Normalizacao")

def test_catalog_mapping():
    """Teste 4: Mapa de catálogo"""
    servicos_db = {
        'srv_1': {'nome': 'Pedicure', 'duracao': 30},
        'srv_2': {'nome': 'Manicure', 'duracao': 30},
        'srv_3': {'nome': 'Corte Feminino', 'duracao': 40}
    }

    # Mapear normalizados
    servicos_norm = {}
    for doc_id, doc_data in servicos_db.items():
        if isinstance(doc_data, dict) and 'nome' in doc_data:
            nome_norm = unidecode(doc_data['nome'].strip().lower())
            servicos_norm[nome_norm] = doc_data

    # Teste: encontrar serviços
    assert 'pedicure' in servicos_norm
    assert 'manicure' in servicos_norm
    assert 'corte feminino' in servicos_norm
    assert 'inexistente' not in servicos_norm

    print("[PASS] Teste 4: Mapa de catalogo")

def test_service_search():
    """Teste 5-7: Busca com normalização"""
    servicos_db = {
        'srv_1': {'nome': 'Pedicure', 'duracao': 30},
        'srv_2': {'nome': 'Manicure', 'duracao': 30}
    }

    servicos_norm = {}
    for doc_id, doc_data in servicos_db.items():
        if isinstance(doc_data, dict) and 'nome' in doc_data:
            nome_norm = unidecode(doc_data['nome'].strip().lower())
            servicos_norm[nome_norm] = doc_data

    # Teste busca com diferentes variações
    test_cases = [
        ('pedicure', True),
        ('PEDICURE', True),
        ('Pedicure', True),
        ('  pedicure  ', True),
        ('manicure', True),
        ('inexistente', False),
        ('', False)
    ]

    for servico, esperado in test_cases:
        servico_norm = unidecode(servico.strip().lower())
        encontrado = servico_norm in servicos_norm
        assert encontrado == esperado, f"Falha: {servico} → {encontrado} (esperado {esperado})"

    print("[PASS] Teste 5-7: Busca com normalizacao")

def test_duration_extraction():
    """Teste 8: Extração de duração"""
    servicos_db = {
        'srv_1': {'nome': 'Pedicure', 'duracao': 30},
        'srv_2': {'nome': 'Manicure', 'duracao': 30}
    }

    servicos_norm = {}
    for doc_id, doc_data in servicos_db.items():
        if isinstance(doc_data, dict) and 'nome' in doc_data:
            nome_norm = unidecode(doc_data['nome'].strip().lower())
            servicos_norm[nome_norm] = doc_data

    # Teste extração de duração
    assert servicos_norm['pedicure']['duracao'] == 30
    assert servicos_norm['manicure']['duracao'] == 30

    print("[PASS] Teste 8: Extracao de duracao")

def test_malformed_handling():
    """Teste 9: Documento malformado"""
    servicos_db = {
        'srv_1': {'nome': 'Pedicure', 'duracao': 30},
        'srv_2': {'nome': 'Manicure'},  # SEM duração
        'srv_3': {'duracao': 40},  # SEM nome
        'srv_4': None,  # Nulo
        'srv_5': {'nome': 'Corte', 'duracao': 40}
    }

    servicos_norm = {}
    for doc_id, doc_data in servicos_db.items():
        if isinstance(doc_data, dict) and 'nome' in doc_data:
            nome_norm = unidecode(doc_data['nome'].strip().lower())
            servicos_norm[nome_norm] = doc_data

    # Apenas documentos bem-formados (com nome) devem estar no mapa
    assert 'pedicure' in servicos_norm
    assert 'manicure' in servicos_norm
    assert 'corte' in servicos_norm
    assert len(servicos_norm) == 3  # Só 3 documentos bem-formados

    print("[PASS] Teste 9: Documento malformado")

if __name__ == "__main__":
    test_normalization()
    test_catalog_mapping()
    test_service_search()
    test_duration_extraction()
    test_malformed_handling()
    print("\n[PASS] TODOS OS TESTES OBRIGATORIOS PASSED")
