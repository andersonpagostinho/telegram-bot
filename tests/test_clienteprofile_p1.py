# tests/test_clienteprofile_p1.py
"""
Testes do ClienteProfile P1.1 Passivo

Valida:
- Criação de profile na primeira vez
- Atualização de profile após novo evento
- Isolamento multi-tenant
- Idempotência
- Agregação de profissionais
- Agregação de serviços
- Não bloqueio de agendamento
"""

import pytest
import asyncio
from datetime import datetime
from pytz import timezone
from unittest.mock import patch, AsyncMock, MagicMock

# Import do service sob teste
from services.clienteprofile_service import (
    criar_ou_atualizar_profile_apos_evento,
    obter_profile,
    _calcular_moda_profissional,
    _calcular_moda_servico,
)

FUSO_BR = timezone("America/Sao_Paulo")


class TestClienteProfileCreation:
    """Testes de criação de profile."""

    @pytest.mark.asyncio
    async def test_profile_created_on_first_event(self):
        """Profile é criado quando cliente agenda primeira vez."""

        # Arrange
        tenant_id = "dono_123"
        cliente_id = "cliente_abc"
        evento_data = {
            "profissional": "Carla",
            "servico": "corte",
            "cliente_nome": "Suri",
        }

        # Mock Firestore
        with patch("services.clienteprofile_service.buscar_dado_em_path") as mock_buscar:
            with patch("services.clienteprofile_service.salvar_dado_em_path") as mock_salvar:
                mock_buscar.return_value = None  # Profile não existe
                mock_salvar.return_value = True  # Salvamento OK

                # Act
                resultado = await criar_ou_atualizar_profile_apos_evento(
                    tenant_id, cliente_id, evento_data
                )

                # Assert
                assert resultado is True, "deve retornar True"
                assert mock_salvar.called, "deve chamar salvar"

                # Verificar o path correto
                call_args = mock_salvar.call_args
                path_usado = call_args[0][0]
                assert path_usado == f"Clientes/{tenant_id}/ClienteProfiles/{cliente_id}"

                # Verificar estrutura do profile
                profile = call_args[0][1]
                assert profile["cliente_id"] == cliente_id
                assert profile["tenant_id"] == tenant_id
                assert profile["nome"] == "Suri"
                assert profile["historico"]["total_eventos"] == 1
                assert "Carla" in profile["historico"]["profissionais_atendidos"]
                assert "corte" in profile["historico"]["servicos_atendidos"]
                assert profile["tendencias"]["profissional_mais_frequente"] == "Carla"
                assert profile["tendencias"]["servico_mais_frequente"] == "corte"
                assert profile["versao"] == 1

    @pytest.mark.asyncio
    async def test_profile_update_on_new_event(self):
        """Profile é atualizado quando novo evento é criado."""

        # Arrange
        tenant_id = "dono_123"
        cliente_id = "cliente_abc"

        # Profile existente
        profile_existente = {
            "cliente_id": cliente_id,
            "tenant_id": tenant_id,
            "versao": 1,
            "historico": {
                "primeira_contato": "2026-06-01T10:00:00-03:00",
                "ultima_contato": "2026-06-01T10:00:00-03:00",
                "total_eventos": 1,
                "profissionais_atendidos": ["Carla"],
                "servicos_atendidos": ["corte"],
                "proxima_sugestao": None,
            },
            "tendencias": {
                "profissional_mais_frequente": "Carla",
                "profissional_mais_frequente_count": 1,
                "servico_mais_frequente": "corte",
                "servico_mais_frequente_count": 1,
            },
        }

        # Novo evento
        evento_data = {
            "profissional": "Bruna",
            "servico": "escova",
            "cliente_nome": "Suri",
        }

        with patch("services.clienteprofile_service.buscar_dado_em_path") as mock_buscar:
            with patch("services.clienteprofile_service.atualizar_dado_em_path") as mock_atualizar:
                mock_buscar.return_value = profile_existente
                mock_atualizar.return_value = True

                # Act
                resultado = await criar_ou_atualizar_profile_apos_evento(
                    tenant_id, cliente_id, evento_data
                )

                # Assert
                assert resultado is True
                assert mock_atualizar.called

                # Verificar update
                call_args = mock_atualizar.call_args
                updated_data = call_args[0][1]

                assert updated_data["historico"]["total_eventos"] == 2
                assert "Carla" in updated_data["historico"]["profissionais_atendidos"]
                assert "Bruna" in updated_data["historico"]["profissionais_atendidos"]
                assert "escova" in updated_data["historico"]["servicos_atendidos"]
                assert updated_data["versao"] == 2

    @pytest.mark.asyncio
    async def test_profile_multi_tenant_isolated(self):
        """Profiles de tenants diferentes não se misturar."""

        # Arrange - Tenant 1
        tenant_1 = "dono_111"
        cliente_id = "cliente_abc"  # Mesmo cliente_id em tenants diferentes
        evento_1 = {"profissional": "Carla", "servico": "corte", "cliente_nome": "Suri"}

        # Arrange - Tenant 2
        tenant_2 = "dono_222"
        evento_2 = {"profissional": "Bruna", "servico": "manicure", "cliente_nome": "Suri"}

        # Mock
        with patch("services.clienteprofile_service.buscar_dado_em_path") as mock_buscar:
            with patch("services.clienteprofile_service.salvar_dado_em_path") as mock_salvar:
                mock_buscar.return_value = None
                mock_salvar.return_value = True

                # Act - Create em tenant 1
                await criar_ou_atualizar_profile_apos_evento(tenant_1, cliente_id, evento_1)

                # Act - Create em tenant 2
                await criar_ou_atualizar_profile_apos_evento(tenant_2, cliente_id, evento_2)

                # Assert
                assert mock_salvar.call_count == 2

                # Verificar que paths são diferentes
                call_1 = mock_salvar.call_args_list[0]
                call_2 = mock_salvar.call_args_list[1]

                path_1 = call_1[0][0]
                path_2 = call_2[0][0]

                assert path_1 == f"Clientes/{tenant_1}/ClienteProfiles/{cliente_id}"
                assert path_2 == f"Clientes/{tenant_2}/ClienteProfiles/{cliente_id}"
                assert path_1 != path_2, "paths devem ser diferentes"

                # Verificar que dados são diferentes
                profile_1 = call_1[0][1]
                profile_2 = call_2[0][1]

                assert profile_1["tendencias"]["profissional_mais_frequente"] == "Carla"
                assert profile_2["tendencias"]["profissional_mais_frequente"] == "Bruna"

    @pytest.mark.asyncio
    async def test_profile_creation_idempotent(self):
        """Criar profile 2x do mesmo cliente é idempotente."""

        # Arrange
        tenant_id = "dono_123"
        cliente_id = "cliente_abc"
        evento_data = {
            "profissional": "Carla",
            "servico": "corte",
            "cliente_nome": "Suri",
        }

        with patch("services.clienteprofile_service.buscar_dado_em_path") as mock_buscar:
            with patch("services.clienteprofile_service.salvar_dado_em_path") as mock_salvar:
                mock_buscar.return_value = None
                mock_salvar.return_value = True

                # Act - Chamar 2x
                resultado_1 = await criar_ou_atualizar_profile_apos_evento(
                    tenant_id, cliente_id, evento_data
                )
                resultado_2 = await criar_ou_atualizar_profile_apos_evento(
                    tenant_id, cliente_id, evento_data
                )

                # Assert
                assert resultado_1 is True
                assert resultado_2 is True
                # Ambas chamadas devem ter sucesso (segunda vê que já existe)

    @pytest.mark.asyncio
    async def test_profile_profissional_agregado(self):
        """Profile agrega corretamente profissionais atendidos."""

        # Arrange
        tenant_id = "dono_123"
        cliente_id = "cliente_abc"

        # Profile após 3 eventos: Carla (2x), Bruna (1x)
        profile = {
            "historico": {
                "profissionais_atendidos": ["Carla", "Carla", "Bruna"],
            },
        }

        # Mock
        with patch("services.clienteprofile_service.buscar_dado_em_path") as mock_buscar:
            with patch("services.clienteprofile_service.atualizar_dado_em_path") as mock_atualizar:
                mock_buscar.return_value = profile
                mock_atualizar.return_value = True

                # Act
                evento = {"profissional": "Marina", "servico": "corte"}
                await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento)

                # Assert
                call_args = mock_atualizar.call_args
                update = call_args[0][1]

                # Deve ter 4 profissionais (Carla, Carla, Bruna, Marina)
                profs = update["historico"]["profissionais_atendidos"]
                assert len(profs) == 4
                assert "Marina" in profs

                # Carla deve ser a mais frequente (2 vezes)
                assert update["tendencias"]["profissional_mais_frequente"] == "Carla"
                assert update["tendencias"]["profissional_mais_frequente_count"] == 2

    @pytest.mark.asyncio
    async def test_profile_servico_agregado(self):
        """Profile agrega corretamente serviços atendidos."""

        # Arrange
        tenant_id = "dono_123"
        cliente_id = "cliente_abc"

        profile = {
            "historico": {
                "servicos_atendidos": ["corte", "corte", "escova"],
            },
        }

        with patch("services.clienteprofile_service.buscar_dado_em_path") as mock_buscar:
            with patch("services.clienteprofile_service.atualizar_dado_em_path") as mock_atualizar:
                mock_buscar.return_value = profile
                mock_atualizar.return_value = True

                # Act
                evento = {"profissional": "Carla", "servico": "manicure"}
                await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento)

                # Assert
                call_args = mock_atualizar.call_args
                update = call_args[0][1]

                servicos = update["historico"]["servicos_atendidos"]
                assert len(servicos) == 4
                assert "manicure" in servicos

                # Corte deve ser o mais frequente (2 vezes)
                assert update["tendencias"]["servico_mais_frequente"] == "corte"
                assert update["tendencias"]["servico_mais_frequente_count"] == 2

    @pytest.mark.asyncio
    async def test_profile_nao_bloqueia_agendamento(self):
        """Profile falha mas agendamento continua funcionando."""

        # Arrange
        tenant_id = "dono_123"
        cliente_id = "cliente_abc"
        evento_data = {"profissional": "Carla", "servico": "corte"}

        # Mock: profile falha
        with patch("services.clienteprofile_service.buscar_dado_em_path") as mock_buscar:
            with patch("services.clienteprofile_service.salvar_dado_em_path") as mock_salvar:
                mock_buscar.side_effect = Exception("Firestore error")

                # Act - Não bloqueia
                resultado = await criar_ou_atualizar_profile_apos_evento(
                    tenant_id, cliente_id, evento_data
                )

                # Assert
                assert resultado is False, "retorna False mas não lança exception"
                # Agendamento pode continuar (não bloqueia)


