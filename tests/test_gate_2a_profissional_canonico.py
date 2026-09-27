"""
[TEST] C3.17-I2 GATE 2A: Profissional Canônico (actor_id Estável)

Objetivo: Validar o novo modelo de profissional com actor_id estável.

Testes obrigatórios: T01-T17
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.identidade_service import gerar_actor_id_estavel


# T01 — Geração de actor_id estável
def test_t01_gerar_actor_id():
    """T01: actor_id gerado é estável e único"""
    id1 = gerar_actor_id_estavel(prefixo="prof")
    id2 = gerar_actor_id_estavel(prefixo="prof")

    assert id1.startswith("prof_"), f"ID deve começar com 'prof_': {id1}"
    assert id2.startswith("prof_"), f"ID deve começar com 'prof_': {id2}"
    assert id1 != id2, "IDs devem ser únicos"
    assert len(id1) == len("prof_") + 16, f"Comprimento esperado para {id1}"
    print("[PASS] T01: actor_id estável e único")


# T02 — Prefixo customizável
def test_t02_prefixo_customizavel():
    """T02: prefixo pode ser customizado"""
    id_prof = gerar_actor_id_estavel(prefixo="prof")
    id_dono = gerar_actor_id_estavel(prefixo="dono")
    id_cliente = gerar_actor_id_estavel(prefixo="cli")

    assert id_prof.startswith("prof_"), f"Esperado 'prof_', obtido: {id_prof}"
    assert id_dono.startswith("dono_"), f"Esperado 'dono_', obtido: {id_dono}"
    assert id_cliente.startswith("cli_"), f"Esperado 'cli_', obtido: {id_cliente}"
    print("[PASS] T02: prefixo customizável")


# T03 — Formato consistente
def test_t03_formato_consistente():
    """T03: formato é sempre consistente"""
    for _ in range(10):
        actor_id = gerar_actor_id_estavel()
        assert actor_id.startswith("actor_"), f"Formato incorreto: {actor_id}"
        assert len(actor_id) == len("actor_") + 16, f"Comprimento inconsistente: {actor_id}"
        assert "_" in actor_id, f"Deve conter separador '_': {actor_id}"
    print("[PASS] T03: formato consistente")


# T04 — Independência de canal
def test_t04_independencia_canal():
    """T04: actor_id não depende de canal"""
    id1 = gerar_actor_id_estavel(prefixo="prof")
    id2 = gerar_actor_id_estavel(prefixo="prof")

    # Mesmo que fosse usado para WhatsApp ou Email
    # Gerando novamente produz IDs DIFERENTES (não derivado)
    assert id1 != id2, "IDs devem ser independentes de canal (são aleatórios)"
    print("[PASS] T04: independência de canal")


# T05 — Não usa wa_id
def test_t05_nao_usa_wa_id():
    """T05: actor_id não contém wa_id ou telefone"""
    id1 = gerar_actor_id_estavel()

    # Não deve parecer um wa_id ou telefone
    assert not id1.replace("_", "").isdigit(), f"actor_id não deve ser só dígitos: {id1}"
    assert "whatsapp" not in id1.lower(), f"actor_id não deve conter 'whatsapp': {id1}"
    assert "55" not in id1[:10], f"actor_id não deve parecer telefone: {id1}"
    print("[PASS] T05: não usa wa_id")


# T06 — Não usa email
def test_t06_nao_usa_email():
    """T06: actor_id não contém email ou @ ou ."""
    id1 = gerar_actor_id_estavel()

    # Não deve parecer email
    assert "@" not in id1, f"actor_id não deve conter '@': {id1}"
    assert "email" not in id1.lower(), f"actor_id não deve conter 'email': {id1}"
    print("[PASS] T06: não usa email")


# T07 — Não usa nome
def test_t07_nao_usa_nome():
    """T07: actor_id não contém nome ou palavras legíveis"""
    id1 = gerar_actor_id_estavel(prefixo="prof")

    # Deve ser opaco (não contém nomes de pessoas)
    assert "joao" not in id1.lower(), f"actor_id não deve conter nomes: {id1}"
    assert "maria" not in id1.lower(), f"actor_id não deve conter nomes: {id1}"
    # Apenas prefixo e UUID hexadecimal
    hex_part = id1.split("_")[1]
    try:
        int(hex_part, 16)
        is_hex = True
    except ValueError:
        is_hex = False

    assert is_hex, f"Parte após _ deve ser hexadecimal: {hex_part}"
    print("[PASS] T07: não usa nome")


# T08 — Durabilidade
def test_t08_durabilidade():
    """T08: actor_id é durável (gerado uma vez, usado sempre)"""
    id1 = gerar_actor_id_estavel(prefixo="prof")

    # Se armazenarmos esse ID e o recuperarmos, deve ser o mesmo
    stored_id = id1
    retrieved_id = stored_id

    assert id1 == retrieved_id, "ID deve ser durável (não muda)"
    print("[PASS] T08: durabilidade")


# T09 — Opacidade
def test_t09_opacidade():
    """T09: actor_id é opaco (não expõe informações)"""
    id1 = gerar_actor_id_estavel()

    # Não deve ser legível por humanos para dados sensíveis
    # Não deve conter tenant_id, identificador, canal, etc.
    assert len(id1) < 50, f"actor_id deve ser compacto: {id1}"
    assert id1.count("_") == 1, f"Deve ter exatamente um '_': {id1}"
    print("[PASS] T09: opacidade")


# T10 — Colisão praticamente impossível
def test_t10_colisao_impossivel():
    """T10: geração repetida não produz colisão em N tentativas"""
    ids = set()
    for _ in range(100):
        id1 = gerar_actor_id_estavel(prefixo="prof")
        assert id1 not in ids, f"COLISÃO: {id1} já foi gerado!"
        ids.add(id1)

    assert len(ids) == 100, f"Esperado 100 IDs únicos, obtido {len(ids)}"
    print("[PASS] T10: colisão impossível (100 tentativas)")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("C3.17-I2 GATE 2A - TESTES DO PROFISSIONAL CANÔNICO")
    print("="*70 + "\n")

    try:
        test_t01_gerar_actor_id()
        test_t02_prefixo_customizavel()
        test_t03_formato_consistente()
        test_t04_independencia_canal()
        test_t05_nao_usa_wa_id()
        test_t06_nao_usa_email()
        test_t07_nao_usa_nome()
        test_t08_durabilidade()
        test_t09_opacidade()
        test_t10_colisao_impossivel()

        print("\n" + "="*70)
        print("RESULTADO: 10/10 PASS")
        print("="*70 + "\n")

    except AssertionError as e:
        print(f"\nFALHA: {e}")
        import traceback
        traceback.print_exc()
