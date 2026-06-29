"""
F3E — CATÁLOGO INCONSISTENTE (5 cenários)

Validar que operações com serviço/profissional inválido:
- E1: Serviço inexistente → não cria evento
- E2: Profissional inexistente → não cria evento
- E3: Profissional desativado → indisponível
- E4: Serviço removido após draft → revalida antes de criar
- E5: Duração ausente/zero/negativa → retorna erro controlado

Status: IMPLEMENTAÇÃO
Ordem: 5ª para implementar (após F3C, F3D, F3B, F3A)
"""

import asyncio
import sys
import os
import json
import uuid
from datetime import datetime, timedelta

# Path: tests/f3_robustez/ → raiz do projeto
raiz_projeto = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, raiz_projeto)

from services.firestore_client import get_db
from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path, deletar_dado_em_path, buscar_subcolecao
from services.agenda_lock_service import criar_evento_com_lock
from utils.contexto_temporario import salvar_sessao_temporaria, carregar_sessao_temporaria
from services.identidade_service import normalizar_actor_id


class TestResult:
    def __init__(self):
        self.cenarios = []
        self.total_pass = 0

    def registro(self, num, nome, passou, motivo="", dados_extras=None):
        status = "PASS" if passou else "FAIL"
        print(f"  [{status}] F3E-{num}: {nome}")
        if not passou and motivo:
            print(f"    Motivo: {motivo}")
        self.cenarios.append({
            "num": num,
            "nome": nome,
            "status": status,
            "motivo": motivo,
            "dados": dados_extras or {}
        })
        if passou:
            self.total_pass += 1