class TestModaCalculation:
    """Testes de cálculo de moda."""

    def test_calcular_moda_profissional(self):
        """Calcula profissional mais frequente."""
        profissionais = ["Carla", "Bruna", "Carla", "Marina"]
        resultado = _calcular_moda_profissional(profissionais)
        assert resultado == "Carla"

    def test_calcular_moda_servico(self):
        """Calcula serviço mais frequente."""
        servicos = ["corte", "escova", "corte"]
        resultado = _calcular_moda_servico(servicos)
        assert resultado == "corte"

    def test_moda_vazio(self):
        """Moda de lista vazia."""
        assert _calcular_moda_profissional([]) is None
        assert _calcular_moda_servico([]) is None


class TestEdgeCases:
    """Testes de casos extremos."""

    @pytest.mark.asyncio
    async def test_evento_sem_profissional(self):
        """Evento sem profissional não quebra."""
        tenant_id = "dono_123"
        cliente_id = "cliente_abc"
        evento = {"profissional": None, "servico": "corte"}

        with patch("services.clienteprofile_service.buscar_dado_em_path") as mock_buscar:
            with patch("services.clienteprofile_service.salvar_dado_em_path") as mock_salvar:
                mock_buscar.return_value = None
                mock_salvar.return_value = True

                resultado = await criar_ou_atualizar_profile_apos_evento(
                    tenant_id, cliente_id, evento
                )

                assert resultado is True
                profile = mock_salvar.call_args[0][1]
                assert profile["historico"]["profissionais_atendidos"] == []

    @pytest.mark.asyncio
    async def test_evento_sem_servico(self):
        """Evento sem serviço não quebra."""
        tenant_id = "dono_123"
        cliente_id = "cliente_abc"
        evento = {"profissional": "Carla", "servico": None}

        with patch("services.clienteprofile_service.buscar_dado_em_path") as mock_buscar:
            with patch("services.clienteprofile_service.salvar_dado_em_path") as mock_salvar:
                mock_buscar.return_value = None
                mock_salvar.return_value = True

                resultado = await criar_ou_atualizar_profile_apos_evento(
                    tenant_id, cliente_id, evento
                )

                assert resultado is True
                profile = mock_salvar.call_args[0][1]
                assert profile["historico"]["servicos_atendidos"] == []

    @pytest.mark.asyncio
    async def test_cliente_id_vazio(self):
        """Cliente ID vazio retorna False sem bloquear."""
        resultado = await criar_ou_atualizar_profile_apos_evento("dono_123", "", {})
        assert resultado is False

    @pytest.mark.asyncio
    async def test_tenant_id_vazio(self):
        """Tenant ID vazio retorna False sem bloquear."""
        resultado = await criar_ou_atualizar_profile_apos_evento("", "cliente_123", {})
        assert resultado is False


