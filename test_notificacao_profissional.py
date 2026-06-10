# -*- coding: utf-8 -*-
# test_notificacao_profissional.py
"""
Teste para validar criacao de notificacoes para cliente e profissional.
"""

import asyncio
from datetime import datetime
from pytz import timezone
from unittest.mock import AsyncMock, MagicMock, patch

FUSO_BR = timezone("America/Sao_Paulo")


class MockFirestore:
    """Mock simples de Firestore para testes."""

    def __init__(self):
        self.data = {}
        self.updates = []

    async def salvar_dado_em_path(self, path, dados):
        """Simula salvar em Firestore."""
        self.data[path] = dados
        self.updates.append({"path": path, "dados": dados})
        return True

    async def buscar_subcolecao(self, path):
        """Simula buscar subcoleção."""
        # Retorna todos os docs com esse path como prefixo
        resultado = {}
        for chave, valor in self.data.items():
            if chave.startswith(path):
                # Extrai ID do doc
                doc_id = chave.replace(f"{path}/", "").split("/")[0]
                if "/" not in chave.replace(f"{path}/", "", 1):
                    resultado[doc_id] = valor
        return resultado if resultado else None

    async def buscar_dado_em_path(self, path):
        """Simula buscar um documento."""
        return self.data.get(path)


async def test_criar_notificacoes_com_profissional():
    """
    Cenário: Evento com cliente Bruna e profissional Carla com telegram_id.
    Esperado: Criar 2 notificações (cliente + profissional).
    """
    print("\n" + "="*70)
    print("[TEST 1] Notificacoes: Cliente + Profissional com ID")
    print("="*70)

    # Importar a função (com mocks)
    with patch("services.notificacao_service.salvar_dado_em_path") as mock_salvar:
        with patch("services.notificacao_service.buscar_subcolecao") as mock_buscar_sub:

            mock_salvar.return_value = True
            mock_buscar_sub.return_value = None  # Sem duplicatas

            from services.notificacao_service import criar_notificacoes_evento_cliente_e_profissional

            # Executar
            resultado = await criar_notificacoes_evento_cliente_e_profissional(
                tenant_id="usuario123",
                evento_id="evento_001",
                cliente_id="cliente_bruna",
                cliente_nome="Bruna",
                profissional_nome="Carla",
                profissional_user_id="prof_carla",
                data="2026-06-10",
                hora_inicio="14:00",
                canal_cliente="telegram",
                canal_profissional="telegram",
                minutos_antes=30,
            )

            # Validar
            print("\n[RESULTADO]")
            print("  Cliente:")
            print("    Sucesso: {}".format(resultado["cliente"]["sucesso"]))
            print("    Notif ID: {}".format(resultado["cliente"]["notif_id"][:8] if resultado["cliente"]["notif_id"] else None))

            print("  Profissional:")
            print("    Sucesso: {}".format(resultado["profissional"]["sucesso"]))
            print("    Notif ID: {}".format(resultado["profissional"]["notif_id"][:8] if resultado["profissional"]["notif_id"] else None))

            # Verificar chamadas
            print("\n[CHAMADAS FIREBASE]")
            print("  Total de salvar_dado_em_path: {}".format(mock_salvar.call_count))

            if mock_salvar.call_count == 2:
                print("  [PASS] Ambas notificacoes foram salvas")

                # Verificar paths
                chamadas = mock_salvar.call_args_list
                for i, chamada in enumerate(chamadas):
                    path = chamada[0][0]
                    dados = chamada[0][1]
                    print("\n  Chamada {}:".format(i + 1))
                    print("    Path: {}".format(path))
                    print("    Papel: {}".format(dados.get("papel_destinatario")))
                    print("    Destinatario: {}".format(dados.get("destinatario_user_id")))
                    print("    Tipo: {}".format(dados.get("tipo")))
                    print("    Status: {}".format(dados.get("status")))

                return True
            else:
                print("  [FAIL] Esperava 2 chamadas, obteve {}".format(mock_salvar.call_count))
                return False


async def test_notificacao_profissional_sem_id():
    """
    Cenario: Evento com profissional SEM telegram_id.
    Esperado: Criar notificacao cliente, avisar sobre profissional sem ID.
    """
    print("\n" + "="*70)
    print("[TEST 2] Profissional SEM ID (aviso, nao quebra)")
    print("="*70)

    with patch("services.notificacao_service.salvar_dado_em_path") as mock_salvar:
        with patch("services.notificacao_service.buscar_subcolecao") as mock_buscar_sub:

            mock_salvar.return_value = True
            mock_buscar_sub.return_value = None

            from services.notificacao_service import criar_notificacoes_evento_cliente_e_profissional

            resultado = await criar_notificacoes_evento_cliente_e_profissional(
                tenant_id="usuario123",
                evento_id="evento_002",
                cliente_id="cliente_ana",
                cliente_nome="Ana",
                profissional_nome="Fernanda",
                profissional_user_id=None,  # SEM ID
                data="2026-06-11",
                hora_inicio="10:00",
            )

            print("\n[RESULTADO]")
            print("  Cliente:")
            print("    Sucesso: {}".format(resultado["cliente"]["sucesso"]))

            print("  Profissional:")
            print("    Sucesso: {}".format(resultado["profissional"]["sucesso"]))
            print("    Motivo: {}".format(resultado["profissional"]["motivo"]))

            # Validar
            if (resultado["cliente"]["sucesso"] and
                not resultado["profissional"]["sucesso"] and
                resultado["profissional"]["motivo"] == "profissional_sem_id"):
                print("\n  [PASS] Cliente notificado, profissional aviso apenas")

                if mock_salvar.call_count == 1:
                    print("  [PASS] Apenas 1 chamada Firestore (cliente)")
                    return True
                else:
                    print("  [FAIL] Esperava 1 chamada, obteve {}".format(mock_salvar.call_count))
                    return False
            else:
                print("  [FAIL] Estado invalido")
                return False


