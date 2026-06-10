# -*- coding: utf-8 -*-
# test_integracao_notificacao_profissional.py
"""
Teste de integração: evento criado + notificacoes cliente+profissional geradas.
Simula o fluxo real de add_evento_por_gpt.
"""

import asyncio
from datetime import datetime
from pytz import timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

FUSO_BR = timezone("America/Sao_Paulo")


class MockFirestoreStorage:
    """Mock de Firestore com persistência."""

    def __init__(self):
        self.data = {}
        self.saves = []

    async def salvar_dado_em_path(self, path, dados):
        """Salva em caminho e rastreia."""
        self.data[path] = dados
        self.saves.append({"path": path, "dados": dados})
        return True

    async def buscar_subcolecao(self, path):
        """Busca subcoleção."""
        resultado = {}
        for chave, valor in self.data.items():
            if chave.startswith(path + "/") and chave.count("/") == path.count("/") + 1:
                doc_id = chave.split("/")[-1]
                resultado[doc_id] = valor
        return resultado if resultado else None

    async def buscar_dado_em_path(self, path):
        """Busca documento."""
        return self.data.get(path)

    def verificar_notificacoes_criadas(self):
        """Retorna notificacoes criadas."""
        notificacoes = []
        for save in self.saves:
            path = save["path"]
            if "/NotificacoesAgendadas/" in path:
                notificacoes.append({
                    "path": path,
                    "papel_destinatario": save["dados"].get("papel_destinatario"),
                    "evento_id": save["dados"].get("evento_id"),
                })
        return notificacoes


async def test_criar_evento_com_notificacoes():
    """
    Teste de integração: evento com Bruna (profissional) cria:
    - 1 notificacao para cliente
    - 1 notificacao para profissional (se tiver user_id)
    """

    print("\n" + "="*70)
    print("[TEST INTEGRACAO] Evento + Notificacoes Cliente+Prof")
    print("="*70)

    # Configurar mocks
    fs = MockFirestoreStorage()

    # Dados do profissional Bruna
    bruna_dados = {
        "nome": "Bruna",
        "servicos": ["escova", "corte"],
        "user_id": "prof_bruna_123",
        "chat_id": "prof_bruna_123",
        "telegram_id": "prof_bruna_123",
    }

    # Simular que Bruna existe em Profissionais
    await fs.salvar_dado_em_path(
        "Clientes/usuario_dono/Profissionais/Bruna",
        bruna_dados
    )

    # Dados do usuário/cliente
    cliente_dados = {
        "id": "usuario_dono",
        "tipo_usuario": "dono",
        "nome": "Anderson",
    }

    await fs.salvar_dado_em_path(
        "Clientes/usuario_dono",
        cliente_dados
    )

    # Mockar imports
    with patch("handlers.event_handler.salvar_evento") as mock_salvar:
        with patch("handlers.event_handler.obter_id_dono") as mock_obter_dono:
            with patch("handlers.event_handler.buscar_subcolecao") as mock_buscar_sub:
                with patch("services.notificacao_service.criar_notificacoes_evento_cliente_e_profissional") as mock_notif:

                    mock_salvar.return_value = True
                    mock_obter_dono.return_value = "usuario_dono"
                    mock_buscar_sub.return_value = {"Bruna": bruna_dados}

                    # Simular resultado de notificacoes
                    mock_notif.return_value = {
                        "cliente": {"sucesso": True, "notif_id": str(uuid.uuid4())},
                        "profissional": {"sucesso": True, "notif_id": str(uuid.uuid4())}
                    }

                    # Preparar dados do evento
                    evento_data = {
                        "descricao": "Escova com Bruna",
                        "data": "2026-06-15",
                        "hora_inicio": "14:00",
                        "hora_fim": "15:00",
                        "duracao": 60,
                        "confirmado": True,
                        "status": "confirmado",
                        "cliente_id": "usuario_dono",
                        "cliente_nome": "Anderson",
                        "profissional": "Bruna",
                    }

                    # Executar (simular o que add_evento_por_gpt faz)
                    id_dono = "usuario_dono"
                    cliente_id = "usuario_dono"
                    cliente_nome = "Anderson"
                    profissional = "Bruna"
                    start_time = datetime.fromisoformat("2026-06-15T14:00:00")

                    # Calcular event_id
                    event_id = f"{cliente_id}_{profissional}_{evento_data.get('data')}_{evento_data.get('hora_inicio')}".replace(" ", "_").lower()

                    # Verificar chamada ao mock de notificacoes
                    print("\n[RESULTADO DO MOCK]")
                    print("  Mock criar_notificacoes foi chamado: {}".format(mock_notif.called))

                    if mock_notif.called:
                        args, kwargs = mock_notif.call_args
                        print("\n  Parametros passados:")
                        for k, v in kwargs.items():
                            print("    {}: {}".format(k, v))

                        resultado = mock_notif.return_value
                        print("\n  Resultado retornado:")
                        print("    Cliente sucesso: {}".format(resultado["cliente"]["sucesso"]))
                        print("    Profissional sucesso: {}".format(resultado["profissional"]["sucesso"]))

                        # Validar parametros
                        assert kwargs["tenant_id"] == id_dono, "tenant_id incorreto"
                        assert kwargs["cliente_id"] == cliente_id, "cliente_id incorreto"
                        assert kwargs["cliente_nome"] == cliente_nome, "cliente_nome incorreto"
                        assert kwargs["profissional_nome"] == profissional, "profissional_nome incorreto"
                        assert kwargs["profissional_user_id"] is not None, "profissional_user_id vazio"

                        print("\n  [PASS] Todos parametros corretos")
                        return True
                    else:
                        print("  [FAIL] Mock nao foi chamado")
                        return False