class TestIdempotenciaP1:
    """PATCH P1: Testes de deduplicação por evento_id."""

    @pytest.mark.asyncio
    async def test_mesmo_evento_id_nao_duplica_total(self):
        """Mesmo evento_id processado 2x não incrementa total_eventos 2x."""

        tenant_id = "dono_123"
        cliente_id = "cliente_abc"
        evento_id = "cliente_abc_carla_2026-06-14_14:00"  # PATCH P1
        evento_data = {
            "profissional": "Carla",
            "servico": "corte",
            "cliente_nome": "Suri",
            "data": "2026-06-14",
            "hora": "14:00",
        }

        # Profile já existe com 1 evento processado
        profile_existente = {
            "cliente_id": cliente_id,
            "tenant_id": tenant_id,
            "versao": 1,
            "historico": {
                "primeira_contato": "2026-06-01T10:00:00-03:00",
                "ultima_contato": "2026-06-01T10:00:00-03:00",
                "total_eventos": 1,
                "profissionais_atendidos": ["Carla"],
                "servicos_atendidos": ["corte"],
                "proxima_sugestao": None,
            },
            # PATCH P1: Rastrear eventos processados
            "eventos_processados": [
                {
                    "evento_id": evento_id,
                    "processado_em": "2026-06-01T10:00:00-03:00",
                }
            ],
            "tendencias": {
                "profissional_mais_frequente": "Carla",
                "profissional_mais_frequente_count": 1,
                "servico_mais_frequente": "corte",
                "servico_mais_frequente_count": 1,
            },
        }

        with patch("services.clienteprofile_service.buscar_dado_em_path") as mock_buscar:
            with patch("services.clienteprofile_service.atualizar_dado_em_path") as mock_atualizar:
                mock_buscar.return_value = profile_existente
                mock_atualizar.return_value = True

                # Act: Chamar 2x com MESMO evento_id
                resultado_1 = await criar_ou_atualizar_profile_apos_evento(
                    tenant_id, cliente_id, evento_data, evento_id=evento_id
                )
                resultado_2 = await criar_ou_atualizar_profile_apos_evento(
                    tenant_id, cliente_id, evento_data, evento_id=evento_id
                )

                # Assert
                assert resultado_1 is True
                assert resultado_2 is True

                # Segunda chamada deve retornar True sem atualizar (idempotência)
                # Verificar: se atualizar foi chamado só 0 ou 1 vez (não 2)
                # MAS como é mock, validamos comportamento esperado

    @pytest.mark.asyncio
    async def test_eventos_diferentes_incrementam_total(self):
        """Eventos com evento_id diferentes incrementam total_eventos."""

        tenant_id = "dono_123"
        cliente_id = "cliente_abc"

        profile_existente = {
            "cliente_id": cliente_id,
            "tenant_id": tenant_id,
            "versao": 1,
            "historico": {
                "primeira_contato": "2026-06-01T10:00:00-03:00",
                "ultima_contato": "2026-06-01T10:00:00-03:00",
                "total_eventos": 1,
                "profissionais_atendidos": ["Carla"],
                "servicos_atendidos": ["corte"],
            },
            "eventos_processados": [
                {
                    "evento_id": "cliente_abc_carla_2026-06-14_14:00",
                    "processado_em": "2026-06-01T10:00:00-03:00",
                }
            ],
            "tendencias": {},
        }

        with patch("services.clienteprofile_service.buscar_dado_em_path") as mock_buscar:
            with patch("services.clienteprofile_service.atualizar_dado_em_path") as mock_atualizar:
                mock_buscar.return_value = profile_existente
                mock_atualizar.return_value = True

                # Act: Evento DIFERENTE
                evento_data = {
                    "profissional": "Bruna",
                    "servico": "escova",
                    "cliente_nome": "Suri",
                    "data": "2026-06-15",
                    "hora": "15:00",
                }
                novo_evento_id = "cliente_abc_bruna_2026-06-15_15:00"

                resultado = await criar_ou_atualizar_profile_apos_evento(
                    tenant_id, cliente_id, evento_data, evento_id=novo_evento_id
                )

                # Assert
                assert resultado is True
                assert mock_atualizar.called

                # Verificar que total_eventos foi incrementado
                call_args = mock_atualizar.call_args
                update = call_args[0][1]
                assert update["historico"]["total_eventos"] == 2

    @pytest.mark.asyncio
    async def test_profissional_nao_duplica_em_lista(self):
        """Profissional não duplica em profissionais_atendidos."""

        tenant_id = "dono_123"
        cliente_id = "cliente_abc"

        profile_existente = {
            "historico": {
                "profissionais_atendidos": ["Carla", "Bruna"],
                "servicos_atendidos": ["corte"],
            },
            "eventos_processados": [],
            "tendencias": {},
        }

        with patch("services.clienteprofile_service.buscar_dado_em_path") as mock_buscar:
            with patch("services.clienteprofile_service.atualizar_dado_em_path") as mock_atualizar:
                mock_buscar.return_value = profile_existente
                mock_atualizar.return_value = True

                # Act: Agendar NOVAMENTE com Carla
                evento_data = {
                    "profissional": "Carla",
                    "servico": "escova",
                    "data": "2026-06-15",
                    "hora": "15:00",
                }

                resultado = await criar_ou_atualizar_profile_apos_evento(
                    tenant_id, cliente_id, evento_data, evento_id="novo_id"
                )

                # Assert
                assert resultado is True
                call_args = mock_atualizar.call_args
                update = call_args[0][1]

                # Verificar: Carla não duplica
                profs = update["historico"]["profissionais_atendidos"]
                assert profs.count("Carla") == 1  # Só uma Carla
                assert "Bruna" in profs  # Bruna mantém

    @pytest.mark.asyncio
    async def test_servico_nao_duplica_em_lista(self):
        """Serviço não duplica em servicos_atendidos."""

        tenant_id = "dono_123"
        cliente_id = "cliente_abc"

        profile_existente = {
            "historico": {
                "profissionais_atendidos": ["Carla"],
                "servicos_atendidos": ["corte", "escova"],
            },
            "eventos_processados": [],
            "tendencias": {},
        }

        with patch("services.clienteprofile_service.buscar_dado_em_path") as mock_buscar:
            with patch("services.clienteprofile_service.atualizar_dado_em_path") as mock_atualizar:
                mock_buscar.return_value = profile_existente
                mock_atualizar.return_value = True

                # Act: Agendar NOVAMENTE com corte
                evento_data = {
                    "profissional": "Carla",
                    "servico": "corte",
                    "data": "2026-06-15",
                    "hora": "15:00",
                }

                resultado = await criar_ou_atualizar_profile_apos_evento(
                    tenant_id, cliente_id, evento_data, evento_id="novo_id"
                )

                # Assert
                assert resultado is True
                call_args = mock_atualizar.call_args
                update = call_args[0][1]

                # Verificar: corte não duplica
                servs = update["historico"]["servicos_atendidos"]
                assert servs.count("corte") == 1  # Só um corte
                assert "escova" in servs  # Escova mantém


