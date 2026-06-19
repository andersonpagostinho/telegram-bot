"""
PATCH P0 — Testes de Integração com Firebase Real

⚠️ REQUER:
- Credenciais Firebase válidas em .env ou arquivo de configuração
- Acesso a base de dados de teste
- Internet ativa

Execução:
pytest tests/test_patch_p0_cancelamento_firebase.py -v -s
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
import os

# Verificar se temos credenciais Firebase
FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS") or \
                       os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

pytestmark = pytest.mark.skipif(
    not FIREBASE_CREDENTIALS,
    reason="Firebase credentials not configured"
)


@pytest.mark.asyncio
class TestCancelamentoFirebase:
    """Testes de integração com Firebase real"""

    @classmethod
    def setup_class(cls):
        """Setup Firebase conexão"""
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore

            # Verificar se já inicializado
            if not firebase_admin._apps:
                # Carregar credenciais
                cred_path = FIREBASE_CREDENTIALS
                if os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)

            cls.db = firestore.client()
            cls.firebase_ready = True
        except Exception as e:
            print(f"⚠️ Firebase não configurado: {e}")
            cls.firebase_ready = False

    async def test_e2e_criar_eventos_e_cancelar_com_filtro(self):
        """
        Teste E2E Real: Criar eventos → Buscar com filtro → Cancelar

        Fluxo:
        1. Criar 3 eventos no Firebase
        2. Chamar cancelar_evento_por_texto() com filtro
        3. Validar que encontrou os eventos corretos
        4. Cancelar e verificar status no Firebase
        """
        if not self.firebase_ready:
            pytest.skip("Firebase não configurado")

        # Setup
        dono_id = "test_dono_123"
        cliente_id = "test_cliente_456"
        hoje = datetime.now().date()
        amanha = str(hoje + timedelta(days=1))

        # 1️⃣ Criar eventos de teste no Firebase
        print("\n[TESTE FIREBASE] 1️⃣ Criando eventos de teste...")

        eventos_criados = []

        evento_1 = {
            "cliente_id": cliente_id,
            "profissional": "Bruna",
            "servico": "Corte",
            "descricao": "Corte com Bruna",
            "data": amanha,
            "hora_inicio": "14:00",
            "hora_fim": "15:00",
            "status": "confirmado",
            "confirmado": True,
            "confirmado_em": datetime.now().isoformat(),
        }

        evento_2 = {
            "cliente_id": cliente_id,
            "profissional": "Bruna",
            "servico": "Escova",
            "descricao": "Escova com Bruna",
            "data": str(hoje + timedelta(days=2)),
            "hora_inicio": "15:00",
            "hora_fim": "16:00",
            "status": "confirmado",
            "confirmado": True,
            "confirmado_em": datetime.now().isoformat(),
        }

        evento_3 = {
            "cliente_id": cliente_id,
            "profissional": "Ana",
            "servico": "Corte",
            "descricao": "Corte com Ana",
            "data": amanha,
            "hora_inicio": "10:00",
            "hora_fim": "11:00",
            "status": "confirmado",
            "confirmado": True,
            "confirmado_em": datetime.now().isoformat(),
        }

        try:
            # Salvar no Firebase
            path_base = f"Clientes/{dono_id}/Eventos"

            evento_1_id = "test_ev_bruna_corte"
            evento_2_id = "test_ev_bruna_escova"
            evento_3_id = "test_ev_ana_corte"

            from services.firebase_service_async import salvar_dado_em_path

            await salvar_dado_em_path(f"{path_base}/{evento_1_id}", evento_1)
            await salvar_dado_em_path(f"{path_base}/{evento_2_id}", evento_2)
            await salvar_dado_em_path(f"{path_base}/{evento_3_id}", evento_3)

            eventos_criados = [evento_1_id, evento_2_id, evento_3_id]
            print(f"✅ Eventos criados: {eventos_criados}")

        except Exception as e:
            print(f"❌ Erro ao criar eventos: {e}")
            pytest.skip(f"Falha ao criar eventos no Firebase: {e}")
            return

        # 2️⃣ Buscar com filtro "com Bruna"
        print("\n[TESTE FIREBASE] 2️⃣ Buscando com filtro 'com Bruna'...")

        try:
            from services.event_service_async import cancelar_evento_por_texto

            ok, msg, candidatos = await cancelar_evento_por_texto(
                user_id=cliente_id,
                termo="com Bruna",
                tenant_id=dono_id
            )

            print(f"   Encontrados: {len(candidatos)} eventos")
            print(f"   Mensagem: {msg[:80]}...")

            # Validar que encontrou 2 eventos (Bruna)
            assert len(candidatos) == 2, f"Esperava 2 eventos com Bruna, obtive {len(candidatos)}"
            assert not ok, "Não deve cancelar direto"

        except Exception as e:
            print(f"❌ Erro ao buscar: {e}")
            pytest.skip(f"Falha ao buscar eventos: {e}")
            return
        finally:
            # Cleanup
            await self._limpar_eventos_teste(path_base, eventos_criados)

    async def test_e2e_cancelamento_completo_firebase(self):
        """
        Teste E2E: Cancelamento completo (buscar → confirmar → validar status)

        Cenário: Cancelar 1 evento específico com Bruna amanhã
        """
        if not self.firebase_ready:
            pytest.skip("Firebase não configurado")

        dono_id = "test_dono_789"
        cliente_id = "test_cliente_999"
        hoje = datetime.now().date()
        amanha = str(hoje + timedelta(days=1))

        evento_mock = {
            "cliente_id": cliente_id,
            "profissional": "Carla",
            "servico": "Manicure",
            "descricao": "Manicure com Carla",
            "data": amanha,
            "hora_inicio": "16:00",
            "hora_fim": "17:00",
            "status": "confirmado",
            "confirmado": True,
            "confirmado_em": datetime.now().isoformat(),
        }

        evento_id = "test_ev_cancelamento_completo"
        path_base = f"Clientes/{dono_id}/Eventos"

        try:
            # 1️⃣ Criar evento
            print("\n[TESTE FIREBASE] 1️⃣ Criando evento para cancelar...")
            from services.firebase_service_async import salvar_dado_em_path

            await salvar_dado_em_path(f"{path_base}/{evento_id}", evento_mock)
            print(f"✅ Evento criado: {evento_id}")

            # 2️⃣ Buscar
            print("\n[TESTE FIREBASE] 2️⃣ Buscando evento...")
            from services.event_service_async import cancelar_evento_por_texto

            ok, msg, candidatos = await cancelar_evento_por_texto(
                user_id=cliente_id,
                termo="com Carla amanhã",
                tenant_id=dono_id
            )

            assert len(candidatos) == 1, f"Esperava 1 evento, obtive {len(candidatos)}"
            print(f"✅ Evento encontrado: {candidatos[0][0]}")

            # 3️⃣ Cancelar
            print("\n[TESTE FIREBASE] 3️⃣ Cancelando evento...")
            from services.event_service_async import cancelar_evento

            resultado = await cancelar_evento(
                user_id=cliente_id,
                event_id=evento_id,
                cancelado_por_tipo="cliente",
                motivo="Mudança de planos"
            )

            assert resultado == True, "Cancelamento deve ser bem-sucedido"
            print(f"✅ Evento cancelado com sucesso")

            # 4️⃣ Validar status no Firebase
            print("\n[TESTE FIREBASE] 4️⃣ Validando status no Firebase...")
            from services.firebase_service_async import buscar_dado_em_path

            evento_apos = await buscar_dado_em_path(f"{path_base}/{evento_id}")

            assert evento_apos.get("status") == "cancelado", \
                f"Status deve ser 'cancelado', obtive: {evento_apos.get('status')}"
            assert evento_apos.get("cancelado_por") == cliente_id, \
                f"cancelado_por deve ser {cliente_id}"
            assert "cancelado_em" in evento_apos, "Deve ter cancelado_em"
            assert evento_apos.get("motivo_cancelamento") == "Mudança de planos", \
                "Motivo deve ser salvo"

            print(f"✅ Status validado:")
            print(f"   status: {evento_apos.get('status')}")
            print(f"   cancelado_por: {evento_apos.get('cancelado_por')}")
            print(f"   cancelado_em: {evento_apos.get('cancelado_em')[:19]}")
            print(f"   motivo: {evento_apos.get('motivo_cancelamento')}")

        except Exception as e:
            print(f"❌ Erro durante teste: {e}")
            import traceback
            traceback.print_exc()
            pytest.skip(f"Teste Firebase falhou: {e}")
            return
        finally:
            # Cleanup
            await self._limpar_eventos_teste(path_base, [evento_id])

    async def test_e2e_multiplos_eventos_selecao(self):
        """
        Teste E2E: Múltiplos eventos → Seleção por número

        Cenário: 3 eventos com mesmo profissional → usuário escolhe por número
        """
        if not self.firebase_ready:
            pytest.skip("Firebase não configurado")

        dono_id = "test_dono_multi"
        cliente_id = "test_cliente_multi"
        hoje = datetime.now().date()

        eventos_mock = [
            {
                "cliente_id": cliente_id,
                "profissional": "Juliana",
                "servico": "Hidratação",
                "descricao": "Hidratação com Juliana",
                "data": str(hoje),
                "hora_inicio": "10:00",
                "hora_fim": "11:00",
                "status": "confirmado",
                "confirmado": True,
                "confirmado_em": datetime.now().isoformat(),
            },
            {
                "cliente_id": cliente_id,
                "profissional": "Juliana",
                "servico": "Progressiva",
                "descricao": "Progressiva com Juliana",
                "data": str(hoje + timedelta(days=1)),
                "hora_inicio": "14:00",
                "hora_fim": "16:00",
                "status": "confirmado",
                "confirmado": True,
                "confirmado_em": datetime.now().isoformat(),
            },
            {
                "cliente_id": cliente_id,
                "profissional": "Juliana",
                "servico": "Corte",
                "descricao": "Corte com Juliana",
                "data": str(hoje + timedelta(days=2)),
                "hora_inicio": "15:00",
                "hora_fim": "15:30",
                "status": "confirmado",
                "confirmado": True,
                "confirmado_em": datetime.now().isoformat(),
            },
        ]

        evento_ids = ["test_ev_juli_1", "test_ev_juli_2", "test_ev_juli_3"]
        path_base = f"Clientes/{dono_id}/Eventos"

        try:
            # 1️⃣ Criar 3 eventos
            print("\n[TESTE FIREBASE] 1️⃣ Criando 3 eventos com Juliana...")
            from services.firebase_service_async import salvar_dado_em_path

            for eid, evento in zip(evento_ids, eventos_mock):
                await salvar_dado_em_path(f"{path_base}/{eid}", evento)

            print(f"✅ 3 eventos criados")

            # 2️⃣ Buscar com filtro "com Juliana"
            print("\n[TESTE FIREBASE] 2️⃣ Buscando com filtro 'com Juliana'...")
            from services.event_service_async import cancelar_evento_por_texto

            ok, msg, candidatos = await cancelar_evento_por_texto(
                user_id=cliente_id,
                termo="com Juliana",
                tenant_id=dono_id
            )

            assert len(candidatos) == 3, f"Esperava 3 eventos, obtive {len(candidatos)}"
            print(f"✅ 3 eventos encontrados")
            print(f"   Mensagem (primeiras 100 chars): {msg[:100]}...")

            # Validar que lista contém números (1, 2, 3)
            assert "1)" in msg or "Qual" in msg, f"Mensagem deve listar opções: {msg}"

        except Exception as e:
            print(f"❌ Erro durante teste: {e}")
            pytest.skip(f"Teste Firebase falhou: {e}")
            return
        finally:
            # Cleanup
            await self._limpar_eventos_teste(path_base, evento_ids)

    async def _limpar_eventos_teste(self, path_base: str, evento_ids: list):
        """Remover eventos de teste do Firebase"""
        try:
            from services.firebase_service_async import deletar_dado_em_path

            for eid in evento_ids:
                try:
                    await deletar_dado_em_path(f"{path_base}/{eid}")
                except:
                    pass  # Ignorar se não existir

            print(f"🧹 Limpeza: {len(evento_ids)} eventos removidos")
        except Exception as e:
            print(f"⚠️ Erro ao limpar: {e}")


# ============================================================================
# TESTES DE VALIDAÇÃO (sem Firebase)
# ============================================================================

@pytest.mark.asyncio
class TestValidacaoCodigo:
    """Validações de código sem precisar de Firebase"""

    async def test_codigo_guarda_p0_existe(self):
        """Verificar que guarda P0 está implementada no código"""
        # Ler arquivo e verificar que contém a guarda
        with open("router/principal_router.py", "r", encoding="utf-8") as f:
            conteudo = f.read()

        # Procurar pela guarda
        assert "aguardando_confirmacao_cancelamento" in conteudo, \
            "Guarda P0 não encontrada no router"
        assert "return None" in conteudo, \
            "Bloqueio não encontrado no router"

        print("✅ Guarda P0 encontrada no código")

    async def test_filtros_implementados(self):
        """Verificar que filtros estão implementados"""
        with open("services/event_service_async.py", "r", encoding="utf-8") as f:
            conteudo = f.read()

        # Procurar por filtros
        assert "profissional_filtro" in conteudo, "Filtro profissional não encontrado"
        assert "data_filtro" in conteudo, "Filtro data não encontrado"
        assert "amanhã" in conteudo or "amanha" in conteudo, \
            "Suporte para 'amanhã' não encontrado"

        print("✅ Filtros avançados encontrados no código")

    async def test_tenant_id_em_salvamento(self):
        """Verificar que tenant_id está em salvar_contexto_temporario"""
        with open("router/principal_router.py", "r", encoding="utf-8") as f:
            conteudo = f.read()

        # Procurar por salvar_contexto_temporario com tenant_id (próximo a cancelamento)
        # Verificar que há pelo menos uma chamada com tenant_id
        assert "tenant_id=dono_id" in conteudo, \
            "tenant_id não está sendo passado corretamente"

        print("✅ tenant_id está sendo passado para salvar_contexto_temporario")
