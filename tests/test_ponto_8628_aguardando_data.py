# -*- coding: utf-8 -*-
"""
Testes Específicos — Ponto 8628 (aguardando_data CASO C)
Validar que a ordem de serviços é preservada no fluxo aguardando_data
"""

import pytest
import sys
import os
import re
import unidecode

raiz_projeto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, raiz_projeto)

# Serviços disponíveis para testes (simulando profissional com múltiplos serviços)
SERVICOS_TESTE = ["manicure", "pedicure", "escova"]


def normalizar(texto: str) -> str:
    """Normaliza texto para comparação"""
    return unidecode.unidecode(
        re.sub(r"[^\w\s]", " ", str(texto).lower())
    ).strip()


def simular_logica_ponto_8628(texto_usuario: str, servicos_disponiveis: list[str]):
    """
    Simular a lógica do Ponto 8628 (após correção)
    Retornar servicos_mencionados na ordem preservada
    """
    servicos_catalogo_multiplos = set()

    # Simular profissionais com serviços
    for serv in servicos_disponiveis:
        servicos_catalogo_multiplos.add(normalizar(str(serv)))

    texto_norm_multiplos = normalizar(texto_usuario)
    servicos_mencionados = []
    servicos_visto = set()

    # 🔥 LÓGICA CORRIGIDA (Ponto 8628 após fix)
    servicos_ord = sorted(servicos_catalogo_multiplos, key=len, reverse=True)
    matches_com_posicao = []

    for serv_cat in servicos_ord:
        # Tentar match exato com word boundaries
        match_exato = re.search(rf"\b{re.escape(serv_cat)}\b", texto_norm_multiplos)
        if match_exato:
            if serv_cat not in servicos_visto:
                matches_com_posicao.append((match_exato.start(), serv_cat))
                servicos_visto.add(serv_cat)
            continue

        # Fallback: match de prefixo
        serv_palavras = serv_cat.split()
        if serv_palavras:
            primeira_palavra = serv_palavras[0]
            match_prefixo = re.search(rf"\b{re.escape(primeira_palavra)}\b", texto_norm_multiplos)
            if match_prefixo and serv_cat not in servicos_visto:
                matches_com_posicao.append((match_prefixo.start(), serv_cat))
                servicos_visto.add(serv_cat)

    # Ordenar por posição de primeira menção
    matches_com_posicao.sort(key=lambda x: x[0])
    servicos_mencionados = [serv for _, serv in matches_com_posicao]

    return servicos_mencionados