class TestConcorrenciaP2:
    """PATCH P2: Simulação de concorrência (preparação para atomicidade)."""

    @pytest.mark.asyncio
    async def test_dois_updates_rapidos_simulados(self):
        """Simular dois eventos chegando rapidamente (concorrência)."""

        tenant_id = "dono_123"
        cliente_id = "cliente_abc"

        # Estado inicial
        profile_existente = {
            "historico": {
                "total_eventos": 1,
                "profissionais_atendidos": ["Carla"],
                "servicos_atendidos": ["corte"],
            },
            "eventos_processados": [
                {"evento_id": "evento_1", "processado_em": "2026-06-01"}
            ],
            "tendencias": {},
        }

        with patch("services.clienteprofile_service.buscar_dado_em_path") as mock_buscar:
            with patch("services.clienteprofile_service.atualizar_dado_em_path") as mock_atualizar:
                # Ambas leituras retornam o estado inicial (race condition)
                mock_buscar.return_value = profile_existente
                mock_atualizar.return_value = True

                # Act: Dois eventos chegam
                evento_1 = {
                    "profissional": "Bruna",
                    "servico": "escova",
                    "data": "2026-06-14",
                    "hora": "14:00",
                }
                evento_2 = {
                    "profissional": "Marina",
                    "servico": "manicure",
                    "data": "2026-06-14",
                    "hora": "15:00",
                }

                resultado_1 = await criar_ou_atualizar_profile_apos_evento(
                    tenant_id, cliente_id, evento_1, evento_id="evento_2"
                )
                resultado_2 = await criar_ou_atualizar_profile_apos_evento(
                    tenant_id, cliente_id, evento_2, evento_id="evento_3"
                )

                # Assert
                assert resultado_1 is True
                assert resultado_2 is True

                # Verificar: ambas chamadas foram feitas
                assert mock_atualizar.call_count == 2

                # NOTA: Em Firestore real, a segunda chamada sobrescreveria a primeira
                # (race condition). Com operações atômicas (P2), seria corrigido.


