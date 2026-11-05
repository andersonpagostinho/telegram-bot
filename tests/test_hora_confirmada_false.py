"""
TESTE: Verificar resposta quando hora_confirmada = False
"""

import pytest
from datetime import datetime, timedelta

try:
    from router.principal_router import montar_resposta_fallback
    IMPORTS_OK = True
except Exception as e:
    print(f"Import error: {e}")
    IMPORTS_OK = False


@pytest.mark.skipif(not IMPORTS_OK, reason="Failed to import")
class TestHoraConfirmadaFalse:

    def test_montar_resposta_com_hora_confirmada_false(self):
        """
        Testar: O que montar_resposta_fallback() retorna quando hora_confirmada = False?
        """
        print("\n" + "="*100)
        print("TESTE: O que acontece quando hora_confirmada = False?")
        print("="*100)

        amanha = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                  + timedelta(days=1))
        data_esperada = amanha.strftime("%Y-%m-%d")

        contexto = {
            "estado_fluxo": "aguardando_profissional",
            "hora_confirmada": False,  # <-- FALSE
            "servico": "corte feminino",
            "profissional_escolhido": "Bruna",
            "data_hora": f"{data_esperada}T15:00:00",
        }

        # Chamar com proximo_passo_real = "confirmar_ou_executar"
        resposta = montar_resposta_fallback(
            proximo_passo_real="confirmar_ou_executar",
            frase_data_legivel=f"para {data_esperada} as 15h",
            contexto=contexto
        )

        print(f"\nParametros:")
        print(f"  proximo_passo_real: 'confirmar_ou_executar'")
        print(f"  contexto.hora_confirmada: False")
        print(f"  contexto.servico: 'corte feminino'")
        print(f"  contexto.profissional_escolhido: 'Bruna'")
        print(f"  contexto.data_hora: '{data_esperada}T15:00:00'")

        print(f"\nResultado:")
        print(f"  {resposta!r}")

        if "Qual horario" in resposta or "Qual horário" in resposta or "horario" in resposta:
            print(f"\n🔴 A RESPOSTA PEDE HORARIO!")
            print(f"\nDIAGNOSTICO:")
            print(f"  Se o usuario recebe 'Qual horario?', entao:")
            print(f"  -> contexto['hora_confirmada'] estava False em linha 14238")
            print(f"  -> Ha um RESET de hora_confirmada para False entre linhas 1930-14238")
        else:
            print(f"\n✅ Nao pede horario")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
