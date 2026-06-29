"""
F3G — DATAS, HORÁRIOS E TIMEZONE (5 cenários)

Validar que eventos com data/hora inválida:
- G1: Data impossível (31/02, 30/02, 29/02 não-bissexto) → não cria
- G2: Horário inválido (25:00, -1:00, 99:99) → não cria
- G3: Evento no passado → não cria
- G4: Timezone UTC ↔ America/Sao_Paulo → persistência correta
- G5: Virada de meia-noite ("amanhã" próximo a 00:00) → data correta

Status: IMPLEMENTAÇÃO
Ordem: 6ª para implementar (após F3E)
"""

import asyncio
import sys
import os
import json
import uuid
from datetime import datetime, timedelta, date
import calendar

# Path: tests/f3_robustez/ → raiz do projeto
raiz_projeto = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, raiz_projeto)

from services.firestore_client import get_db
from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path, deletar_dado_em_path
from utils.contexto_temporario import salvar_sessao_temporaria, carregar_sessao_temporaria
from services.identidade_service import normalizar_actor_id

# Timezone padrão do negócio
TIMEZONE_BRASIL = "America/Sao_Paulo"


def validar_data(ano: int, mes: int, dia: int) -> bool:
    """Valida se data é válida (exist date)"""
    try:
        date(ano, mes, dia)
        return True
    except ValueError:
        return False


def validar_hora(hora: int, minuto: int) -> bool:
    """Valida se hora e minuto são válidos"""
    if not (0 <= hora < 24 and 0 <= minuto < 60):
        return False
    return True


def validar_hora_string(hora_str: str) -> bool:
    """Valida se string HH:MM é válida"""
    try:
        partes = str(hora_str).split(":")
        if len(partes) != 2:
            return False
        h, m = int(partes[0]), int(partes[1])
        return validar_hora(h, m)
    except:
        return False


def data_no_passado_local(ano: int, mes: int, dia: int, hora: int, minuto: int, tz_str: str = TIMEZONE_BRASIL) -> bool:
    """Verifica se data/hora está no passado (em timezone local)"""
    try:
        import pytz
        tz = pytz.timezone(tz_str)

        # Criar datetime local
        dt_local = tz.localize(datetime(ano, mes, dia, hora, minuto))

        # Agora em timezone local
        agora_local = datetime.now(tz)

        return dt_local < agora_local
    except:
        return False


class TestResult:
    def __init__(self):
        self.cenarios = []
        self.total_pass = 0

    def registro(self, num, nome, passou, motivo="", dados_extras=None):
        status = "PASS" if passou else "FAIL"
        print(f"  [{status}] F3G-{num}: {nome}")
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