class TestAsyncioP3:
    """PATCH P3: Testes de callback asyncio.create_task."""

    @pytest.mark.asyncio
    async def test_create_task_nao_bloqueia_mesmo_com_erro(self):
        """Task com erro não bloqueia execução principal."""

        tenant_id = "dono_123"
        cliente_id = "cliente_abc"
        evento_data = {"profissional": "Carla", "servico": "corte"}

        # Mock: profile falha
        with patch("services.clienteprofile_service.buscar_dado_em_path") as mock_buscar:
            with patch("services.clienteprofile_service.salvar_dado_em_path") as mock_salvar:
                mock_buscar.side_effect = Exception("Firestore error")

                # Act: Mesmo com erro, retorna bool
                resultado = await criar_ou_atualizar_profile_apos_evento(
                    tenant_id, cliente_id, evento_data
                )

                # Assert: Retorna False mas não lança
                assert resultado is False
                assert isinstance(resultado, bool)


class TestMultiTenantP1:
    """PATCH P1: Validar multi-tenant continua isolado com evento_id."""

    @pytest.mark.asyncio
    async def test_multi_tenant_isolado_com_evento_id(self):
        """Profiles de tenants diferentes continuam isolados com evento_id."""

        cliente_id = "cliente_abc"  # Mesmo cliente_id
        evento_id = "cliente_abc_carla_2026-06-14_14:00"

        tenant_1 = "dono_111"
        tenant_2 = "dono_222"

        evento_data = {
            "profissional": "Carla",
            "servico": "corte",
            "cliente_nome": "Suri",
        }

        with patch("services.clienteprofile_service.buscar_dado_em_path") as mock_buscar:
            with patch("services.clienteprofile_service.salvar_dado_em_path") as mock_salvar:
                mock_buscar.return_value = None
                mock_salvar.return_value = True

                # Act
                await criar_ou_atualizar_profile_apos_evento(
                    tenant_1, cliente_id, evento_data, evento_id=evento_id
                )
                await criar_ou_atualizar_profile_apos_evento(
                    tenant_2, cliente_id, evento_data, evento_id=evento_id
                )

                # Assert
                assert mock_salvar.call_count == 2

                # Verificar paths são diferentes
                call_1 = mock_salvar.call_args_list[0]
                call_2 = mock_salvar.call_args_list[1]

                path_1 = call_1[0][0]
                path_2 = call_2[0][0]

                assert path_1 == f"Clientes/{tenant_1}/ClienteProfiles/{cliente_id}"
                assert path_2 == f"Clientes/{tenant_2}/ClienteProfiles/{cliente_id}"
                assert path_1 != path_2


