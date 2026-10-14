"""
Teste Simples: Validar que cenarios fixtures sao carregaveis
e que teste consegue ao menos acessar a router
"""

import pytest
import json
import sys
from pathlib import Path
from datetime import datetime

# Adicionar projeto ao path
projeto_dir = Path(__file__).parent.parent
sys.path.insert(0, str(projeto_dir))


class TestCenariosCarregamento:
    """Valida que cenarios P0 e P1 podem ser carregados"""

    def test_cenarios_p0_carregam(self):
        """Validar que cenarios_agendamento_real.json carrega corretamente"""
        fixture_path = Path(__file__).parent / "fixtures" / "cenarios_agendamento_real.json"

        assert fixture_path.exists(), f"Arquivo nao encontrado: {fixture_path}"

        with open(fixture_path, encoding='utf-8') as f:
            data = json.load(f)

        cenarios = data.get("cenarios", [])
        assert len(cenarios) > 0, "Nenhum cenario encontrado em P0"
        assert len(cenarios) == 24, f"Esperava 24 cenarios P0, encontrou {len(cenarios)}"

        print(f"[OK] P0: {len(cenarios)} cenarios carregados")
        for c in cenarios[:5]:
            print(f"   - {c.get('id')}: {c.get('frase')[:50]}...")

    def test_cenarios_p1_carregam(self):
        """Validar que cenarios_p1_onboarding_real.json carrega corretamente"""
        fixture_path = Path(__file__).parent / "fixtures" / "cenarios_p1_onboarding_real.json"

        assert fixture_path.exists(), f"Arquivo nao encontrado: {fixture_path}"

        with open(fixture_path, encoding='utf-8') as f:
            data = json.load(f)

        cenarios = data.get("cenarios", [])
        assert len(cenarios) > 0, "Nenhum cenario encontrado em P1"
        assert len(cenarios) == 22, f"Esperava 22 cenarios P1, encontrou {len(cenarios)}"

        print(f"[OK] P1: {len(cenarios)} cenarios carregados")
        for c in cenarios[:5]:
            print(f"   - {c.get('id')}: {c.get('frase')[:50]}...")

    def test_cenario_c01_existe(self):
        """Validar que cenario C01 (erro real) existe em P0"""
        fixture_path = Path(__file__).parent / "fixtures" / "cenarios_agendamento_real.json"

        with open(fixture_path, encoding='utf-8') as f:
            data = json.load(f)

        cenarios = data.get("cenarios", [])
        c01 = next((c for c in cenarios if c.get("id") == "C01"), None)

        assert c01 is not None, "Cenario C01 nao encontrado!"
        assert c01.get("frase") == "outra profissional", f"Frase C01 incorreta: {c01.get('frase')}"
        assert "confirmacao_pendente" in str(c01.get("contexto_previo", {})), \
            "C01 deve ter contexto_previo com confirmacao_pendente"

        print(f"[OK] C01 VALIDADO:")
        print(f"   Frase: {c01.get('frase')}")
        print(f"   Tipo esperado: {c01.get('esperado', {}).get('tipo')}")
        print(f"   Contexto: {c01.get('contexto_previo')}")

    def test_encontrar_servico_funciona(self):
        """Validar que funcao encontrar_servico_mais_proximo pode ser importada"""
        try:
            from services.normalizacao_service import encontrar_servico_mais_proximo
            print(f"[OK] encontrar_servico_mais_proximo importada com sucesso")
        except ImportError as e:
            pytest.fail(f"Nao conseguiu importar encontrar_servico_mais_proximo: {e}")

    def test_router_funciona(self):
        """Validar que funcao roteador_principal pode ser importada"""
        try:
            from router.principal_router import roteador_principal
            print(f"[OK] roteador_principal importada com sucesso")
        except ImportError as e:
            pytest.fail(f"Nao conseguiu importar roteador_principal: {e}")

    def test_cenarios_tem_campos_obrigatorios(self):
        """Validar que todos cenarios tem campos obrigatorios"""
        fixture_path = Path(__file__).parent / "fixtures" / "cenarios_agendamento_real.json"

        with open(fixture_path, encoding='utf-8') as f:
            data = json.load(f)

        cenarios = data.get("cenarios", [])

        campos_base = ["id", "categoria", "frase", "porque"]

        for cenario in cenarios:
            for campo in campos_base:
                assert campo in cenario, \
                    f"Cenario {cenario.get('id')} faltando campo '{campo}'"

            # Cenarios em etapas (A08) tem "esperado_final" ao invez de "esperado"
            if cenario.get("categoria") == "agendamento_em_etapas":
                assert "esperado_final" in cenario, \
                    f"Cenario {cenario.get('id')} (em etapas) faltando esperado_final"
            else:
                assert "esperado" in cenario, \
                    f"Cenario {cenario.get('id')} faltando esperado"

        print(f"[OK] Todos {len(cenarios)} cenarios tem campos validos")

    def test_resumo_cenarios(self):
        """Mostrar resumo dos cenarios por categoria"""
        fixture_path = Path(__file__).parent / "fixtures" / "cenarios_agendamento_real.json"

        with open(fixture_path, encoding='utf-8') as f:
            data = json.load(f)

        cenarios = data.get("cenarios", [])

        categorias = {}
        for c in cenarios:
            cat = c.get("categoria", "N/A")
            categorias[cat] = categorias.get(cat, 0) + 1

        print("\nRESUMO CENARIOS P0:")
        for cat, count in sorted(categorias.items()):
            print(f"  {cat}: {count}")

        fixture_path = Path(__file__).parent / "fixtures" / "cenarios_p1_onboarding_real.json"

        with open(fixture_path, encoding='utf-8') as f:
            data = json.load(f)

        cenarios = data.get("cenarios", [])

        categorias = {}
        for c in cenarios:
            cat = c.get("fase", "N/A")
            categorias[cat] = categorias.get(cat, 0) + 1

        print("\nRESUMO CENARIOS P1:")
        for cat, count in sorted(categorias.items()):
            print(f"  {cat}: {count}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