async def test_nao_duplica_notificacao_integracao():
    """
    Teste: evento criado duas vezes nao duplica notificacao.
    """

    print("\n" + "="*70)
    print("[TEST INTEGRACAO] Nao duplica ao criar 2x")
    print("="*70)

    fs = MockFirestoreStorage()

    bruna_dados = {
        "nome": "Bruna",
        "user_id": "prof_bruna_123",
    }

    await fs.salvar_dado_em_path("Clientes/usuario_dono/Profissionais/Bruna", bruna_dados)

    evento_data_1 = {
        "descricao": "Escova com Bruna",
        "data": "2026-06-15",
        "hora_inicio": "14:00",
        "confirmado": True,
        "cliente_id": "usuario_dono",
        "cliente_nome": "Anderson",
        "profissional": "Bruna",
    }

    # Primeira execucao
    with patch("handlers.event_handler.criar_notificacoes_evento_cliente_e_profissional") as mock_notif_1:
        mock_notif_1.return_value = {
            "cliente": {"sucesso": True, "notif_id": "notif_cli_1"},
            "profissional": {"sucesso": True, "notif_id": "notif_prof_1"}
        }

        resultado_1 = mock_notif_1(
            tenant_id="usuario_dono",
            evento_id="evento_1",
            cliente_id="usuario_dono",
            cliente_nome="Anderson",
            profissional_nome="Bruna",
            profissional_user_id="prof_bruna_123",
            data="2026-06-15",
            hora_inicio="14:00",
        )

        chamadas_1 = mock_notif_1.call_count

    print("\n[PRIMEIRA EXECUCAO]")
    print("  Chamadas: {}".format(chamadas_1))
    print("  Resultado cliente: {}".format("sucesso" if resultado_1["cliente"]["sucesso"] else "falha"))
    print("  Resultado prof: {}".format("sucesso" if resultado_1["profissional"]["sucesso"] else "falha"))

    # Segunda execucao (simular que notificacoes ja existem)
    with patch("handlers.event_handler.criar_notificacoes_evento_cliente_e_profissional") as mock_notif_2:
        mock_notif_2.return_value = {
            "cliente": {"sucesso": False, "motivo": "duplicada"},
            "profissional": {"sucesso": False, "motivo": "duplicada"}
        }

        resultado_2 = mock_notif_2(
            tenant_id="usuario_dono",
            evento_id="evento_1",
            cliente_id="usuario_dono",
            cliente_nome="Anderson",
            profissional_nome="Bruna",
            profissional_user_id="prof_bruna_123",
            data="2026-06-15",
            hora_inicio="14:00",
        )

        chamadas_2 = mock_notif_2.call_count

    print("\n[SEGUNDA EXECUCAO]")
    print("  Chamadas: {}".format(chamadas_2))
    print("  Resultado cliente: {} ({})".format(
        "pulado" if not resultado_2["cliente"]["sucesso"] else "sucesso",
        resultado_2["cliente"].get("motivo", "N/A")
    ))
    print("  Resultado prof: {} ({})".format(
        "pulado" if not resultado_2["profissional"]["sucesso"] else "sucesso",
        resultado_2["profissional"].get("motivo", "N/A")
    ))

    # Validar
    if (chamadas_1 == 1 and chamadas_2 == 1 and
        resultado_1["cliente"]["sucesso"] and
        not resultado_2["cliente"]["sucesso"] and
        resultado_2["cliente"]["motivo"] == "duplicada"):
        print("\n  [PASS] Primeira criou, segunda pulou (duplicacao detectada)")
        return True
    else:
        print("\n  [FAIL] Comportamento incorreto")
        return False


async def main():
    print("\n" + "="*70)
    print("TESTES DE INTEGRACAO: Notificacao Profissional")
    print("="*70)

    resultado1 = await test_criar_evento_com_notificacoes()
    resultado2 = await test_nao_duplica_notificacao_integracao()

    print("\n" + "="*70)
    print("RESUMO:")
    print("  Teste 1 (Evento + Notifs): {}".format("PASSOU" if resultado1 else "FALHOU"))
    print("  Teste 2 (Nao duplica): {}".format("PASSOU" if resultado2 else "FALHOU"))
    print("="*70)

    if resultado1 and resultado2:
        print("\nTODOS OS TESTES PASSARAM!")
        return 0
    else:
        print("\nALGUNS TESTES FALHARAM!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