async def test_nao_duplica_notificacao():
    """
    Cenario: Executar 2x criar_notificacoes para mesmo evento.
    Esperado: Primeira vez cria, segunda vez nao duplica.
    """
    print("\n" + "="*70)
    print("[TEST 3] Nao duplica notificacao")
    print("="*70)

    # Primeira execucao: sem notificacoes existentes
    with patch("services.notificacao_service.salvar_dado_em_path") as mock_salvar_1:
        with patch("services.notificacao_service.buscar_subcolecao") as mock_buscar_1:

            mock_salvar_1.return_value = True
            mock_buscar_1.return_value = None  # Nada existe ainda

            from services.notificacao_service import criar_notificacoes_evento_cliente_e_profissional

            resultado1 = await criar_notificacoes_evento_cliente_e_profissional(
                tenant_id="usuario456",
                evento_id="evento_003",
                cliente_id="cliente_julia",
                cliente_nome="Julia",
                profissional_nome="Monica",
                profissional_user_id="prof_monica",
                data="2026-06-12",
                hora_inicio="15:30",
            )

            print("\n[PRIMEIRA EXECUCAO]")
            print("  Cliente: {}".format("CRIADA" if resultado1["cliente"]["sucesso"] else "FALHOU"))
            print("  Prof: {}".format("CRIADA" if resultado1["profissional"]["sucesso"] else "FALHOU"))
            chamadas_1 = mock_salvar_1.call_count
            print("  Chamadas Firestore: {}".format(chamadas_1))

    # Segunda execucao: simular que notificacoes ja existem
    with patch("services.notificacao_service.salvar_dado_em_path") as mock_salvar_2:
        with patch("services.notificacao_service.buscar_subcolecao") as mock_buscar_2:

            mock_salvar_2.return_value = True

            # Simular que ja existem notificacoes pendentes
            notificacoes_existentes = {
                "notif_1": {
                    "evento_id": "evento_003",
                    "destinatario_user_id": "cliente_julia",
                    "tipo": "lembrete_evento",
                    "avisado": False,
                },
                "notif_2": {
                    "evento_id": "evento_003",
                    "destinatario_user_id": "prof_monica",
                    "tipo": "lembrete_evento",
                    "avisado": False,
                }
            }
            mock_buscar_2.return_value = notificacoes_existentes

            resultado2 = await criar_notificacoes_evento_cliente_e_profissional(
                tenant_id="usuario456",
                evento_id="evento_003",
                cliente_id="cliente_julia",
                cliente_nome="Julia",
                profissional_nome="Monica",
                profissional_user_id="prof_monica",
                data="2026-06-12",
                hora_inicio="15:30",
            )

            print("\n[SEGUNDA EXECUCAO]")
            print("  Cliente: {}".format("CRIADA" if resultado2["cliente"]["sucesso"] else "PULA/DUPLICADA"))
            print("  Prof: {}".format("CRIADA" if resultado2["profissional"]["sucesso"] else "PULA/DUPLICADA"))
            print("  Motivo cliente: {}".format(resultado2["cliente"].get("motivo", "N/A")))
            print("  Motivo prof: {}".format(resultado2["profissional"].get("motivo", "N/A")))
            chamadas_2 = mock_salvar_2.call_count
            print("  Chamadas Firestore: {}".format(chamadas_2))

            # Validar
            if (chamadas_1 == 2 and chamadas_2 == 0 and
                not resultado2["cliente"]["sucesso"] and
                resultado2["cliente"]["motivo"] == "duplicada"):
                print("\n  [PASS] Primeira execucao criou 2, segunda pulou (duplicadas)")
                return True
            else:
                print("\n  [FAIL] Comportamento esperado nao foi atingido")
                return False


async def main():
    print("\n" + "="*70)
    print("TESTES: Notificacao de Profissional")
    print("="*70)

    resultado1 = await test_criar_notificacoes_com_profissional()
    resultado2 = await test_notificacao_profissional_sem_id()
    resultado3 = await test_nao_duplica_notificacao()

    print("\n" + "="*70)
    print("RESUMO:")
    print("  Teste 1 (Cliente + Prof): {}".format("PASSOU" if resultado1 else "FALHOU"))
    print("  Teste 2 (Prof sem ID): {}".format("PASSOU" if resultado2 else "FALHOU"))
    print("  Teste 3 (Nao duplica): {}".format("PASSOU" if resultado3 else "FALHOU"))
    print("="*70)

    if resultado1 and resultado2 and resultado3:
        print("\nTODOS OS TESTES PASSARAM!")
        return 0
    else:
        print("\nALGUNS TESTES FALHARAM!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