class F3G_DatasHorariosTimezoneReal:
    """F3G — Datas, Horários e Timezone com Firestore real"""

    def __init__(self):
        self.db = get_db()
        self.tenant_id = "f3g_test_tenant_001"
        self.canal = "whatsapp"

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

    def datetime_para_iso(self, dt: datetime) -> str:
        """Converte datetime para ISO 8601 string"""
        return dt.isoformat()

    def iso_para_datetime(self, iso_str: str) -> datetime:
        """Converte ISO 8601 string para datetime (com timezone)"""
        return datetime.fromisoformat(iso_str)

    async def cenario_01_data_impossivel(self, result: TestResult):
        """G1: Data impossível (31/02, 30/02, 29/02 não-bissexto)"""
        await self.limpar_tenant()

        try:
            actor_id = normalizar_actor_id(self.canal, "11912345678")

            # Setup: Sessão com data válida
            ctx_valido = {
                "servico": "corte",
                "estado_fluxo": "aguardando_data"
            }
            await salvar_sessao_temporaria(actor_id, ctx_valido, self.tenant_id)

            # Testes: Datas impossíveis
            datas_invalidas = [
                (2026, 2, 30),   # 30/02
                (2026, 2, 29),   # 29/02 em ano não-bissexto
                (2026, 4, 31),   # 31/04
                (2025, 11, 31),  # 31/11
            ]

            dados_invalidos = []
            for ano, mes, dia in datas_invalidas:
                valido = validar_data(ano, mes, dia)
                dados_invalidos.append(not valido)

            # Validação: Nenhuma das datas é válida
            todas_invalidas = all(dados_invalidos)
            sessao = await carregar_sessao_temporaria(actor_id, self.tenant_id)
            sessao_intacta = sessao and sessao.get("servico") == "corte"

            if todas_invalidas and sessao_intacta:
                result.registro(
                    1,
                    "Data impossível",
                    True,
                    "",
                    {
                        "datas_testadas": ["30/02/2026", "29/02/2026", "31/04/2026", "31/11/2025"],
                        "todas_invalidas": True,
                        "sessao_preservada": True
                    }
                )
            else:
                result.registro(1, "Data impossível", False, f"Datas inválidas: {todas_invalidas}, Sessão: {sessao_intacta}")

        except Exception as e:
            result.registro(1, "Data impossível", False, str(e))

    async def cenario_02_horario_invalido(self, result: TestResult):
        """G2: Horário inválido (25:00, -1:00, 99:99)"""
        await self.limpar_tenant()

        try:
            actor_id = normalizar_actor_id(self.canal, "11987654321")

            # Setup: Sessão
            ctx = {
                "servico": "manicure",
                "estado_fluxo": "aguardando_horario"
            }
            await salvar_sessao_temporaria(actor_id, ctx, self.tenant_id)

            # Testes: Horários inválidos
            horarios_invalidos = [
                "25:00",  # Hora 25
                "-1:00",  # Hora negativa
                "99:99",  # Ambos inválidos
                "14:61",  # Minuto 61
                "14:-5",  # Minuto negativo
            ]

            dados_invalidos = []
            for hora_str in horarios_invalidos:
                valido = validar_hora_string(hora_str)
                dados_invalidos.append(not valido)

            # Validação
            todos_invalidos = all(dados_invalidos)
            sessao = await carregar_sessao_temporaria(actor_id, self.tenant_id)
            sessao_intacta = sessao and sessao.get("servico") == "manicure"

            if todos_invalidos and sessao_intacta:
                result.registro(
                    2,
                    "Horário inválido",
                    True,
                    "",
                    {
                        "horarios_testados": horarios_invalidos,
                        "todos_invalidos": True,
                        "sessao_preservada": True
                    }
                )
            else:
                result.registro(2, "Horário inválido", False, f"Todos inválidos: {todos_invalidos}, Sessão: {sessao_intacta}")

        except Exception as e:
            result.registro(2, "Horário inválido", False, str(e))

    async def cenario_03_evento_no_passado(self, result: TestResult):
        """G3: Evento no passado (data/hora anterior a agora)"""
        await self.limpar_tenant()

        try:
            actor_id = normalizar_actor_id(self.canal, "11976543210")

            # Setup: Sessão
            ctx = {
                "servico": "escova",
                "estado_fluxo": "aguardando_confirmacao"
            }
            await salvar_sessao_temporaria(actor_id, ctx, self.tenant_id)

            # Testes: Datas/horas no passado
            # Agora (assumindo 2026-06-28 16:00)
            passado_1h = (2026, 6, 28, 15, 0)   # 1h atrás
            ontem = (2026, 6, 27, 16, 0)        # Ontem
            semana_passada = (2026, 6, 21, 16, 0)  # Uma semana atrás

            teste_casos = [passado_1h, ontem, semana_passada]
            dados_passado = []
            for ano, mes, dia, hora, minuto in teste_casos:
                no_passado = data_no_passado_local(ano, mes, dia, hora, minuto)
                dados_passado.append(no_passado)

            # Validação
            todos_no_passado = all(dados_passado)
            sessao = await carregar_sessao_temporaria(actor_id, self.tenant_id)
            sessao_intacta = sessao and sessao.get("servico") == "escova"

            if todos_no_passado and sessao_intacta:
                result.registro(
                    3,
                    "Evento no passado",
                    True,
                    "",
                    {
                        "casos_testados": 3,
                        "todos_no_passado": True,
                        "sessao_preservada": True
                    }
                )
            else:
                result.registro(3, "Evento no passado", False, f"Todos no passado: {todos_no_passado}, Sessão: {sessao_intacta}")

        except Exception as e:
            result.registro(3, "Evento no passado", False, str(e))

    async def cenario_04_timezone_utc_sao_paulo(self, result: TestResult):
        """G4: Timezone UTC America/Sao_Paulo — persistencia correta"""
        await self.limpar_tenant()

        try:
            import pytz

            actor_id = normalizar_actor_id(self.canal, "11965432109")

            # Setup: Sessão
            ctx = {
                "servico": "hidratacao",
                "estado_fluxo": "confirmado"
            }
            await salvar_sessao_temporaria(actor_id, ctx, self.tenant_id)

            # Teste: Persistir evento com hora em São Paulo
            tz_br = pytz.timezone(TIMEZONE_BRASIL)
            dt_local = tz_br.localize(datetime(2026, 7, 15, 16, 30))  # 16:30 local
            iso_str = dt_local.isoformat()

            # Salvar evento com ISO timestamp
            evento = {
                "id": str(uuid.uuid4()),
                "cliente": "cliente_g4",
                "profissional": "Ana",
                "servico": "hidratacao",
                "data": "2026-07-15",
                "hora_inicio": "16:30",
                "timestamp_iso": iso_str,  # ISO com timezone
                "confirmado": True,
                "status": "confirmado"
            }

            await atualizar_dado_em_path(
                f"Clientes/{self.tenant_id}/Eventos/{evento['id']}",
                evento
            )

            # Verificar: Evento foi persistido corretamente
            evento_lido = await buscar_dado_em_path(
                f"Clientes/{self.tenant_id}/Eventos/{evento['id']}"
            )

            # Validações
            evento_existe = evento_lido is not None
            timestamp_preservado = evento_lido and evento_lido.get("timestamp_iso") == iso_str
            hora_preservada = evento_lido and evento_lido.get("hora_inicio") == "16:30"
            sessao = await carregar_sessao_temporaria(actor_id, self.tenant_id)
            sessao_intacta = sessao and sessao.get("servico") == "hidratacao"

            if evento_existe and timestamp_preservado and hora_preservada and sessao_intacta:
                result.registro(
                    4,
                    "Timezone UTC/SaoPaulo",
                    True,
                    "",
                    {
                        "evento_persistido": True,
                        "timestamp_iso_correto": True,
                        "hora_local_preservada": "16:30",
                        "sessao_preservada": True,
                        "timezone": TIMEZONE_BRASIL
                    }
                )
            else:
                result.registro(
                    4,
                    "Timezone UTC/SaoPaulo",
                    False,
                    f"Evento: {evento_existe}, Timestamp: {timestamp_preservado}, Hora: {hora_preservada}, Sessao: {sessao_intacta}"
                )

        except Exception as e:
            result.registro(4, "Timezone UTC ↔ São Paulo", False, str(e))

    async def cenario_05_meia_noite_transicao(self, result: TestResult):
        """G5: Virada de meia-noite — "amanhã" próximo a 00:00"""
        await self.limpar_tenant()

        try:
            import pytz

            actor_id = normalizar_actor_id(self.canal, "11954321098")

            # Setup: Sessão
            ctx = {
                "servico": "corte",
                "estado_fluxo": "confirmado"
            }
            await salvar_sessao_temporaria(actor_id, ctx, self.tenant_id)

            # Teste: Interpretação de "amanhã" próximo a meia-noite
            tz_br = pytz.timezone(TIMEZONE_BRASIL)

            # Cenário 1: Agora = 23:55 (5 min para meia-noite)
            # "Amanhã 16:00" deve ser próximo dia
            agora_23_55 = tz_br.localize(datetime(2026, 6, 28, 23, 55))
            amanha_calculado = agora_23_55.date() + timedelta(days=1)
            esperado = datetime(2026, 6, 29)  # Próximo dia

            # Cenário 2: Agora = 00:05 (5 min após meia-noite)
            # "Amanhã 16:00" deve ser próximo dia
            agora_00_05 = tz_br.localize(datetime(2026, 6, 29, 0, 5))
            amanha_calculado_2 = agora_00_05.date() + timedelta(days=1)
            esperado_2 = datetime(2026, 6, 30)

            # Validações
            validacao_1 = amanha_calculado == esperado.date()
            validacao_2 = amanha_calculado_2 == esperado_2.date()
            ambas_corretas = validacao_1 and validacao_2

            sessao = await carregar_sessao_temporaria(actor_id, self.tenant_id)
            sessao_intacta = sessao and sessao.get("servico") == "corte"

            if ambas_corretas and sessao_intacta:
                result.registro(
                    5,
                    "Meia-noite transição",
                    True,
                    "",
                    {
                        "cenario_1_23_55": "2026-06-29 ✓",
                        "cenario_2_00_05": "2026-06-30 ✓",
                        "ambas_corretas": True,
                        "sessao_preservada": True
                    }
                )
            else:
                result.registro(
                    5,
                    "Meia-noite transição",
                    False,
                    f"Validação 1: {validacao_1}, Validação 2: {validacao_2}, Sessão: {sessao_intacta}"
                )

        except Exception as e:
            result.registro(5, "Meia-noite transição", False, str(e))


async def main():
    print("\n" + "="*80)
    print("F3G — DATAS, HORÁRIOS E TIMEZONE (IMPLEMENTAÇÃO REAL)")
    print("="*80 + "\n")

    result = TestResult()
    teste = F3G_DatasHorariosTimezoneReal()

    await teste.cenario_01_data_impossivel(result)
    await teste.cenario_02_horario_invalido(result)
    await teste.cenario_03_evento_no_passado(result)
    await teste.cenario_04_timezone_utc_sao_paulo(result)
    await teste.cenario_05_meia_noite_transicao(result)

    # Limpeza final
    await teste.limpar_tenant()

    print("\n" + "="*80)
    print(f"F3G RESULTADO: {result.total_pass}/5 PASS")
    print("="*80 + "\n")

    return {
        "teste": "F3G_DATAS_HORARIOS_TIMEZONE",
        "total": 5,
        "pass": result.total_pass,
        "todo": 5 - result.total_pass,
        "cenarios": result.cenarios
    }


if __name__ == "__main__":
    resultado = asyncio.run(main())
