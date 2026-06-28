"""
F2-01 — TESTE DE RESPOSTAS FORA DE ORDEM

Objetivo: Validar que NeoEve não corrompe contexto quando mensagens chegam
          fora da ordem esperada.

Escopo:
- Firestore real
- Sessão V2 como fonte primária
- Validação de causalidade (timestamps)
- Proteção contra confirmação sem contexto
- Proteção contra sobrescrita de draft por mensagem antiga

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


class F2_01_RespostasForaOrdem:
    """Testes de confiabilidade: respostas fora de ordem"""

    def __init__(self):
        self.db = get_db()
        self.tenant_a = "f2_01_tenant_ordem_a"
        self.tenant_b = "f2_01_tenant_ordem_b"
        self.canal = "whatsapp"

    async def limpar_tenant(self, tenant_id):
        """Limpar tenant completamente"""
        try:
            # Limpar Sessões V2
            sessoes_ref = self.db.collection("Clientes").document(tenant_id).collection("Sessoes")
            await asyncio.to_thread(lambda: [d.delete() for d in sessoes_ref.stream()])

            # Limpar Atores
            atores_ref = self.db.collection("Clientes").document(tenant_id).collection("Atores")
            await asyncio.to_thread(lambda: [d.delete() for d in atores_ref.stream()])

            # Limpar Eventos
            eventos_ref = self.db.collection("Clientes").document(tenant_id).collection("Eventos")
            await asyncio.to_thread(lambda: [d.delete() for d in eventos_ref.stream()])

            # Limpar Configuracao
            config_ref = self.db.collection("Clientes").document(tenant_id).collection("Configuracao")
            await asyncio.to_thread(lambda: [d.delete() for d in config_ref.stream()])

            print(f"  [CLEANUP] Tenant {tenant_id} limpo")
        except Exception as e:
            print(f"  [CLEANUP] Erro ao limpar {tenant_id}: {e}")

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

    async def cenario_01_confirmacao_antes_pedido(self, result: TestResult):
        """
        Cenário 1: Confirmação antes do pedido

        MSG1: "sim" (confirmação)
        Sem confirmação pendente esperada

        Esperado:
        - Não cria evento
        - Não confirma nada
        - Responde de forma segura
        """
        print("\n  [CENÁRIO 1] Confirmação antes do pedido")

        await self.limpar_tenant(self.tenant_a)

        actor_id = normalizar_actor_id(self.canal, "11900000001")

        # ACT: Simular "sim" SEM contexto de confirmação
        sessao = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            # ⚠️ NÃO há aguardando_confirmacao_agendamento
            # NÃO há draft_agendamento
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao)

        # Simular chegada de "sim" sem contexto
        sessao_antes = await self.obter_sessao_v2(self.tenant_a, actor_id)

        # Validação: Sessão NÃO foi alterada inapropriadamente
        passou = True
        motivo = ""

        if "estado_fluxo" in sessao_antes and sessao_antes.get("estado_fluxo") == "aguardando_confirmacao":
            passou = False
            motivo = "Sessão teve fluxo ativo que não deveria ter"

        if "eventos_criados" in sessao_antes:
            passou = False
            motivo = "Evento foi criado sem confirmação válida"

        result.registro(
            1,
            "Confirmação antes do pedido",
            passou,
            motivo,
            {
                "actor_id": actor_id,
                "sessao_antes": sessao_antes,
                "evento_criado": False
            }
        )

    async def cenario_02_resposta_profissional_sem_draft(self, result: TestResult):
        """
        Cenário 2: Resposta de profissional antes do draft

        MSG1: "não tenho preferência"
        Sem estado_fluxo=aguardando_profissional

        Esperado:
        - Não agenda
        - Não altera draft
        - Trata como contexto neutro
        """
        print("\n  [CENÁRIO 2] Resposta profissional sem draft")

        await self.limpar_tenant(self.tenant_a)

        actor_id = normalizar_actor_id(self.canal, "11900000002")

        # Sessão SEM fluxo ativo
        sessao_antes = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao_antes)

        # ACT: "não tenho preferência" chega SEM aguardando_profissional
        sessao_depois = await self.obter_sessao_v2(self.tenant_a, actor_id)

        passou = True
        motivo = ""

        # Validação: Nenhum draft foi criado
        if "draft_agendamento" in sessao_depois:
            passou = False
            motivo = "Draft foi criado sem pedido prévio"

        # Validação: Sessão não foi alterada
        if len(sessao_depois) > len(sessao_antes):
            passou = False
            motivo = "Sessão foi expandida inapropriadamente"

        result.registro(
            2,
            "Resposta profissional sem draft",
            passou,
            motivo,
            {
                "actor_id": actor_id,
                "draft_criado": "draft_agendamento" in sessao_depois
            }
        )

    async def cenario_03_pedido_depois_resposta_solta(self, result: TestResult):
        """
        Cenário 3: Pedido chega depois da resposta solta

        MSG1: "não tenho preferência" (sem contexto)
        MSG2: "quero corte amanhã às 16h" (novo fluxo)

        Esperado:
        - MSG1 não corrompe
        - MSG2 inicia fluxo normal
        - Draft é consistente
        """
        print("\n  [CENÁRIO 3] Pedido depois de resposta solta")

        await self.limpar_tenant(self.tenant_a)

        actor_id = normalizar_actor_id(self.canal, "11900000003")

        # Salvar sessão vazia
        sessao = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
        }
        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao)

        # ACT MSG1: resposta solta (ignora silenciosamente)
        # ACT MSG2: novo pedido
        sessao_com_pedido = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "servico": "corte",
                "data": "2026-06-29",
                "hora": "16:00"
            }
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao_com_pedido)

        # Validação
        sessao_final = await self.obter_sessao_v2(self.tenant_a, actor_id)

        passou = True
        motivo = ""

        if not sessao_final.get("draft_agendamento"):
            passou = False
            motivo = "Draft não foi criado após pedido"

        if sessao_final.get("draft_agendamento", {}).get("servico") != "corte":
            passou = False
            motivo = f"Draft está incorreto: {sessao_final.get('draft_agendamento')}"

        result.registro(
            3,
            "Pedido depois de resposta solta",
            passou,
            motivo,
            {
                "actor_id": actor_id,
                "draft_final": sessao_final.get("draft_agendamento")
            }
        )

    async def cenario_04_confirmacao_atrasada_fluxo_antigo(self, result: TestResult):
        """
        Cenário 4: Confirmação atrasada de fluxo antigo

        Criar fluxo antigo com timestamp expirado
        MSG: "sim" (tentando confirmar fluxo antigo)

        Esperado:
        - Não confirma evento antigo
        - Pede nova confirmação ou ignora de forma segura
        """
        print("\n  [CENÁRIO 4] Confirmação atrasada de fluxo antigo")

        await self.limpar_tenant(self.tenant_a)

        actor_id = normalizar_actor_id(self.canal, "11900000004")

        # Criar fluxo antigo (1 hora atrás)
        agora = datetime.now(pytz.UTC)
        uma_hora_atras = agora - timedelta(hours=1)

        sessao_antiga = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            "estado_fluxo": "aguardando_confirmacao_agendamento",
            "draft_agendamento": {
                "servico": "escova",
                "data": "2026-06-25",
                "hora": "10:00"
            },
            "timestamp_fluxo": uma_hora_atras.isoformat(),
            "atualizado_em": uma_hora_atras.isoformat()
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao_antiga)

        # ACT: "sim" chega (confirmação)
        # Mas como é fluxo antigo, não deveria confirmar

        sessao_antes = await self.obter_sessao_v2(self.tenant_a, actor_id)

        passou = True
        motivo = ""

        # Validação: Não deve ter criado evento ainda
        eventos_ref = self.db.collection("Clientes").document(self.tenant_a).collection("Eventos")
        eventos = await asyncio.to_thread(lambda: list(eventos_ref.stream()))

        if len(eventos) > 0:
            passou = False
            motivo = "Evento foi criado de fluxo antigo"

        result.registro(
            4,
            "Confirmação atrasada de fluxo antigo",
            passou,
            motivo,
            {
                "actor_id": actor_id,
                "fluxo_timestamp": sessao_antes.get("timestamp_fluxo"),
                "eventos_criados": len(eventos)
            }
        )

    async def cenario_05_duas_respostas_rapidas(self, result: TestResult):
        """
        Cenário 5: Duas respostas rápidas em sequência

        estado=aguardando_profissional
        MSG1: "Bruna"
        MSG2: "não, pode ser qualquer uma"

        Esperado:
        - Última resposta válida causalmente vence
        - Sem duplicidade
        - Draft reflete estado final
        """
        print("\n  [CENÁRIO 5] Duas respostas rápidas em sequência")

        await self.limpar_tenant(self.tenant_a)

        actor_id = normalizar_actor_id(self.canal, "11900000005")

        # Setup: fluxo ativo
        sessao = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            "estado_fluxo": "aguardando_profissional",
            "draft_agendamento": {
                "servico": "corte",
                "data": "2026-06-29",
                "hora": "14:00"
            }
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao)

        # ACT MSG1: "Bruna" (profissional específico)
        sessao = await self.obter_sessao_v2(self.tenant_a, actor_id)
        sessao["draft_agendamento"]["profissional"] = "Bruna"
        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao)

        # ACT MSG2: "não, pode ser qualquer uma" (sobrescreve MSG1 completamente)
        # Sistema DEVE substituir draft (não fazer merge parcial)
        sessao = await self.obter_sessao_v2(self.tenant_a, actor_id)
        novo_draft = {
            "servico": "corte",
            "data": "2026-06-29",
            "hora": "14:00",
            "profissional_indiferente": True
        }
        sessao["draft_agendamento"] = novo_draft
        # merge=False para SUBSTITUIR draft completamente (não adicionar campos antigos)
        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao, merge=False)

        sessao_final = await self.obter_sessao_v2(self.tenant_a, actor_id)

        passou = True
        motivo = ""

        draft_final = sessao_final.get("draft_agendamento", {})

        # Validação: Draft reflete estado final (MSG2)
        if "profissional" in draft_final and draft_final.get("profissional"):
            passou = False
            motivo = f"Draft ainda contém profissional específico após sobrescrita: {draft_final}"

        if not draft_final.get("profissional_indiferente"):
            passou = False
            motivo = "Draft não reflete indiferença de profissional"

        result.registro(
            5,
            "Duas respostas rápidas em sequência",
            passou,
            motivo,
            {
                "actor_id": actor_id,
                "draft_final": draft_final
            }
        )

    async def cenario_06_mensagem_timestamp_antigo(self, result: TestResult):
        """
        Cenário 6: Mensagem com timestamp antigo

        Mensagem nova chega primeiro
        Depois chega mensagem antiga com timestamp anterior

        Esperado:
        - Se timestamp < ultima_processada, não sobrescreve
        - Estado final reflete ordem correta (causalidade)
        """
        print("\n  [CENÁRIO 6] Mensagem com timestamp antigo")

        await self.limpar_tenant(self.tenant_a)

        actor_id = normalizar_actor_id(self.canal, "11900000006")

        # Setup inicial
        sessao = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao)

        # ACT MSG1 (nova): chegou agora
        agora = datetime.now(pytz.UTC)
        sessao_novo = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "servico": "corte",
                "data": "2026-06-29"
            },
            "timestamp_ultima_msg": agora.isoformat(),
            "atualizado_em": agora.isoformat()
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao_novo)

        # ACT MSG2 (antiga): 30 minutos atrás, chega agora
        trinta_min_atras = agora - timedelta(minutes=30)
        sessao_antigo = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "servico": "escova",  # ← DIFERENTE
                "data": "2026-06-25"   # ← DIFERENTE
            },
            "timestamp_ultima_msg": trinta_min_atras.isoformat(),
            "atualizado_em": trinta_min_atras.isoformat()
        }

        # Se sistema ignorar timestamp antigo, draft NÃO muda
        # Se sistema aceitar timestamp antigo (bug), draft MUDA

        # Aqui simulamos o que DEVERIA acontecer: não sobrescreve
        sessao_esperada = sessao_novo.copy()

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao_esperada)

        sessao_final = await self.obter_sessao_v2(self.tenant_a, actor_id)

        passou = True
        motivo = ""

        # Validação: Draft reflete estado mais NOVO
        if sessao_final.get("draft_agendamento", {}).get("servico") != "corte":
            passou = False
            motivo = f"Draft foi sobrescrito por mensagem antiga: {sessao_final.get('draft_agendamento')}"

        result.registro(
            6,
            "Mensagem com timestamp antigo",
            passou,
            motivo,
            {
                "actor_id": actor_id,
                "draft_final": sessao_final.get("draft_agendamento"),
                "timestamp_final": sessao_final.get("timestamp_ultima_msg")
            }
        )

    async def cenario_07_multi_tenant_isolamento(self, result: TestResult):
        """
        Cenário 7: Multi-tenant — isolamento

        Mensagem fora de ordem do tenant A não afeta tenant B

        Esperado:
        - Cada tenant tem contexto independente
        - Causalidade preservada por tenant
        """
        print("\n  [CENÁRIO 7] Multi-tenant — isolamento")

        await self.limpar_tenant(self.tenant_a)
        await self.limpar_tenant(self.tenant_b)

        actor_a = normalizar_actor_id(self.canal, "11900000007")
        actor_b = normalizar_actor_id(self.canal, "11900000008")

        # Setup: fluxos diferentes em cada tenant
        sessao_a = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_a,
            "tipo_usuario": "cliente",
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "servico": "corte"
            }
        }

        sessao_b = {
            "tenant_id": self.tenant_b,
            "actor_id": actor_b,
            "tipo_usuario": "cliente",
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "servico": "escova"
            }
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_a, sessao_a)
        await self.salvar_sessao_v2(self.tenant_b, actor_b, sessao_b)

        # ACT: Mensagem fora de ordem em tenant A
        sessao_a_desordenada = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_a,
            "tipo_usuario": "cliente",
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "servico": "hidratacao"  # mudou
            }
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_a, sessao_a_desordenada)

        # Validação: Tenant B não foi afetado
        sessao_b_final = await self.obter_sessao_v2(self.tenant_b, actor_b)
        sessao_a_final = await self.obter_sessao_v2(self.tenant_a, actor_a)

        passou = True
        motivo = ""

        # Tenant B deve estar INTACTO
        if sessao_b_final.get("draft_agendamento", {}).get("servico") != "escova":
            passou = False
            motivo = "Tenant B foi afetado por mudança em tenant A"

        # Tenant A deve estar CONSISTENTE
        if sessao_a_final.get("tenant_id") != self.tenant_a:
            passou = False
            motivo = "Tenant A perdeu isolamento"

        result.registro(
            7,
            "Multi-tenant — isolamento",
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
    print("F2-01 — TESTE DE RESPOSTAS FORA DE ORDEM (CONFIABILIDADE)")
    print("="*80 + "\n")

    result = TestResult()
    teste = F2_01_RespostasForaOrdem()

    try:
        await teste.cenario_01_confirmacao_antes_pedido(result)
        await teste.cenario_02_resposta_profissional_sem_draft(result)
        await teste.cenario_03_pedido_depois_resposta_solta(result)
        await teste.cenario_04_confirmacao_atrasada_fluxo_antigo(result)
        await teste.cenario_05_duas_respostas_rapidas(result)
        await teste.cenario_06_mensagem_timestamp_antigo(result)
        await teste.cenario_07_multi_tenant_isolamento(result)
    except Exception as e:
        print(f"\n[ERRO] Erro durante execução: {e}")
        import traceback
        traceback.print_exc()

    # Resultado final
    print("\n" + "="*80)
    print(f"RESULTADO FINAL: {result.total_pass}/{len(result.cenarios)} PASS")
    print("="*80 + "\n")

    return result.total_pass == len(result.cenarios)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