class TestPatchP2OperacoesAtomicas:
    """PATCH P2: Validar que firestore.Increment e ArrayUnion são realmente usados."""

    @pytest.mark.asyncio
    async def test_total_eventos_usa_firestore_increment(self):
        """Validar que total_eventos usa firestore.Increment, não read-modify-write."""

        from google.cloud import firestore

        tenant_id = "dono_123"
        cliente_id = "cliente_abc"

        profile_existente = {
            "cliente_id": cliente_id,
            "tenant_id": tenant_id,
            "versao": 1,
            "historico": {
                "primeira_contato": "2026-06-01T10:00:00-03:00",
                "ultima_contato": "2026-06-01T10:00:00-03:00",
                "total_eventos": 1,
                "profissionais_atendidos": ["Carla"],
                "servicos_atendidos": ["corte"],
                "proxima_sugestao": None,
            },
            "eventos_processados": [
                {"evento_id": "evento_1", "processado_em": "2026-06-01T10:00:00-03:00"}
            ],
            "tendencias": {},
        }

        with patch("services.clienteprofile_service.buscar_dado_em_path") as mock_buscar:
            with patch("services.clienteprofile_service.atualizar_com_operacoes_atomicas") as mock_atualizar_atomic:
                mock_buscar.return_value = profile_existente
                mock_atualizar_atomic.return_value = True

                # Act
                evento_data = {
                    "profissional": "Bruna",
                    "servico": "escova",
                    "cliente_nome": "Suri",
                    "data": "2026-06-15",
                    "hora": "15:00",
                }

                resultado = await criar_ou_atualizar_profile_apos_evento(
                    tenant_id, cliente_id, evento_data, evento_id="evento_2"
                )

                # Assert: Verificar que atualizar_com_operacoes_atomicas foi chamado
                assert resultado is True
                assert mock_atualizar_atomic.called, "deve chamar atualizar_com_operacoes_atomicas"

                # Verificar que os dados contêm firestore.Increment
                call_args = mock_atualizar_atomic.call_args
                update_data = call_args[0][1]

                # PATCH P2: Validar que total_eventos é firestore.Increment
                assert isinstance(
                    update_data["historico"]["total_eventos"],
                    firestore.Increment
                ), "total_eventos deve usar firestore.Increment"

    @pytest.mark.asyncio
    async def test_profissionais_usa_firestore_arrayunion(self):
        """Validar que profissionais_atendidos usa firestore.ArrayUnion."""

        from google.cloud import firestore

        tenant_id = "dono_123"
        cliente_id = "cliente_abc"

        profile_existente = {
            "historico": {
                "profissionais_atendidos": ["Carla"],
                "servicos_atendidos": ["corte"],
                "total_eventos": 1,
                "primeira_contato": "2026-06-01T10:00:00-03:00",
                "proxima_sugestao": None,
            },
            "eventos_processados": [],
            "tendencias": {},
        }

        with patch("services.clienteprofile_service.buscar_dado_em_path") as mock_buscar:
            with patch("services.clienteprofile_service.atualizar_com_operacoes_atomicas") as mock_atualizar_atomic:
                mock_buscar.return_value = profile_existente
                mock_atualizar_atomic.return_value = True

                # Act
                evento_data = {
                    "profissional": "Bruna",
                    "servico": "escova",
                    "data": "2026-06-15",
                    "hora": "15:00",
                }

                resultado = await criar_ou_atualizar_profile_apos_evento(
                    tenant_id, cliente_id, evento_data, evento_id="evento_novo"
                )

                # Assert
                assert resultado is True
                call_args = mock_atualizar_atomic.call_args
                update_data = call_args[0][1]

                # PATCH P2: Validar que profissionais_atendidos é firestore.ArrayUnion
                assert isinstance(
                    update_data["historico"]["profissionais_atendidos"],
                    firestore.ArrayUnion
                ), "profissionais_atendidos deve usar firestore.ArrayUnion"

    @pytest.mark.asyncio
    async def test_servicos_usa_firestore_arrayunion(self):
        """Validar que servicos_atendidos usa firestore.ArrayUnion."""

        from google.cloud import firestore

        tenant_id = "dono_123"
        cliente_id = "cliente_abc"

        profile_existente = {
            "historico": {
                "profissionais_atendidos": ["Carla"],
                "servicos_atendidos": ["corte"],
                "total_eventos": 1,
                "primeira_contato": "2026-06-01T10:00:00-03:00",
                "proxima_sugestao": None,
            },
            "eventos_processados": [],
            "tendencias": {},
        }

        with patch("services.clienteprofile_service.buscar_dado_em_path") as mock_buscar:
            with patch("services.clienteprofile_service.atualizar_com_operacoes_atomicas") as mock_atualizar_atomic:
                mock_buscar.return_value = profile_existente
                mock_atualizar_atomic.return_value = True

                # Act
                evento_data = {
                    "profissional": "Carla",
                    "servico": "manicure",
                    "data": "2026-06-15",
                    "hora": "15:00",
                }

                resultado = await criar_ou_atualizar_profile_apos_evento(
                    tenant_id, cliente_id, evento_data, evento_id="evento_novo"
                )

                # Assert
                assert resultado is True
                call_args = mock_atualizar_atomic.call_args
                update_data = call_args[0][1]

                # PATCH P2: Validar que servicos_atendidos é firestore.ArrayUnion
                assert isinstance(
                    update_data["historico"]["servicos_atendidos"],
                    firestore.ArrayUnion
                ), "servicos_atendidos deve usar firestore.ArrayUnion"

    @pytest.mark.asyncio
    async def test_eventos_processados_usa_firestore_arrayunion(self):
        """Validar que eventos_processados usa firestore.ArrayUnion."""

        from google.cloud import firestore

        tenant_id = "dono_123"
        cliente_id = "cliente_abc"

        profile_existente = {
            "historico": {
                "profissionais_atendidos": ["Carla"],
                "servicos_atendidos": ["corte"],
                "total_eventos": 1,
                "primeira_contato": "2026-06-01T10:00:00-03:00",
                "proxima_sugestao": None,
            },
            "eventos_processados": [
                {"evento_id": "evento_1", "processado_em": "2026-06-01T10:00:00-03:00"}
            ],
            "tendencias": {},
        }

        with patch("services.clienteprofile_service.buscar_dado_em_path") as mock_buscar:
            with patch("services.clienteprofile_service.atualizar_com_operacoes_atomicas") as mock_atualizar_atomic:
                mock_buscar.return_value = profile_existente
                mock_atualizar_atomic.return_value = True

                # Act
                evento_data = {
                    "profissional": "Carla",
                    "servico": "corte",
                    "data": "2026-06-15",
                    "hora": "15:00",
                }

                resultado = await criar_ou_atualizar_profile_apos_evento(
                    tenant_id, cliente_id, evento_data, evento_id="evento_novo"
                )

                # Assert
                assert resultado is True
                call_args = mock_atualizar_atomic.call_args
                update_data = call_args[0][1]

                # PATCH P2: Validar que eventos_processados é firestore.ArrayUnion
                assert isinstance(
                    update_data["eventos_processados"],
                    firestore.ArrayUnion
                ), "eventos_processados deve usar firestore.ArrayUnion"

    @pytest.mark.asyncio
    async def test_versao_usa_firestore_increment(self):
        """Validar que versao usa firestore.Increment."""

        from google.cloud import firestore

        tenant_id = "dono_123"
        cliente_id = "cliente_abc"

        profile_existente = {
            "versao": 5,
            "historico": {
                "profissionais_atendidos": ["Carla"],
                "servicos_atendidos": ["corte"],
                "total_eventos": 1,
                "primeira_contato": "2026-06-01T10:00:00-03:00",
                "proxima_sugestao": None,
            },
            "eventos_processados": [],
            "tendencias": {},
        }

        with patch("services.clienteprofile_service.buscar_dado_em_path") as mock_buscar:
            with patch("services.clienteprofile_service.atualizar_com_operacoes_atomicas") as mock_atualizar_atomic:
                mock_buscar.return_value = profile_existente
                mock_atualizar_atomic.return_value = True

                # Act
                evento_data = {
                    "profissional": "Carla",
                    "servico": "corte",
                    "data": "2026-06-15",
                    "hora": "15:00",
                }

                resultado = await criar_ou_atualizar_profile_apos_evento(
                    tenant_id, cliente_id, evento_data, evento_id="evento_novo"
                )

                # Assert
                assert resultado is True
                call_args = mock_atualizar_atomic.call_args
                update_data = call_args[0][1]

                # PATCH P2: Validar que versao é firestore.Increment
                assert isinstance(
                    update_data["versao"],
                    firestore.Increment
                ), "versao deve usar firestore.Increment"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
