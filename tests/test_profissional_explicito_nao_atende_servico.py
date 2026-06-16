#!/usr/bin/env python3
"""
Teste: Profissional Explícito Que Não Atende o Serviço

Cenário:
Usuário menciona um profissional específico que não atende o serviço solicitado.

Exemplo:
"Quero agendar corte com Carla amanhã às 10"
- Carla NÃO atende corte
- Bruna, Gloria, Joana atendem corte

Resultado esperado:
1. Sistema informa que Carla não atende corte
2. Lista profissionais que atendem corte
3. Mantém contexto (serviço, data, hora) no draft
4. Aguarda escolha de profissional válido
"""

import asyncio
import sys
import io
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

# Force UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, '.')

from handlers.acao_handler import tratar_mensagem_usuario


async def test_profissional_explicito_nao_atende_servico():
    """
    Teste: Profissional mencionado não atende o serviço solicitado.

    Dado:
    - Usuário = user_123
    - Tenant = tenant_456
    - Profissionais cadastrados:
      * Carla (atende: escova, hidratação)
      * Bruna (atende: corte, escova)
      * Gloria (atende: corte, coloração)
      * Joana (atende: corte, manicure)

    Quando:
    - Usuário diz: "Quero agendar corte com Carla amanhã às 10"

    Então:
    1. Sistema detecta "Carla" foi mencionada
    2. Sistema verifica que Carla não atende corte
    3. Resposta informa "Carla não atende corte"
    4. Resposta lista quem atende corte
    5. Draft preserva: serviço=corte, data, hora
    6. Estado continua aguardando_profissional
    """

    print("\n" + "="*80)
    print("TESTE: Profissional Explícito Que Não Atende Serviço")
    print("="*80)

    user_id = "user_123"
    tenant_id = "tenant_456"

    # Mock dados do tenant
    mock_profissionais = {
        "Carla": {
            "nome": "Carla",
            "servicos": ["escova", "hidratação"],
            "precos": {"escova": 40, "hidratação": 50},
        },
        "Bruna": {
            "nome": "Bruna",
            "servicos": ["corte", "escova"],
            "precos": {"corte": 60, "escova": 40},
        },
        "Gloria": {
            "nome": "Gloria",
            "servicos": ["corte", "coloração"],
            "precos": {"corte": 60, "coloração": 120},
        },
        "Joana": {
            "nome": "Joana",
            "servicos": ["corte", "manicure"],
            "precos": {"corte": 60, "manicure": 30},
        },
    }

    # Setup: Criar sessão simulando fluxo até estado aguardando_profissional
    amanha = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    sessao_inicial = {
        "estado": "aguardando_profissional",
        "servico": "corte",
        "data": amanha,
        "hora": "10:00",
        "duracao": 60,
        "disponiveis": ["Bruna", "Gloria", "Joana"],  # Carla NÃO está aqui
    }

    with patch("handlers.acao_handler.pegar_sessao") as mock_pegar_sessao, \
         patch("handlers.acao_handler.obter_id_dono") as mock_obter_dono, \
         patch("handlers.acao_handler.buscar_subcolecao") as mock_buscar_sub, \
         patch("handlers.acao_handler.buscar_profissionais_por_servico") as mock_buscar_prof_servico, \
         patch("handlers.acao_handler.criar_ou_atualizar_sessao") as mock_criar_sessao, \
         patch("handlers.acao_handler.sincronizar_contexto") as mock_sincronizar, \
         patch("handlers.acao_handler.interpretar_data_e_hora") as mock_interpretar_data:

        # Setup mocks
        mock_pegar_sessao.return_value = sessao_inicial
        mock_obter_dono.return_value = tenant_id
        mock_interpretar_data.return_value = None  # Não detectar data/hora para não interferir

        # Mock: buscar_subcolecao retorna profissionais quando chamado para Profissionais
        def mock_buscar_impl(path):
            if "Profissionais" in path:
                return mock_profissionais
            return {}

        mock_buscar_sub.side_effect = mock_buscar_impl

        # Mock: buscar_profissionais_por_servico retorna quem atende corte
        mock_buscar_prof_servico.return_value = {
            "Bruna": mock_profissionais["Bruna"],
            "Gloria": mock_profissionais["Gloria"],
            "Joana": mock_profissionais["Joana"],
        }

        # Executar: Usuário diz "Carla" (apenas o nome, sem data/hora)
        # Simulando que data/hora já foram coletadas nos passos anteriores
        mensagem = "Carla"
        print(f"\n📨 Entrada: {mensagem}")

        resposta = await tratar_mensagem_usuario(user_id, mensagem)

        print(f"\n📤 Resposta obtida:\n{resposta}\n")

        # Validações
        validacoes_ok = 0
        validacoes_total = 0

        def validar(condicao, descricao):
            nonlocal validacoes_ok, validacoes_total
            validacoes_total += 1
            if condicao:
                print(f"✅ {descricao}")
                validacoes_ok += 1
            else:
                print(f"❌ {descricao}")

        # ✅ Resposta contém o nome da profissional mencionada
        validar("Carla" in resposta, "Resposta menciona 'Carla'")

        # ✅ Resposta informa que não atende o serviço
        nao_atende = "não atende" in resposta.lower() or "nao atende" in resposta.lower()
        validar(nao_atende, "Resposta informa que Carla não atende o serviço")

        # ✅ Resposta menciona o serviço
        validar("corte" in resposta.lower(), "Resposta menciona 'corte'")

        # ✅ Resposta lista profissionais que atendem corte
        tem_opcao = ("Bruna" in resposta or "Gloria" in resposta or "Joana" in resposta)
        validar(tem_opcao, "Resposta lista profissionais que atendem corte")

        # ✅ Draft preserva serviço
        validar(sessao_inicial.get("servico") == "corte", "Draft preservou serviço")

        # ✅ Draft preserva data
        validar(sessao_inicial.get("data") == amanha, "Draft preservou data")

        # ✅ Draft preserva hora
        validar(sessao_inicial.get("hora") == "10:00", "Draft preservou hora")

        # ✅ Draft preserva disponiveis (para continuidade)
        validar(sessao_inicial.get("disponiveis") == ["Bruna", "Gloria", "Joana"],
                "Draft preservou lista de disponíveis")

        # ✅ Estado continua aguardando_profissional
        validar(sessao_inicial.get("estado") == "aguardando_profissional",
                "Estado continua aguardando_profissional")

        # ✅ Profissional não foi preenchido
        nao_preenchido = "profissional" not in sessao_inicial or sessao_inicial.get("profissional") is None
        validar(nao_preenchido, "Profissional não foi preenchido (aguardando escolha)")

        print(f"\n{'='*80}")
        print(f"Resultado: {validacoes_ok}/{validacoes_total} validações passaram")
        print(f"{'='*80}\n")

        return validacoes_ok == validacoes_total


async def main():
    try:
        resultado = await test_profissional_explicito_nao_atende_servico()
        if resultado:
            print("✅ TESTE PASSOU!")
            sys.exit(0)
        else:
            print("❌ TESTE FALHOU!")
            sys.exit(1)
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
