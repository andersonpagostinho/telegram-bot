#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste simples: Patch P0 - Consulta Informativa Fora de Fluxo
"""

import sys

def test_router_patch():
    """Verifica se o patch foi aplicado ao router"""
    print("\n" + "=" * 80)
    print("TESTE 1: Router patch aplicado")
    print("=" * 80)

    with open(r"C:\Users\ANDERSON\iCloudDrive\Projeto Mercado Digital\Agente Bot\NeoEve - Empresarial\router\principal_router.py", "r", encoding="utf-8") as f:
        conteudo = f.read()

    # Verificacao 1
    print("\n[1] Bloco de consulta informativa adicionado...")
    if "P0 COMPLEMENTAR: Consultas informativas em contexto idle" in conteudo:
        print("    OK - Comentario encontrado")
    else:
        raise AssertionError("Bloco nao encontrado no router")

    # Verificacao 2
    print("[2] Logs CONSULTA_INFORMATIVA_IDLE presentes...")
    if "[CONSULTA_INFORMATIVA_IDLE]" in conteudo:
        print("    OK - Logs encontrados")
    else:
        raise AssertionError("Logs nao encontrados")

    # Verificacao 3
    print("[3] Ordem correcta (consulta antes de contexto_neutro)...")
    idx_consulta = conteudo.find("[CONSULTA_INFORMATIVA_IDLE]")
    idx_neutro = conteudo.find('motivo": "contexto_neutro')
    if idx_consulta > 0 and idx_neutro > 0 and idx_consulta < idx_neutro:
        print(f"    OK - Ordem correcta (pos {idx_consulta} < {idx_neutro})")
    else:
        raise AssertionError(f"Ordem incorreta. Consulta: {idx_consulta}, Neutro: {idx_neutro}")

    # Verificacao 4
    print("[4] Logica de deteccao consulta + agendamento...")
    if "tem_agendar and tem_temporal" in conteudo:
        print("    OK - Logica encontrada")
    else:
        raise AssertionError("Logica nao encontrada")

    print("\n[RESULTADO] Router patch - PASSOU")
    print("=" * 80)


def test_informacao_service_patch():
    """Verifica se o patch foi aplicado ao informacao_service"""
    print("\n" + "=" * 80)
    print("TESTE 2: Informacao Service patch aplicado")
    print("=" * 80)

    with open(r"C:\Users\ANDERSON\iCloudDrive\Projeto Mercado Digital\Agente Bot\NeoEve - Empresarial\services\informacao_service.py", "r", encoding="utf-8") as f:
        conteudo = f.read()

    # Verificacao 1
    print("\n[1] Comentario de endereco adicionado...")
    if "Endereco/Localizacao do negocio" in conteudo or "Endereco/Localizacao" in conteudo or "Endereço/Localização" in conteudo:
        print("    OK - Comentario encontrado")
    else:
        raise AssertionError("Comentario nao encontrado")

    # Verificacao 2
    print("[2] Palavras-chave de endereco...")
    palavras = [
        "qual o endereco", "onde fica", "como chegar", "localizacao"
    ]
    for palavra in palavras:
        if palavra in conteudo:
            print(f"    OK - '{palavra}' encontrada")
        else:
            raise AssertionError(f"Palavra-chave '{palavra}' nao encontrada")

    # Verificacao 3
    print("[3] Buscar endereco negocio...")
    if "buscar_endereco_negocio(dono_id)" in conteudo:
        print("    OK - Funcao buscar_endereco_negocio chamada com dono_id")
    else:
        raise AssertionError("buscar_endereco_negocio nao encontrada ou nao usa dono_id")

    # Verificacao 4
    print("[4] Resposta com endereco completo...")
    if "Nosso endereco" in conteudo or "Nosso endereço" in conteudo:
        print("    OK - Resposta formatada encontrada")
    else:
        raise AssertionError("Resposta nao encontrada")

    print("\n[RESULTADO] Informacao Service patch - PASSOU")
    print("=" * 80)


def main():
    print("\n")
    print("=" * 80)
    print("VALIDACAO - PATCH P0 COMPLEMENTAR")
    print("Consulta Informativa Fora de Fluxo")
    print("=" * 80)

    try:
        test_router_patch()
        test_informacao_service_patch()

        print("\n")
        print("=" * 80)
        print("RESULTADO FINAL: TODOS OS TESTES PASSARAM")
        print("Patch P0 Complementar aplicado com sucesso!")
        print("=" * 80)
        print()

    except Exception as e:
        print("\n")
        print("=" * 80)
        print("RESULTADO FINAL: TESTE FALHOU")
        print("=" * 80)
        print(f"\nErro: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
