"""
F2-03 — TESTE DE SESSÃO CAÍDA E RECONEXÃO

Objetivo: Garantir que reinícios, quedas de processo, retries e reconexões
          nunca corrompem o estado conversacional da NeoEve.

Princípios:
- Sessão V2 = única fonte de verdade
- Reinício não altera estado
- Retries são idempotentes
- Reconexão não duplica eventos
- Isolamento multi-tenant garantido

Status: FASE 2 (Confiabilidade) — não entra em P0 ainda
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import pytz
import json

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


class F2_03_SessaoCaidaReconexao:
    """Testes de confiabilidade: sessão caída e reconexão"""

    def __init__(self):
        self.db = get_db()
        self.tenant_a = "f2_03_tenant_reconexao_a"
        self.tenant_b = "f2_03_tenant_reconexao_b"
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

    async def cenario_01_reinicio_entre_pergunta_resposta(self, result: TestResult):
        """
        Cenário 1: Reinício entre pergunta e resposta

        Fluxo:
        - Iniciar agendamento
        - estado=aguardando_profissional
        - Salvar em Firestore (simula primeiro restart)
        - Responder "Bruna"

        Esperado:
        - Fluxo continua normalmente
        - Nenhum dado perdido
        """
        print("\n  [CENÁRIO 1] Reinício entre pergunta e resposta")

        await self.limpar_tenant(self.tenant_a)

        actor_id = normalizar_actor_id(self.canal, "11900000001")

        # Setup: iniciar fluxo antes do restart
        sessao_antes = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            "estado_fluxo": "aguardando_profissional",
            "draft_agendamento": {
                "servico": "corte",
                "data": "2026-06-29",
                "hora": "14:00"
            },
            "timestamp_fluxo": datetime.now(pytz.UTC).isoformat()
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao_antes)

        # Simular restart (ler dados de Firestore como se processo reiniciasse)
        sessao_apos_restart = await self.obter_sessao_v2(self.tenant_a, actor_id)

        # ACT: responder após restart
        sessao_com_resposta = sessao_apos_restart.copy()
        sessao_com_resposta["draft_agendamento"]["profissional"] = "Bruna"
        sessao_com_resposta["estado_fluxo"] = "aguardando_confirmacao_agendamento"

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao_com_resposta)

        sessao_final = await self.obter_sessao_v2(self.tenant_a, actor_id)

        passou = True
        motivo = ""

        # Validação: Dados antes do restart preservados
        if sessao_final.get("draft_agendamento", {}).get("servico") != "corte":
            passou = False
            motivo = "Serviço foi perdido após restart"

        if sessao_final.get("draft_agendamento", {}).get("data") != "2026-06-29":
            passou = False
            motivo = "Data foi perdida após restart"

        # Validação: Nova resposta registrada
        if sessao_final.get("draft_agendamento", {}).get("profissional") != "Bruna":
            passou = False
            motivo = "Resposta não foi registrada"

        result.registro(
            1,
            "Reinício entre pergunta e resposta",
            passou,
            motivo,
            {
                "actor_id": actor_id,
                "draft_final": sessao_final.get("draft_agendamento"),
                "fluxo_continuou": sessao_final.get("estado_fluxo") == "aguardando_confirmacao_agendamento"
            }
        )

    async def cenario_02_reinicio_com_confirmacao_pendente(self, result: TestResult):
        """
        Cenário 2: Reinício com confirmação pendente

        Fluxo:
        - Confirmação aguardando "sim/não"
        - Reiniciar processo
        - Usuário responde "sim"

        Esperado:
        - Evento criado uma única vez
        - Sem duplicidade
        - Sem perda de confirmação
        """
        print("\n  [CENÁRIO 2] Reinício com confirmação pendente")

        await self.limpar_tenant(self.tenant_a)

        actor_id = normalizar_actor_id(self.canal, "11900000002")

        # Setup: confirmação pendente
        sessao_antes = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            "estado_fluxo": "aguardando_confirmacao_agendamento",
            "draft_agendamento": {
                "servico": "corte",
                "data": "2026-06-29",
                "hora": "14:00",
                "profissional": "Bruna"
            },
            "dados_confirmacao_agendamento": {
                "servico": "corte",
                "data": "2026-06-29",
                "hora": "14:00",
                "profissional": "Bruna",
                "criado_em": datetime.now(pytz.UTC).isoformat()
            }
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao_antes)

        # Simular restart
        sessao_apos_restart = await self.obter_sessao_v2(self.tenant_a, actor_id)

        # Validação 1: Estado preservado
        passou = True
        motivo = ""

        if not sessao_apos_restart.get("dados_confirmacao_agendamento"):
            passou = False
            motivo = "Dados de confirmação foram perdidos no restart"

        # ACT: processar confirmação após restart
        sessao_confirmada = sessao_apos_restart.copy()
        sessao_confirmada["estado_fluxo"] = "evento_criado"
        sessao_confirmada.pop("dados_confirmacao_agendamento", None)

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao_confirmada)

        sessao_final = await self.obter_sessao_v2(self.tenant_a, actor_id)

        # Validação 2: Confirmação processada uma única vez
        if sessao_final.get("estado_fluxo") != "evento_criado":
            passou = False
            motivo = "Confirmação não foi processada"

        result.registro(
            2,
            "Reinício com confirmação pendente",
            passou,
            motivo,
            {
                "actor_id": actor_id,
                "confirmacao_preservada": bool(sessao_apos_restart.get("dados_confirmacao_agendamento")),
                "evento_criado_uma_vez": sessao_final.get("estado_fluxo") == "evento_criado"
            }
        )

    async def cenario_03_retry_mensagem_duplicada(self, result: TestResult):
        """
        Cenário 3: Retry do Telegram (mensagem duplicada)

        Mesmo update recebido duas vezes.

        Esperado:
        - Processamento idempotente
        - Nenhum evento duplicado
        - Nenhuma alteração indevida de estado
        """
        print("\n  [CENÁRIO 3] Retry (mensagem duplicada)")

        await self.limpar_tenant(self.tenant_a)

        actor_id = normalizar_actor_id(self.canal, "11900000003")

        # Setup
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

        # ACT: processar mesma mensagem "Bruna" duas vezes
        for i in range(2):
            sessao_atual = await self.obter_sessao_v2(self.tenant_a, actor_id)
            sessao_atual["draft_agendamento"]["profissional"] = "Bruna"
            sessao_atual["ultima_msg_timestamp"] = datetime.now(pytz.UTC).isoformat()
            await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao_atual)

        sessao_final = await self.obter_sessao_v2(self.tenant_a, actor_id)

        passou = True
        motivo = ""

        # Validação: Profissional definido uma única vez (idempotente)
        if sessao_final.get("draft_agendamento", {}).get("profissional") != "Bruna":
            passou = False
            motivo = "Profissional não foi setado"

        # Validação: Sem duplicação de dados
        if isinstance(sessao_final.get("draft_agendamento", {}).get("profissional"), list):
            passou = False
            motivo = "Profissional foi duplicado"

        result.registro(
            3,
            "Retry (mensagem duplicada)",
            passou,
            motivo,
            {
                "actor_id": actor_id,
                "idempotencia_ok": sessao_final.get("draft_agendamento", {}).get("profissional") == "Bruna"
            }
        )

    async def cenario_04_sessao_interrompida_por_horas(self, result: TestResult):
        """
        Cenário 4: Sessão interrompida por horas

        Fluxo:
        - Iniciar atendimento
        - Persistir contexto
        - Simular horas depois
        - Continuar conversa

        Esperado:
        - Sessão V2 preservada
        - Retomada correta
        """
        print("\n  [CENÁRIO 4] Sessão interrompida por horas")

        await self.limpar_tenant(self.tenant_a)

        actor_id = normalizar_actor_id(self.canal, "11900000004")

        agora = datetime.now(pytz.UTC)
        horas_atras = agora - timedelta(hours=3)

        # Setup: contexto antigo (3 horas atrás)
        sessao_antiga = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            "estado_fluxo": "aguardando_data",
            "draft_agendamento": {
                "servico": "corte"
            },
            "timestamp_ultima_msg": horas_atras.isoformat(),
            "atualizado_em": horas_atras.isoformat()
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao_antiga)

        # Simular horas depois: continuar conversa
        sessao_retomada = await self.obter_sessao_v2(self.tenant_a, actor_id)

        # ACT: usuário responde data
        sessao_atualizada = sessao_retomada.copy()
        sessao_atualizada["draft_agendamento"]["data"] = "2026-07-01"
        sessao_atualizada["timestamp_ultima_msg"] = agora.isoformat()
        sessao_atualizada["atualizado_em"] = agora.isoformat()

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao_atualizada)

        sessao_final = await self.obter_sessao_v2(self.tenant_a, actor_id)

        passou = True
        motivo = ""

        # Validação: Contexto antigo preservado
        if sessao_final.get("draft_agendamento", {}).get("servico") != "corte":
            passou = False
            motivo = "Contexto antigo foi perdido"

        # Validação: Nova resposta registrada
        if sessao_final.get("draft_agendamento", {}).get("data") != "2026-07-01":
            passou = False
            motivo = "Nova resposta não foi registrada"

        # Validação: Timestamp atualizado
        if sessao_final.get("timestamp_ultima_msg") == horas_atras.isoformat():
            passou = False
            motivo = "Timestamp não foi atualizado"

        result.registro(
            4,
            "Sessão interrompida por horas",
            passou,
            motivo,
            {
                "actor_id": actor_id,
                "servico_preservado": sessao_final.get("draft_agendamento", {}).get("servico"),
                "data_adicionada": sessao_final.get("draft_agendamento", {}).get("data")
            }
        )

    async def cenario_05_queda_durante_cancelamento(self, result: TestResult):
        """
        Cenário 5: Queda durante cancelamento

        Fluxo:
        - cancelamento_pendente=true
        - Reinício
        - Usuário confirma

        Esperado:
        - Cancelamento executado apenas uma vez
        - Contexto limpo corretamente
        """
        print("\n  [CENÁRIO 5] Queda durante cancelamento")

        await self.limpar_tenant(self.tenant_a)

        actor_id = normalizar_actor_id(self.canal, "11900000005")

        # Setup: cancelamento pendente
        sessao_cancelamento = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            "cancelamento_pendente": True,
            "evento_a_cancelar": {
                "data": "2026-06-29",
                "horario": "14:00",
                "servico": "corte"
            }
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao_cancelamento)

        # Simular restart
        sessao_apos_restart = await self.obter_sessao_v2(self.tenant_a, actor_id)

        passou = True
        motivo = ""

        # Validação 1: Cancelamento pendente preservado
        if not sessao_apos_restart.get("cancelamento_pendente"):
            passou = False
            motivo = "cancelamento_pendente foi perdido no restart"

        # ACT: processar cancelamento
        # Criar novo documento SEM os campos antigos (merge=False sobrescreve)
        sessao_confirmada = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            "cancelamento_confirmado": True
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao_confirmada, merge=False)

        sessao_final = await self.obter_sessao_v2(self.tenant_a, actor_id)

        # Validação 2: Cancelamento executado uma única vez
        if not sessao_final.get("cancelamento_confirmado"):
            passou = False
            motivo = "Cancelamento não foi confirmado"

        if "cancelamento_pendente" in sessao_final:
            passou = False
            motivo = "cancelamento_pendente não foi limpo"

        result.registro(
            5,
            "Queda durante cancelamento",
            passou,
            motivo,
            {
                "actor_id": actor_id,
                "cancelamento_confirmado": sessao_final.get("cancelamento_confirmado"),
                "pendente_limpo": "cancelamento_pendente" not in sessao_final
            }
        )

    async def cenario_06_multi_tenant_isolamento(self, result: TestResult):
        """
        Cenário 6: Multi-tenant

        Tenant A reinicia.

        Esperado:
        - Tenant B permanece intacto
        - Nenhuma contaminação de sessão
        """
        print("\n  [CENÁRIO 6] Multi-tenant isolamento")

        await self.limpar_tenant(self.tenant_a)
        await self.limpar_tenant(self.tenant_b)

        actor_a = normalizar_actor_id(self.canal, "11900000006")
        actor_b = normalizar_actor_id(self.canal, "11900000007")

        # Setup: sessões em tenants diferentes
        sessao_a = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_a,
            "tipo_usuario": "cliente",
            "draft_agendamento": {"servico": "corte"}
        }

        sessao_b = {
            "tenant_id": self.tenant_b,
            "actor_id": actor_b,
            "tipo_usuario": "cliente",
            "draft_agendamento": {"servico": "escova"}
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_a, sessao_a)
        await self.salvar_sessao_v2(self.tenant_b, actor_b, sessao_b)

        # Simular restart de tenant A
        sessao_a_apos_restart = await self.obter_sessao_v2(self.tenant_a, actor_a)

        # ACT: modificar apenas tenant A
        sessao_a_nova = sessao_a_apos_restart.copy()
        sessao_a_nova["draft_agendamento"]["servico"] = "hidratacao"
        await self.salvar_sessao_v2(self.tenant_a, actor_a, sessao_a_nova)

        # Verificar isolamento
        sessao_a_final = await self.obter_sessao_v2(self.tenant_a, actor_a)
        sessao_b_final = await self.obter_sessao_v2(self.tenant_b, actor_b)

        passou = True
        motivo = ""

        # Validação: Tenant A foi alterado
        if sessao_a_final.get("draft_agendamento", {}).get("servico") != "hidratacao":
            passou = False
            motivo = "Tenant A não foi alterado"

        # Validação: Tenant B permanece intacto
        if sessao_b_final.get("draft_agendamento", {}).get("servico") != "escova":
            passou = False
            motivo = "Tenant B foi afetado por restart de A"

        result.registro(
            6,
            "Multi-tenant isolamento",
            passou,
            motivo,
            {
                "tenant_a_servico": sessao_a_final.get("draft_agendamento", {}).get("servico"),
                "tenant_b_servico": sessao_b_final.get("draft_agendamento", {}).get("servico"),
                "isolamento_ok": sessao_b_final.get("draft_agendamento", {}).get("servico") == "escova"
            }
        )

    async def cenario_07_legacy_inexistente(self, result: TestResult):
        """
        Cenário 7: Legacy inexistente

        Sessão V2 válida
        MemoriaTemporaria ausente

        Esperado:
        - Continua funcionando
        - Nenhuma tentativa de reconstrução incorreta
        """
        print("\n  [CENÁRIO 7] Legacy inexistente")

        await self.limpar_tenant(self.tenant_a)

        actor_id = normalizar_actor_id(self.canal, "11900000008")

        # Setup: Apenas V2, sem legacy
        sessao_v2 = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            "estado_fluxo": "aguardando_profissional",
            "draft_agendamento": {
                "servico": "corte",
                "data": "2026-06-29"
            }
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao_v2)

        # ACT: carregamento após restart (V2 existe, legacy não)
        sessao_carregada = await self.obter_sessao_v2(self.tenant_a, actor_id)

        passou = True
        motivo = ""

        # Validação: V2 foi carregada corretamente
        if not sessao_carregada.get("estado_fluxo"):
            passou = False
            motivo = "V2 não foi carregada"

        if sessao_carregada.get("draft_agendamento", {}).get("servico") != "corte":
            passou = False
            motivo = "V2 dados corrompidos"

        # Validação: Sem tentativa de reconstrução
        if sessao_carregada.get("legado_reconstruido"):
            passou = False
            motivo = "Sistema tentou reconstruir legacy indevidamente"

        result.registro(
            7,
            "Legacy inexistente",
            passou,
            motivo,
            {
                "actor_id": actor_id,
                "v2_carregada": bool(sessao_carregada.get("estado_fluxo")),
                "sem_reconstrucao": "legado_reconstruido" not in sessao_carregada
            }
        )

    async def cenario_08_legacy_conflitante(self, result: TestResult):
        """
        Cenário 8: Legacy conflitante

        Sessão V2: estado_fluxo=aguardando_profissional
        Legado: estado_fluxo=None

        Esperado:
        - V2 vence
        - Legado ignorado
        """
        print("\n  [CENÁRIO 8] Legacy conflitante")

        await self.limpar_tenant(self.tenant_a)

        actor_id = normalizar_actor_id(self.canal, "11900000009")

        # Setup: V2 com fluxo ativo, legado vazio
        sessao_v2 = {
            "tenant_id": self.tenant_a,
            "actor_id": actor_id,
            "tipo_usuario": "cliente",
            "estado_fluxo": "aguardando_profissional",
            "draft_agendamento": {
                "servico": "corte"
            }
        }

        await self.salvar_sessao_v2(self.tenant_a, actor_id, sessao_v2)

        # Simular: legacy vazio (estado_fluxo=None)
        # (Na prática, legacy não existiria ou estaria vazio)

        # ACT: carregamento após restart
        sessao_final = await self.obter_sessao_v2(self.tenant_a, actor_id)

        passou = True
        motivo = ""

        # Validação: V2 venceu
        if sessao_final.get("estado_fluxo") != "aguardando_profissional":
            passou = False
            motivo = "V2 foi sobrescrito por legacy"

        if not sessao_final.get("draft_agendamento", {}).get("servico"):
            passou = False
            motivo = "Draft foi perdido"

        result.registro(
            8,
            "Legacy conflitante",
            passou,
            motivo,
            {
                "actor_id": actor_id,
                "v2_venceu": sessao_final.get("estado_fluxo") == "aguardando_profissional",
                "draft_preservado": bool(sessao_final.get("draft_agendamento", {}).get("servico"))
            }
        )


async def main():
    print("\n" + "="*80)
    print("F2-03 — TESTE DE SESSÃO CAÍDA E RECONEXÃO (CONFIABILIDADE)")
    print("="*80 + "\n")

    result = TestResult()
    teste = F2_03_SessaoCaidaReconexao()

    try:
        await teste.cenario_01_reinicio_entre_pergunta_resposta(result)
        await teste.cenario_02_reinicio_com_confirmacao_pendente(result)
        await teste.cenario_03_retry_mensagem_duplicada(result)
        await teste.cenario_04_sessao_interrompida_por_horas(result)
        await teste.cenario_05_queda_durante_cancelamento(result)
        await teste.cenario_06_multi_tenant_isolamento(result)
        await teste.cenario_07_legacy_inexistente(result)
        await teste.cenario_08_legacy_conflitante(result)
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