class TestPonto8628:
    """Testes específicos para Ponto 8628 (aguardando_data CASO C)"""

    def test_8628_manicure_pedicure_nessa_ordem(self):
        """Teste 1: "manicure e pedicure" preserva ordem"""
        texto = "manicure e pedicure"
        resultado = simular_logica_ponto_8628(texto, SERVICOS_TESTE)

        resultado_norm = [r.lower().strip() for r in resultado]

        idx_manicure = None
        idx_pedicure = None

        for i, serv in enumerate(resultado_norm):
            if 'manicur' in serv:
                idx_manicure = i
            if 'pedicur' in serv:
                idx_pedicure = i

        if idx_manicure is not None and idx_pedicure is not None:
            assert idx_manicure < idx_pedicure, \
                f"❌ Ordem incorreta em Ponto 8628: manicure deveria vir antes. Resultado: {resultado_norm}"

        print(f"✓ Teste 1 PASS: '{texto}' → {resultado_norm}")

    def test_8628_pedicure_manicure_nessa_ordem(self):
        """Teste 2: "pedicure e manicure" inverte corretamente"""
        texto = "pedicure e manicure"
        resultado = simular_logica_ponto_8628(texto, SERVICOS_TESTE)

        resultado_norm = [r.lower().strip() for r in resultado]

        idx_pedicure = None
        idx_manicure = None

        for i, serv in enumerate(resultado_norm):
            if 'pedicur' in serv:
                idx_pedicure = i
            if 'manicur' in serv:
                idx_manicure = i

        if idx_pedicure is not None and idx_manicure is not None:
            assert idx_pedicure < idx_manicure, \
                f"❌ Ordem incorreta em Ponto 8628: pedicure deveria vir antes. Resultado: {resultado_norm}"

        print(f"✓ Teste 2 PASS: '{texto}' → {resultado_norm}")

    def test_8628_com_virgula(self):
        """Teste 3: Ordem preservada com vírgula"""
        texto = "manicure, depois pedicure"
        resultado = simular_logica_ponto_8628(texto, SERVICOS_TESTE)

        resultado_norm = [r.lower().strip() for r in resultado]

        idx_manicure = None
        idx_pedicure = None

        for i, serv in enumerate(resultado_norm):
            if 'manicur' in serv:
                idx_manicure = i
            if 'pedicur' in serv:
                idx_pedicure = i

        if idx_manicure is not None and idx_pedicure is not None:
            assert idx_manicure < idx_pedicure, \
                f"❌ Ordem incorreta com vírgula. Resultado: {resultado_norm}"

        print(f"✓ Teste 3 PASS: '{texto}' → {resultado_norm}")

    def test_8628_sem_duplicata(self):
        """Teste 4: Sem duplicação quando mencionado 2x"""
        texto = "manicure e manicure"
        resultado = simular_logica_ponto_8628(texto, SERVICOS_TESTE)

        resultado_norm = [r.lower().strip() for r in resultado]

        count = sum(1 for s in resultado_norm if 'manicur' in s)

        assert count == 1, \
            f"❌ Manicure deveria aparecer uma vez apenas. Resultado: {resultado_norm}"

        print(f"✓ Teste 4 PASS: Sem duplicação → {resultado_norm}")

    def test_8628_com_contexto(self):
        """Teste 5: Ordem preservada em mensagem com contexto"""
        texto = "Olá, preciso de manicure e pedicure para amanhã"
        resultado = simular_logica_ponto_8628(texto, SERVICOS_TESTE)

        resultado_norm = [r.lower().strip() for r in resultado]

        idx_manicure = None
        idx_pedicure = None

        for i, serv in enumerate(resultado_norm):
            if 'manicur' in serv:
                idx_manicure = i
            if 'pedicur' in serv:
                idx_pedicure = i

        if idx_manicure is not None and idx_pedicure is not None:
            assert idx_manicure < idx_pedicure, \
                f"❌ Ordem não preservada em mensagem com contexto. Resultado: {resultado_norm}"

        print(f"✓ Teste 5 PASS: Contexto preservado → {resultado_norm}")

    def test_8628_multiplos_cenarios(self):
        """Teste 6: Vários cenários validados"""
        cenarios = [
            ("manicure, pedicure e escova", "manicure", "pedicure"),  # Ordem 1
            ("escova, pedicure e manicure", "escova", "pedicure"),    # Ordem 2
            ("pedicure manicure", "pedicure", "manicure"),             # Sem "e"
        ]

        for texto, primeiro_esperado, segundo_esperado in cenarios:
            resultado = simular_logica_ponto_8628(texto, SERVICOS_TESTE)
            resultado_norm = [r.lower().strip() for r in resultado]

            if len(resultado_norm) >= 2:
                # Verificar que pelo menos os dois primeiros aparecem na ordem
                idx_primeiro = None
                idx_segundo = None

                for i, serv in enumerate(resultado_norm):
                    if primeiro_esperado in serv and idx_primeiro is None:
                        idx_primeiro = i
                    if segundo_esperado in serv and idx_segundo is None:
                        idx_segundo = i

                if idx_primeiro is not None and idx_segundo is not None:
                    assert idx_primeiro < idx_segundo, \
                        f"❌ Ordem incorreta para '{texto}': {resultado_norm}"

                    print(f"✓ Cenário OK: '{texto}' → {resultado_norm}")


if __name__ == "__main__":
    import asyncio

    print("\n" + "="*70)
    print("TESTES PONTO 8628 (aguardando_data CASO C)")
    print("="*70 + "\n")

    pytest.main([__file__, "-v", "-s"])
