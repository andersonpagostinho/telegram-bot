# -*- coding: utf-8 -*-
"""
Testes Simples — Ponto 8628 (aguardando_data CASO C)
"""

import pytest
import re
import unidecode


def normalizar(texto: str) -> str:
    """Normaliza texto para comparação"""
    return unidecode.unidecode(
        re.sub(r"[^\w\s]", " ", str(texto).lower())
    ).strip()


def simular_ponto_8628(texto_usuario: str, servicos_disponiveis: list[str]):
    """Simular lógica do Ponto 8628 (após correção)"""
    servicos_catalogo_multiplos = set()

    for serv in servicos_disponiveis:
        servicos_catalogo_multiplos.add(normalizar(str(serv)))

    texto_norm_multiplos = normalizar(texto_usuario)
    servicos_visto = set()

    # 🔥 LÓGICA CORRIGIDA
    servicos_ord = sorted(servicos_catalogo_multiplos, key=len, reverse=True)
    matches_com_posicao = []

    for serv_cat in servicos_ord:
        match_exato = re.search(rf"\b{re.escape(serv_cat)}\b", texto_norm_multiplos)
        if match_exato:
            if serv_cat not in servicos_visto:
                matches_com_posicao.append((match_exato.start(), serv_cat))
                servicos_visto.add(serv_cat)
            continue

        serv_palavras = serv_cat.split()
        if serv_palavras:
            primeira_palavra = serv_palavras[0]
            match_prefixo = re.search(rf"\b{re.escape(primeira_palavra)}\b", texto_norm_multiplos)
            if match_prefixo and serv_cat not in servicos_visto:
                matches_com_posicao.append((match_prefixo.start(), serv_cat))
                servicos_visto.add(serv_cat)

    matches_com_posicao.sort(key=lambda x: x[0])
    return [serv for _, serv in matches_com_posicao]


class TestPonto8628:
    """Testes do Ponto 8628"""

    def test_manicure_pedicure_ordem(self):
        """Teste 1: "manicure e pedicure" → ['manicure', 'pedicure']"""
        texto = "manicure e pedicure"
        servicos = ["manicure", "pedicure"]
        resultado = simular_ponto_8628(texto, servicos)

        # Verificar que manicure vem antes de pedicure
        assert len(resultado) >= 2, f"Esperava 2 serviços, obteve {len(resultado)}"
        assert 'manicur' in resultado[0], f"Primeiro deveria ser manicure, obteve {resultado[0]}"
        assert 'pedicur' in resultado[1], f"Segundo deveria ser pedicure, obteve {resultado[1]}"
        print(f"✓ Teste 1 PASS: {resultado}")

    def test_pedicure_manicure_invertida(self):
        """Teste 2: "pedicure e manicure" → ['pedicure', 'manicure']"""
        texto = "pedicure e manicure"
        servicos = ["manicure", "pedicure"]
        resultado = simular_ponto_8628(texto, servicos)

        assert len(resultado) >= 2
        assert 'pedicur' in resultado[0], f"Primeiro deveria ser pedicure, obteve {resultado[0]}"
        assert 'manicur' in resultado[1], f"Segundo deveria ser manicure, obteve {resultado[1]}"
        print(f"✓ Teste 2 PASS: {resultado}")

    def test_sem_duplicata(self):
        """Teste 3: "manicure e manicure" → ['manicure']"""
        texto = "manicure e manicure"
        servicos = ["manicure", "pedicure"]
        resultado = simular_ponto_8628(texto, servicos)

        count_manicure = sum(1 for s in resultado if 'manicur' in s)
        assert count_manicure == 1, f"Manicure deveria aparecer 1x, encontrou {count_manicure}"
        print(f"✓ Teste 3 PASS: {resultado}")

    def test_com_contexto(self):
        """Teste 4: Ordem preservada com contexto"""
        texto = "Olá, preciso de manicure e pedicure para amanhã à tarde"
        servicos = ["manicure", "pedicure"]
        resultado = simular_ponto_8628(texto, servicos)

        assert len(resultado) >= 2
        assert 'manicur' in resultado[0]
        assert 'pedicur' in resultado[1]
        print(f"✓ Teste 4 PASS: {resultado}")

    def test_com_virgula(self):
        """Teste 5: Ordem com vírgula"""
        texto = "manicure, depois pedicure"
        servicos = ["manicure", "pedicure"]
        resultado = simular_ponto_8628(texto, servicos)

        assert 'manicur' in resultado[0]
        assert 'pedicur' in resultado[1]
        print(f"✓ Teste 5 PASS: {resultado}")

    def test_multiplos_servicos(self):
        """Teste 6: Múltiplos serviços"""
        texto = "escova, pedicure e manicure"
        servicos = ["manicure", "pedicure", "escova"]
        resultado = simular_ponto_8628(texto, servicos)

        assert 'escova' in resultado[0], f"Primeiro: {resultado}"
        assert 'pedicur' in resultado[1], f"Segundo: {resultado}"
        assert 'manicur' in resultado[2], f"Terceiro: {resultado}"
        print(f"✓ Teste 6 PASS: {resultado}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
