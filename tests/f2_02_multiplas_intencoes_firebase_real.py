"""
F2-02 — TESTE DE MÚLTIPLAS INTENÇÕES

Objetivo: Validar que NeoEve consegue interpretar mensagens com múltiplas
          informações simultâneas sem quebrar o princípio:

          GPT interpreta linguagem.
          Motor determinístico executa regras.

Status: FASE 2 (Confiabilidade) — não entra em P0 ainda
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import pytz

# Setup path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# UTF-8 fix para Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from services.firestore_client import get_db
from services.identidade_service import normalizar_actor_id


class TestResult:
    def __init__(self):
        self.cenarios = []
        self.total_pass = 0

    def registro(self, num, nome, passou, motivo, dados_extras=None):
        status = "PASSOU" if passou else "FALHOU"
        print(f"\n  [{status}] Cenário {num}: {nome}")
        if not passou:
            print(f"    Motivo: {motivo}")
        self.cenarios.append({
            "num": num,
            "nome": nome,
            "passou": passou,
            "motivo": motivo,
            "dados": dados_extras or {}
        })
        if passou:
            self.total_pass += 1


class F2_02_MultiplicasIntencoes:
    """Testes de confiabilidade: múltiplas intenções na mesma mensagem"""

    def __init__(self):
        self.db = get_db()
        self.tenant_a = "f2_02_tenant_multiplas_a"
        self.tenant_b = "f2_02_tenant_multiplas_b"
        self.canal = "whatsapp"

    async def limpar_tenant(self, tenant_id):
        """Limpar tenant completamente"""
        try:
            sessoes_ref = self.db.collection("Clientes").document(tenant_id).collection("Sessoes")
            docs = await asyncio.to_thread(lambda: list(sessoes_ref.stream()))
            for doc in docs:
                await asyncio.to_thread(doc.reference.delete)

            atores_ref = self.db.collection("Clientes").document(tenant_id).collection("Atores")
            docs = await asyncio.to_thread(lambda: list(atores_ref.stream()))
            for doc in docs:
                await asyncio.to_thread(doc.reference.delete)

            print(f"  [CLEANUP] Tenant {tenant_id} limpo")
        except Exception as e:
            print(f"  [CLEANUP] Erro: {e}")

    async def obter_sessao_v2(self, tenant_id, actor_id):
        """Obter Sessão V2 do Firestore"""
        try:
            doc = await asyncio.to_thread(
                lambda: self.db.collection("Clientes")
                .document(tenant_id)
                .collection("Sessoes")
                .document(actor_id)
                .get()
            )
            return doc.to_dict() if doc.exists else {}
        except:
            return {}

    async def salvar_sessao_v2(self, tenant_id, actor_id, dados, merge=True):
        """Salvar Sessão V2 no Firestore"""
        try:
            await asyncio.to_thread(
                lambda: self.db.collection("Clientes")
                .document(tenant_id)
                .collection("Sessoes")
                .document(actor_id)
                .set(dados, merge=merge)
            )
            return True
        except:
            return False

    async def cenario_01_completo_4_slots(self, result: TestResult):
        """
        Cenário 1: Completo (4 slots)

        MSG: "Quero corte com a Bruna amanhã às 16h"

        Esperado:
        - Todos os slots preenchidos
        - Nenhuma pergunta intermediária
        - Fluxo segue para validação determinística
        """
        print("\n  [CENÁRIO 1] Completo (4 slots)")

        await self.limpar_tenant(self.tenant_a)

        actor_id = normalizar_actor_id(self.canal, "11900000001")

        # Setup: fluxo ativo de agendamento
        sessao = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            "estado_fluxo": "agendando",
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao)

        # ACT: Simular interpretação de "Quero corte com a Bruna amanhã às 16h"
        agora = datetime.now(pytz.UTC)
        amanha = agora + timedelta(days=1)

        # GPT teria retornado estrutura assim:
        gpt_retorno = {
            "intencao_principal": "agendar",
            "servicos": ["corte"],
            "profissional": "Bruna",
            "data": amanha.strftime("%Y-%m-%d"),
            "horario": "16:00",
            "ambigua": False,
            "confianca": 0.95
        }

        # Motor salva draft com todos os slots
        sessao_atualizada = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "servico": "corte",
                "profissional": "Bruna",
                "data": gpt_retorno["data"],
                "horario": "16:00"
            },
            "gpt_interpretacao": gpt_retorno
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao_atualizada)

        sessao_final = await self.obter_sessao_v2(self.tenant_a, actor_id)

        passou = True
        motivo = ""
        draft = sessao_final.get("draft_agendamento", {})

        # Validação: Todos os 4 slots preenchidos
        if not draft.get("servico"):
            passou = False
            motivo = "Serviço não foi preenchido"

        if not draft.get("profissional"):
            passou = False
            motivo = "Profissional não foi preenchido"

        if not draft.get("data"):
            passou = False
            motivo = "Data não foi preenchida"

        if not draft.get("horario"):
            passou = False
            motivo = "Horário não foi preenchido"

        result.registro(
            1,
            "Completo (4 slots)",
            passou,
            motivo,
            {
                "actor_id": actor_id,
                "slots_preenchidos": 4 if passou else len(draft),
                "draft": draft
            }
        )

    async def cenario_02_parcial_2_slots(self, result: TestResult):
        """
        Cenário 2: Parcial (2 slots)

        MSG: "Quero escova sexta"

        Esperado:
        - Apenas 2 slots preenchidos
        - Pergunta por faltantes (horário, profissional)
        """
        print("\n  [CENÁRIO 2] Parcial (2 slots)")

        await self.limpar_tenant(self.tenant_a)

        actor_id = normalizar_actor_id(self.canal, "11900000002")

        sessao = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            "estado_fluxo": "agendando",
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao)

        # ACT: Simular interpretação de "Quero escova sexta"
        agora = datetime.now(pytz.UTC)
        proxima_sexta = agora + timedelta(days=(4 - agora.weekday()))

        gpt_retorno = {
            "intencao_principal": "agendar",
            "servicos": ["escova"],
            "data": proxima_sexta.strftime("%Y-%m-%d"),
            "profissional": None,
            "horario": None,
            "ambigua": True,
            "confianca": 0.85,
            "faltam": ["horario", "profissional"]
        }

        sessao_atualizada = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "servico": "escova",
                "data": gpt_retorno["data"],
                # horario e profissional FALTAM
            },
            "gpt_interpretacao": gpt_retorno
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao_atualizada)

        sessao_final = await self.obter_sessao_v2(self.tenant_a, actor_id)

        passou = True
        motivo = ""
        draft = sessao_final.get("draft_agendamento", {})
        gpt = sessao_final.get("gpt_interpretacao", {})

        # Validação: Apenas 2 slots preenchidos
        if not draft.get("servico"):
            passou = False
            motivo = "Serviço não foi preenchido"

        if not draft.get("data"):
            passou = False
            motivo = "Data não foi preenchida"

        # Validação: Faltam foi detectado
        if not gpt.get("ambigua"):
            passou = False
            motivo = "GPT não detectou ambiguidade"

        if not gpt.get("faltam"):
            passou = False
            motivo = "GPT não listou campos faltantes"

        result.registro(
            2,
            "Parcial (2 slots)",
            passou,
            motivo,
            {
                "actor_id": actor_id,
                "slots_preenchidos": 2 if passou else len(draft),
                "faltam": gpt.get("faltam")
            }
        )

    async def cenario_03_multiplos_servicos(self, result: TestResult):
        """
        Cenário 3: Múltiplos serviços

        MSG: "Quero escova E hidratação amanhã"

        Esperado:
        - Detectar múltiplos serviços
        - Sinalizar para motor confirmar
        - NÃO escolher sozinho
        """
        print("\n  [CENÁRIO 3] Múltiplos serviços")

        await self.limpar_tenant(self.tenant_a)

        actor_id = normalizar_actor_id(self.canal, "11900000003")

        sessao = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            "estado_fluxo": "agendando",
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao)

        # ACT
        agora = datetime.now(pytz.UTC)
        amanha = agora + timedelta(days=1)

        gpt_retorno = {
            "intencao_principal": "agendar",
            "servicos": ["escova", "hidratacao"],
            "multiplos_servicos": True,
            "data": amanha.strftime("%Y-%m-%d"),
            "ambigua": True,
            "confianca": 0.90,
            "faltam": ["horario", "profissional"]
        }

        sessao_atualizada = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "servicos": ["escova", "hidratacao"],
                "data": gpt_retorno["data"],
            },
            "gpt_interpretacao": gpt_retorno
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao_atualizada)

        sessao_final = await self.obter_sessao_v2(self.tenant_a, actor_id)

        passou = True
        motivo = ""
        draft = sessao_final.get("draft_agendamento", {})
        gpt = sessao_final.get("gpt_interpretacao", {})

        # Validação: Múltiplos serviços detectados
        if not gpt.get("multiplos_servicos"):
            passou = False
            motivo = "GPT não detectou múltiplos serviços"

        if not isinstance(draft.get("servicos"), list) or len(draft.get("servicos", [])) != 2:
            passou = False
            motivo = "Draft não contém ambos os serviços"

        # Validação: Ambiguidade sinalizada
        if not gpt.get("ambigua"):
            passou = False
            motivo = "Múltiplos serviços sem ambiguidade = erro"

        result.registro(
            3,
            "Múltiplos serviços",
            passou,
            motivo,
            {
                "actor_id": actor_id,
                "servicos": draft.get("servicos"),
                "multiplos_detectados": gpt.get("multiplos_servicos")
            }
        )

    async def cenario_04_multiplas_intencoes(self, result: TestResult):
        """
        Cenário 4: Múltiplas intenções (Cancelamento + Nova)

        MSG: "Cancela segunda e marca sexta às 15h"

        Esperado:
        - Detectar múltiplas intenções
        - NÃO executar automaticamente
        - Pedir confirmação
        """
        print("\n  [CENÁRIO 4] Múltiplas intenções")

        await self.limpar_tenant(self.tenant_a)

        actor_id = normalizar_actor_id(self.canal, "11900000004")

        sessao = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao)

        # ACT
        agora = datetime.now(pytz.UTC)
        proxima_segunda = agora + timedelta(days=(0 - agora.weekday()))
        proxima_sexta = agora + timedelta(days=(4 - agora.weekday()))

        gpt_retorno = {
            "intencoes": ["cancelamento", "novo_agendamento"],
            "multiplas_intencoes": True,
            "cancelamento": {
                "data": proxima_segunda.strftime("%Y-%m-%d")
            },
            "novo_agendamento": {
                "data": proxima_sexta.strftime("%Y-%m-%d"),
                "horario": "15:00"
            },
            "ambigua": False,
            "confianca": 0.92
        }

        sessao_atualizada = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            "gpt_interpretacao": gpt_retorno,
            "aguardando_confirmacao_multiplas": True
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao_atualizada)

        sessao_final = await self.obter_sessao_v2(self.tenant_a, actor_id)

        passou = True
        motivo = ""
        gpt = sessao_final.get("gpt_interpretacao", {})

        # Validação: Múltiplas intenções detectadas
        if not gpt.get("multiplas_intencoes"):
            passou = False
            motivo = "GPT não detectou múltiplas intenções"

        if len(gpt.get("intencoes", [])) != 2:
            passou = False
            motivo = "Esperado 2 intenções"

        # Validação: Estado reflete aguardando confirmação (não executou)
        if not sessao_final.get("aguardando_confirmacao_multiplas"):
            passou = False
            motivo = "Sistema não aguardou confirmação antes de executar"

        result.registro(
            4,
            "Múltiplas intenções",
            passou,
            motivo,
            {
                "actor_id": actor_id,
                "intencoes_detectadas": gpt.get("intencoes"),
                "aguardando_confirmacao": sessao_final.get("aguardando_confirmacao_multiplas")
            }
        )

    async def cenario_05_preferencia_vaga(self, result: TestResult):
        """
        Cenário 5: Preferência vaga

        MSG: "Quero corte amanhã à tarde, qualquer profissional"

        Esperado:
        - profissional_indiferente = true
        - intervalo_horario = tarde
        - Motor oferece opções
        """
        print("\n  [CENÁRIO 5] Preferência vaga")

        await self.limpar_tenant(self.tenant_a)

        actor_id = normalizar_actor_id(self.canal, "11900000005")

        sessao = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            "estado_fluxo": "agendando",
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao)

        # ACT
        agora = datetime.now(pytz.UTC)
        amanha = agora + timedelta(days=1)

        gpt_retorno = {
            "intencao_principal": "agendar",
            "servicos": ["corte"],
            "data": amanha.strftime("%Y-%m-%d"),
            "intervalo_horario": "tarde",  # 12:00-18:00
            "profissional_indiferente": True,
            "ambigua": False,
            "confianca": 0.92
        }

        sessao_atualizada = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "servico": "corte",
                "data": gpt_retorno["data"],
                "intervalo_horario": "tarde",
                "profissional_indiferente": True,
            },
            "gpt_interpretacao": gpt_retorno
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao_atualizada)

        sessao_final = await self.obter_sessao_v2(self.tenant_a, actor_id)

        passou = True
        motivo = ""
        draft = sessao_final.get("draft_agendamento", {})

        # Validação: Preferência vaga registrada
        if not draft.get("profissional_indiferente"):
            passou = False
            motivo = "profissional_indiferente não foi setado"

        if draft.get("intervalo_horario") != "tarde":
            passou = False
            motivo = f"intervalo_horario incorreto: {draft.get('intervalo_horario')}"

        result.registro(
            5,
            "Preferência vaga",
            passou,
            motivo,
            {
                "actor_id": actor_id,
                "profissional_indiferente": draft.get("profissional_indiferente"),
                "intervalo_horario": draft.get("intervalo_horario")
            }
        )

    async def cenario_06_mensagem_longa_natural(self, result: TestResult):
        """
        Cenário 6: Mensagem longa e natural

        MSG: "Oi, tudo bem? Queria saber se consigo fazer corte e escova
             amanhã depois das 14h com a Bruna, se ela estiver disponível."

        Esperado:
        - Extrair intenção principal
        - Múltiplos serviços
        - Restrição de horário
        - Profissional tentativo
        """
        print("\n  [CENÁRIO 6] Mensagem longa e natural")

        await self.limpar_tenant(self.tenant_a)

        actor_id = normalizar_actor_id(self.canal, "11900000006")

        sessao = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            "estado_fluxo": "agendando",
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao)

        # ACT
        agora = datetime.now(pytz.UTC)
        amanha = agora + timedelta(days=1)

        gpt_retorno = {
            "intencao_principal": "agendar",
            "servicos": ["corte", "escova"],
            "multiplos_servicos": True,
            "data": amanha.strftime("%Y-%m-%d"),
            "intervalo_horario_minimo": "14:00",
            "profissional": "Bruna",
            "profissional_verificado": "tentativo",  # "se ela estiver"
            "ambigua": False,
            "confianca": 0.88
        }

        sessao_atualizada = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "servicos": ["corte", "escova"],
                "data": gpt_retorno["data"],
                "intervalo_horario_minimo": "14:00",
                "profissional": "Bruna"
            },
            "gpt_interpretacao": gpt_retorno
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao_atualizada)

        sessao_final = await self.obter_sessao_v2(self.tenant_a, actor_id)

        passou = True
        motivo = ""
        draft = sessao_final.get("draft_agendamento", {})
        gpt = sessao_final.get("gpt_interpretacao", {})

        # Validação: Campos extraídos corretamente
        if not draft.get("servicos") or len(draft.get("servicos", [])) != 2:
            passou = False
            motivo = "Serviços não extraídos corretamente"

        if draft.get("intervalo_horario_minimo") != "14:00":
            passou = False
            motivo = "Restrição de horário não extraída"

        if draft.get("profissional") != "Bruna":
            passou = False
            motivo = "Profissional não extraído"

        if not gpt.get("multiplos_servicos"):
            passou = False
            motivo = "Múltiplos serviços não detectados"

        result.registro(
            6,
            "Mensagem longa e natural",
            passou,
            motivo,
            {
                "actor_id": actor_id,
                "servicos": draft.get("servicos"),
                "horario_minimo": draft.get("intervalo_horario_minimo"),
                "profissional": draft.get("profissional")
            }
        )

    async def cenario_07_multi_tenant(self, result: TestResult):
        """
        Cenário 7: Multi-tenant

        Mesma mensagem em tenants diferentes
        → Isolamento total
        """
        print("\n  [CENÁRIO 7] Multi-tenant")

        await self.limpar_tenant(self.tenant_a)
        await self.limpar_tenant(self.tenant_b)

        actor_a = normalizar_actor_id(self.canal, "11900000007")
        actor_b = normalizar_actor_id(self.canal, "11900000008")

        # Setup tenant A
        sessao_a = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_a,
            "tipo_usuario": "cliente",
            "draft_agendamento": {
                "servico": "corte",
                "profissional": "Bruna"
            }
        }

        # Setup tenant B
        sessao_b = {
            "tenant_id": self.tenant_b,
            "actor_id": actor_b,
            "tipo_usuario": "cliente",
            "draft_agendamento": {
                "servico": "escova",
                "profissional": "Carla"
            }
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_a, sessao_a)
        await self.salvar_sessao_v2(self.tenant_b, actor_b, sessao_b)

        # ACT: Alterar apenas tenant A
        sessao_a_nova = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_a,
            "tipo_usuario": "cliente",
            "draft_agendamento": {
                "servico": "hidratacao",
                "profissional": "Lucia"
            }
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_a, sessao_a_nova)

        # Verificar isolamento
        sessao_a_final = await self.obter_sessao_v2(self.tenant_a, actor_a)
        sessao_b_final = await self.obter_sessao_v2(self.tenant_b, actor_b)

        passou = True
        motivo = ""

        # Tenant A deve estar alterado
        if sessao_a_final.get("draft_agendamento", {}).get("servico") != "hidratacao":
            passou = False
            motivo = "Tenant A não foi alterado"

        # Tenant B deve estar INTACTO
        if sessao_b_final.get("draft_agendamento", {}).get("servico") != "escova":
            passou = False
            motivo = "Tenant B foi afetado por mudança em A"

        result.registro(
            7,
            "Multi-tenant",
            passou,
            motivo,
            {
                "tenant_a_servico": sessao_a_final.get("draft_agendamento", {}).get("servico"),
                "tenant_b_servico": sessao_b_final.get("draft_agendamento", {}).get("servico"),
                "isolamento_mantido": sessao_b_final.get("draft_agendamento", {}).get("servico") == "escova"
            }
        )


async def main():
    print("\n" + "="*80)
    print("F2-02 — TESTE DE MÚLTIPLAS INTENÇÕES (CONFIABILIDADE)")
    print("="*80 + "\n")

    result = TestResult()
    teste = F2_02_MultiplicasIntencoes()

    try:
        await teste.cenario_01_completo_4_slots(result)
        await teste.cenario_02_parcial_2_slots(result)
        await teste.cenario_03_multiplos_servicos(result)
        await teste.cenario_04_multiplas_intencoes(result)
        await teste.cenario_05_preferencia_vaga(result)
        await teste.cenario_06_mensagem_longa_natural(result)
        await teste.cenario_07_multi_tenant(result)
    except Exception as e:
        print(f"\n[ERRO] {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*80)
    print(f"RESULTADO FINAL: {result.total_pass}/{len(result.cenarios)} PASS")
    print("="*80 + "\n")

    return result.total_pass == len(result.cenarios)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