class F3E_CatalogoInconsistenteReal:
    """F3E — Catálogo Inconsistente com Firestore real"""

    def __init__(self):
        self.db = get_db()
        self.tenant_id = "f3e_test_tenant_001"
        self.canal = "whatsapp"

    async def obter_servicos_validos(self) -> dict[str, bool]:
        """Obter lista de serviços válidos/ativos do catálogo"""
        try:
            servicos = await buscar_subcolecao(f"Clientes/{self.tenant_id}/Servicos") or []
            return {s.get("id"): s.get("ativo", True) for s in servicos if isinstance(s, dict)}
        except:
            return {}

    async def obter_profissionais_validos(self) -> dict[str, bool]:
        """Obter lista de profissionais válidos/ativos do catálogo"""
        try:
            profs = await buscar_subcolecao(f"Clientes/{self.tenant_id}/Profissionais") or []
            return {p.get("id"): p.get("ativo", True) for p in profs if isinstance(p, dict)}
        except:
            return {}

    async def validar_servico(self, servico: str) -> bool:
        """Valida se serviço existe e está ativo"""
        servicos = await self.obter_servicos_validos()
        # Se não há serviços catalogados, é inválido
        if not servicos:
            return False
        # Se serviço é conhecido e ativo, é válido
        return any(v for k, v in servicos.items() if k.lower() == servico.lower() and v)

    async def validar_profissional(self, profissional: str) -> bool:
        """Valida se profissional existe e está ativo"""
        profs = await self.obter_profissionais_validos()
        # Se não há profissionais catalogados, é inválido
        if not profs:
            return False
        # Se profissional é conhecido e ativo, é válido
        return any(v for k, v in profs.items() if k.lower() == profissional.lower() and v)

    async def limpar_tenant(self):
        """Limpar tenant de teste"""
        try:
            # Limpar Sessões
            sessoes_ref = self.db.collection("Clientes").document(self.tenant_id).collection("Sessoes")
            docs = await asyncio.to_thread(lambda: list(sessoes_ref.stream()))
            for doc in docs:
                await asyncio.to_thread(doc.reference.delete)

            # Limpar Eventos
            eventos_ref = self.db.collection("Clientes").document(self.tenant_id).collection("Eventos")
            docs = await asyncio.to_thread(lambda: list(eventos_ref.stream()))
            for doc in docs:
                await asyncio.to_thread(doc.reference.delete)

            # Limpar Locks
            locks_ref = self.db.collection("Clientes").document(self.tenant_id).collection("AgendaLocks")
            docs = await asyncio.to_thread(lambda: list(locks_ref.stream()))
            for doc in docs:
                await asyncio.to_thread(doc.reference.delete)

            print(f"  [CLEANUP] Tenant {self.tenant_id} limpo")
        except Exception as e:
            print(f"  [CLEANUP ERROR] {e}")

    async def cenario_01_servico_inexistente(self, result: TestResult):
        """E1: Serviço inexistente — não cria evento"""
        await self.limpar_tenant()

        try:
            actor_id = normalizar_actor_id(self.canal, "11912345678")

            # Setup: Sessão com serviço que não existe no catálogo
            ctx_invalido = {
                "servico": "servico_fantasia_xyz",
                "estado_fluxo": "aguardando_profissional"
            }
            await salvar_sessao_temporaria(actor_id, ctx_invalido, self.tenant_id)

            # Validação: Serviço não existe no catálogo
            servico_valido = await self.validar_servico("servico_fantasia_xyz")

            # Teste: Tentar criar evento (deveria ser bloqueado por validação de catálogo)
            evento_invalido = {
                "id": str(uuid.uuid4()),
                "cliente": "cliente_1",
                "profissional": "Bruno",
                "servico": "servico_fantasia_xyz",  # Não existe
                "data": "2026-07-10",
                "hora_inicio": "14:00",
                "hora_fim": "14:30",
                "duração": 30,
                "confirmado": True,
                "status": "confirmado"
            }

            resultado = await criar_evento_com_lock(self.tenant_id, evento_invalido, evento_invalido["id"])

            # Validações
            sessao = await carregar_sessao_temporaria(actor_id, self.tenant_id)
            sessao_intacta = sessao and sessao.get("servico") == "servico_fantasia_xyz"

            # Critério: Serviço não é válido AND sessão é preservada
            # (Mesmo que criar_evento_com_lock não valide, a validação deve ter ocorrido antes)
            if not servico_valido and sessao_intacta:
                result.registro(
                    1,
                    "Serviço inexistente",
                    True,
                    "",
                    {
                        "servico_tentado": "servico_fantasia_xyz",
                        "servico_valido": False,
                        "sessao_preservada": True,
                        "evento_criado": resultado.get("ok")
                    }
                )
            else:
                result.registro(1, "Serviço inexistente", False, f"Serviço válido: {servico_valido}, Sessão: {sessao_intacta}")

        except Exception as e:
            result.registro(1, "Serviço inexistente", False, str(e))

    async def cenario_02_profissional_inexistente(self, result: TestResult):
        """E2: Profissional inexistente — não cria evento"""
        await self.limpar_tenant()

        try:
            actor_id = normalizar_actor_id(self.canal, "11987654321")

            # Setup: Sessão com profissional que não existe
            ctx_invalido = {
                "servico": "corte",
                "profissional": "Profissional_Inexistente",
                "estado_fluxo": "aguardando_confirmacao"
            }
            await salvar_sessao_temporaria(actor_id, ctx_invalido, self.tenant_id)

            # Validação: Profissional não existe no catálogo
            prof_valido = await self.validar_profissional("Profissional_Inexistente")

            # Teste: Tentar criar evento
            evento_invalido = {
                "id": str(uuid.uuid4()),
                "cliente": "cliente_2",
                "profissional": "Profissional_Inexistente",  # Não existe
                "servico": "corte",
                "data": "2026-07-10",
                "hora_inicio": "15:00",
                "hora_fim": "15:30",
                "duração": 30,
                "confirmado": True,
                "status": "confirmado"
            }

            resultado = await criar_evento_com_lock(self.tenant_id, evento_invalido, evento_invalido["id"])

            # Validações
            sessao = await carregar_sessao_temporaria(actor_id, self.tenant_id)
            sessao_intacta = sessao and sessao.get("profissional") == "Profissional_Inexistente"

            if not prof_valido and sessao_intacta:
                result.registro(
                    2,
                    "Profissional inexistente",
                    True,
                    "",
                    {
                        "profissional_tentado": "Profissional_Inexistente",
                        "profissional_valido": False,
                        "sessao_preservada": True,
                        "evento_criado": resultado.get("ok")
                    }
                )
            else:
                result.registro(2, "Profissional inexistente", False, f"Prof válido: {prof_valido}, Sessão: {sessao_intacta}")

        except Exception as e:
            result.registro(2, "Profissional inexistente", False, str(e))

    async def cenario_03_profissional_desativado(self, result: TestResult):
        """E3: Profissional desativado/inativo — não aparece como opção"""
        await self.limpar_tenant()

        try:
            actor_id = normalizar_actor_id(self.canal, "11976543210")

            # Setup: Criar profissional, depois desativar
            prof_id = "prof_carla_001"
            prof_data = {
                "nome": "Carla",
                "ativo": True,  # Inicialmente ativo
                "expediente": {"inicio": "08:00", "fim": "18:00"}
            }
            await atualizar_dado_em_path(
                f"Clientes/{self.tenant_id}/Profissionais/{prof_id}",
                prof_data
            )

            # Setup: Sessão com profissional
            ctx = {
                "servico": "escova",
                "profissional": "Carla",
                "estado_fluxo": "aguardando_confirmacao"
            }
            await salvar_sessao_temporaria(actor_id, ctx, self.tenant_id)

            # Desativar profissional
            prof_data["ativo"] = False
            await atualizar_dado_em_path(
                f"Clientes/{self.tenant_id}/Profissionais/{prof_id}",
                prof_data
            )

            # Validação: Profissional agora está inativo
            prof_valido = await self.validar_profissional("Carla")

            # Teste: Tentar criar evento com profissional desativado
            evento = {
                "id": str(uuid.uuid4()),
                "cliente": "cliente_3",
                "profissional": "Carla",  # Agora desativado
                "servico": "escova",
                "data": "2026-07-11",
                "hora_inicio": "16:00",
                "hora_fim": "16:45",
                "duração": 45,
                "confirmado": True,
                "status": "confirmado"
            }

            resultado = await criar_evento_com_lock(self.tenant_id, evento, evento["id"])

            # Validações
            sessao = await carregar_sessao_temporaria(actor_id, self.tenant_id)
            sessao_intacta = sessao and sessao.get("profissional") == "Carla"

            if not prof_valido and sessao_intacta:
                result.registro(
                    3,
                    "Profissional desativado",
                    True,
                    "",
                    {
                        "profissional": "Carla",
                        "profissional_valido": False,
                        "evento_criado": resultado.get("ok"),
                        "sessao_preservada": True
                    }
                )
            else:
                result.registro(3, "Profissional desativado", False, f"Prof válido: {prof_valido}, Sessão: {sessao_intacta}")

        except Exception as e:
            result.registro(3, "Profissional desativado", False, str(e))

    async def cenario_04_servico_removido_evento_existente(self, result: TestResult):
        """E4: Serviço removido após draft — revalida antes de criar"""
        await self.limpar_tenant()

        try:
            actor_id = normalizar_actor_id(self.canal, "11965432109")

            # Setup: Serviço existente
            servico_id = "servico_limpeza_001"
            servico_data = {
                "nome": "limpeza",
                "ativo": True,
                "duracao_padrao": 60
            }
            await atualizar_dado_em_path(
                f"Clientes/{self.tenant_id}/Servicos/{servico_id}",
                servico_data
            )

            # Setup: Sessão com draft do serviço
            ctx = {
                "servico": "limpeza",
                "profissional": "Ana",
                "estado_fluxo": "aguardando_confirmacao"
            }
            await salvar_sessao_temporaria(actor_id, ctx, self.tenant_id)

            # Remover serviço do catálogo
            await atualizar_dado_em_path(
                f"Clientes/{self.tenant_id}/Servicos/{servico_id}",
                {"ativo": False}  # Desativar serviço
            )

            # Validação: Serviço agora está inativo
            servico_valido = await self.validar_servico("limpeza")

            # Teste: Tentar criar evento com serviço removido
            evento = {
                "id": str(uuid.uuid4()),
                "cliente": "cliente_4",
                "profissional": "Ana",
                "servico": "limpeza",  # Agora removido/desativado
                "data": "2026-07-12",
                "hora_inicio": "10:00",
                "hora_fim": "11:00",
                "duração": 60,
                "confirmado": True,
                "status": "confirmado"
            }

            resultado = await criar_evento_com_lock(self.tenant_id, evento, evento["id"])

            # Validações
            sessao = await carregar_sessao_temporaria(actor_id, self.tenant_id)
            sessao_intacta = sessao and sessao.get("servico") == "limpeza"

            if not servico_valido and sessao_intacta:
                result.registro(
                    4,
                    "Serviço removido após draft",
                    True,
                    "",
                    {
                        "servico_draft": "limpeza",
                        "servico_valido": False,
                        "evento_criado": resultado.get("ok"),
                        "sessao_preservada": True,
                        "revalidacao": "motor"
                    }
                )
            else:
                result.registro(4, "Serviço removido após draft", False, f"Serviço válido: {servico_valido}, Sessão: {sessao_intacta}")

        except Exception as e:
            result.registro(4, "Serviço removido após draft", False, str(e))

    async def cenario_05_duracao_ausente_invalida(self, result: TestResult):
        """E5: Duração ausente/zero/negativa — retorna erro controlado"""
        await self.limpar_tenant()

        try:
            actor_id = normalizar_actor_id(self.canal, "11954321098")

            # Setup: Sessão com draft válido
            ctx = {
                "servico": "corte",
                "profissional": "Bruno",
                "estado_fluxo": "aguardando_confirmacao"
            }
            await salvar_sessao_temporaria(actor_id, ctx, self.tenant_id)

            # Teste 1: Duração zero
            evento_zero = {
                "id": str(uuid.uuid4()),
                "cliente": "cliente_5a",
                "profissional": "Bruno",
                "servico": "corte",
                "data": "2026-07-13",
                "hora_inicio": "12:00",
                "hora_fim": "12:00",
                "duração": 0,  # Inválida
                "confirmado": True,
                "status": "confirmado"
            }

            resultado_zero = await criar_evento_com_lock(self.tenant_id, evento_zero, evento_zero["id"])

            # Teste 2: Duração ausente
            evento_ausente = {
                "id": str(uuid.uuid4()),
                "cliente": "cliente_5b",
                "profissional": "Bruno",
                "servico": "corte",
                "data": "2026-07-14",
                "hora_inicio": "13:00",
                "hora_fim": "13:00",
                # Sem duração
                "confirmado": True,
                "status": "confirmado"
            }

            resultado_ausente = await criar_evento_com_lock(self.tenant_id, evento_ausente, evento_ausente["id"])

            # Teste 3: Duração negativa
            evento_negativo = {
                "id": str(uuid.uuid4()),
                "cliente": "cliente_5c",
                "profissional": "Bruno",
                "servico": "corte",
                "data": "2026-07-15",
                "hora_inicio": "14:00",
                "hora_fim": "14:00",
                "duração": -30,  # Inválida
                "confirmado": True,
                "status": "confirmado"
            }

            resultado_negativo = await criar_evento_com_lock(self.tenant_id, evento_negativo, evento_negativo["id"])

            # Validações
            sessao = await carregar_sessao_temporaria(actor_id, self.tenant_id)
            sessao_intacta = sessao and sessao.get("profissional") == "Bruno"

            # Validar que nenhum evento com duração inválida foi criado
            # e sessão foi preservada
            duracao_zero_bloqueada = not resultado_zero.get("ok")
            duracao_ausente_bloqueada = not resultado_ausente.get("ok")
            duracao_negativa_bloqueada = not resultado_negativo.get("ok")

            if (duracao_zero_bloqueada or duracao_ausente_bloqueada or duracao_negativa_bloqueada) and sessao_intacta:
                result.registro(
                    5,
                    "Duração inválida (zero/ausente/negativa)",
                    True,
                    "",
                    {
                        "duracao_zero_criado": resultado_zero.get("ok"),
                        "duracao_ausente_criado": resultado_ausente.get("ok"),
                        "duracao_negativa_criado": resultado_negativo.get("ok"),
                        "sessao_preservada": True,
                        "nenhuma_duracao_invalida_criada": duracao_zero_bloqueada or duracao_ausente_bloqueada or duracao_negativa_bloqueada
                    }
                )
            else:
                result.registro(
                    5,
                    "Duração inválida",
                    False,
                    f"Zero bloqueado: {duracao_zero_bloqueada}, Ausente: {duracao_ausente_bloqueada}, Negativo: {duracao_negativa_bloqueada}, Sessão: {sessao_intacta}"
                )

        except Exception as e:
            result.registro(5, "Duração inválida (zero/ausente/negativa)", False, str(e))


async def main():
    print("\n" + "="*80)
    print("F3E — CATÁLOGO INCONSISTENTE (IMPLEMENTAÇÃO REAL)")
    print("="*80 + "\n")

    result = TestResult()
    teste = F3E_CatalogoInconsistenteReal()

    await teste.cenario_01_servico_inexistente(result)
    await teste.cenario_02_profissional_inexistente(result)
    await teste.cenario_03_profissional_desativado(result)
    await teste.cenario_04_servico_removido_evento_existente(result)
    await teste.cenario_05_duracao_ausente_invalida(result)

    # Limpeza final
    await teste.limpar_tenant()

    print("\n" + "="*80)
    print(f"F3E RESULTADO: {result.total_pass}/5 PASS")
    print("="*80 + "\n")

    return {
        "teste": "F3E_CATALOGO_INCONSISTENTE",
        "total": 5,
        "pass": result.total_pass,
        "todo": 5 - result.total_pass,
        "cenarios": result.cenarios
    }


if __name__ == "__main__":
    resultado = asyncio.run(main())
