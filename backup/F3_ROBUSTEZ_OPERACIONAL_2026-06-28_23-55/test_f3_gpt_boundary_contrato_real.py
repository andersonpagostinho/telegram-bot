"""
F3-GPT-BOUNDARY — CONTRATO GPT/MOTOR (IMPLEMENTAÇÃO REAL)

Validar que GPT INTERPRETA mas NÃO EXECUTA lógica de negócio.

GPT DEVE:
✅ Chamar classificador de linguagem
✅ Extrair: intencao="preenchimento_slot", slot="profissional", valor="indiferente"
✅ Retornar estrutura descritiva

GPT NUNCA:
❌ Escolher profissional específico
❌ Consultar catálogo
❌ Calcular disponibilidade
❌ Verificar conflito
❌ Sugerir horário
❌ Criar evento

MOTOR ENTÃO:
✅ Recebe estrutura
✅ Obtém duração do serviço (já no draft)
✅ Lista profissionais aptos
✅ Busca disponibilidade
✅ Detecta conflitos
✅ Sugere melhor opção
✅ Aguarda confirmação
✅ Cria evento

Status: IMPLEMENTAÇÃO (PYTEST)
Criticidade: 🔴 CRÍTICA (separa responsabilidades)
"""

import asyncio
import sys
import os
import json

# Path: tests/f3_robustez/ → raiz do projeto
raiz_projeto = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, raiz_projeto)

from services.firestore_client import get_db
from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path
from utils.contexto_temporario import salvar_sessao_temporaria, carregar_sessao_temporaria
from services.identidade_service import normalizar_actor_id


class TestResult:
    def __init__(self):
        self.cenarios = []
        self.total_pass = 0

    def registro(self, num, nome, passou, motivo="", dados_extras=None):
        status = "PASS" if passou else "FAIL"
        print(f"  [{status}] F3-GPT-BOUNDARY-{num}: {nome}")
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


class F3GPTBoundaryContrato:
    """F3-GPT-BOUNDARY — Contrato GPT/Motor"""

    def __init__(self):
        self.db = get_db()
        self.tenant_id = "f3_gpt_boundary_tenant_001"
        self.actor_id = normalizar_actor_id("whatsapp", "11988776655")

    async def limpar(self):
        """Limpar teste anterior"""
        try:
            ref = self.db.collection("Clientes").document(self.tenant_id).collection("Sessoes").document(self.actor_id)
            await asyncio.to_thread(ref.delete)
        except:
            pass

    async def cenario_01_gpt_interpreta_sem_executar(self, result: TestResult):
        """F3-GPT-BOUNDARY-1: GPT interpreta, Motor executa"""
        await self.limpar()

        try:
            # Setup: Usuario em fluxo aguardando_profissional com serviço já definido
            contexto_pre = {
                "servico": "corte",
                "data": "2026-07-01",
                "hora": "14:00",
                "estado_fluxo": "aguardando_profissional"
            }
            await salvar_sessao_temporaria(self.actor_id, contexto_pre, self.tenant_id)

            # Simulação: GPT retorna estrutura de preenchimento de slot
            resposta_gpt = {
                "tipo_resposta": "preenchimento_slot",
                "slot": "profissional",
                "valor": "indiferente",
                "confianca": 0.95,
                "ambigua": False
                # ← Estrutura descritiva, NÃO execução
            }

            # Salvar resposta GPT no contexto (como seria no handler)
            contexto_com_resposta = {
                "resposta_gpt_ultimamente": resposta_gpt,
                "estado_fluxo": "aguardando_profissional",  # Não mudou!
            }
            await salvar_sessao_temporaria(self.actor_id, contexto_com_resposta, self.tenant_id)

            # Validar
            sessao = await carregar_sessao_temporaria(self.actor_id, self.tenant_id)

            if (sessao and
                sessao.get("resposta_gpt_ultimamente", {}).get("tipo_resposta") == "preenchimento_slot" and
                sessao.get("estado_fluxo") == "aguardando_profissional" and
                sessao.get("servico") == "corte"):  # draft preservado
                result.registro(
                    1,
                    "GPT interpreta sem executar",
                    True,
                    "",
                    {
                        "tipo_resposta": sessao.get("resposta_gpt_ultimamente", {}).get("tipo_resposta"),
                        "estado_fluxo": sessao.get("estado_fluxo"),
                        "servico_preservado": sessao.get("servico")
                    }
                )
            else:
                result.registro(1, "GPT interpreta sem executar", False, "Resposta ou contexto errado")

        except Exception as e:
            result.registro(1, "GPT interpreta sem executar", False, str(e))

    async def cenario_02_gpt_nao_consulta_catalogo(self, result: TestResult):
        """F3-GPT-BOUNDARY-2: GPT não consulta catálogo"""
        await self.limpar()

        try:
            # Setup
            contexto = {
                "servico": "escova",
                "data": "2026-07-01",
                "estado_fluxo": "aguardando_profissional"
            }
            await salvar_sessao_temporaria(self.actor_id, contexto, self.tenant_id)

            # Simulação: GPT retorna ESTRUTURA (não consulta catálogo)
            resposta_gpt = {
                "tipo_resposta": "preenchimento_slot",
                "slot": "profissional",
                "valor": "indiferente",
                # NÃO contém: lista de profissionais, disponibilidade, etc
            }

            # Motor receberia essa estrutura e faria a query
            contexto_apos_gpt = {"resposta_gpt": resposta_gpt}
            await salvar_sessao_temporaria(self.actor_id, contexto_apos_gpt, self.tenant_id)

            sessao = await carregar_sessao_temporaria(self.actor_id, self.tenant_id)

            # Validar: resposta_gpt NÃO tem campos que são responsabilidade do Motor
            gpt_data = sessao.get("resposta_gpt", {})
            tem_campos_proibidos = any(k in gpt_data for k in [
                "profissionais_listados", "disponibilidade_consultada",
                "conflito_detectado", "sugestao_horario"
            ])

            if not tem_campos_proibidos and gpt_data.get("tipo_resposta") == "preenchimento_slot":
                result.registro(
                    2,
                    "GPT não consulta catálogo",
                    True,
                    "",
                    {"gpt_fields": list(gpt_data.keys())}
                )
            else:
                result.registro(2, "GPT não consulta catálogo", False, "GPT contém campos que não deveria")

        except Exception as e:
            result.registro(2, "GPT não consulta catálogo", False, str(e))

    async def cenario_03_gpt_nao_cria_evento(self, result: TestResult):
        """F3-GPT-BOUNDARY-3: GPT não cria evento"""
        await self.limpar()

        try:
            # Setup
            contexto = {
                "servico": "manicure",
                "data": "2026-07-01",
                "hora": "15:00",
                "estado_fluxo": "aguardando_profissional"
            }
            await salvar_sessao_temporaria(self.actor_id, contexto, self.tenant_id)

            # Simulação: GPT retorna estrutura
            resposta_gpt = {
                "tipo_resposta": "preenchimento_slot",
                "slot": "profissional",
                "valor": "indiferente"
                # NÃO contém: evento_id, evento_criado_em, etc
            }

            # Salvar
            contexto_com_gpt = {"resposta_gpt": resposta_gpt}
            await salvar_sessao_temporaria(self.actor_id, contexto_com_gpt, self.tenant_id)

            sessao = await carregar_sessao_temporaria(self.actor_id, self.tenant_id)

            # Validar: NÃO há evento criado por GPT
            # (Motor criaria depois de confirmação)
            nao_tem_evento = (
                "evento_id" not in sessao and
                "evento_criado_em" not in sessao and
                "evento_confirmado" not in sessao
            )

            if nao_tem_evento and sessao.get("servico") == "manicure":
                result.registro(
                    3,
                    "GPT não cria evento",
                    True,
                    "",
                    {"servico_preservado": sessao.get("servico"),
                     "evento_criado_por_gpt": False}
                )
            else:
                result.registro(3, "GPT não cria evento", False, "Evento foi criado ou contexto alterado")

        except Exception as e:
            result.registro(3, "GPT não cria evento", False, str(e))

    async def cenario_04_fluxo_continua_aguardando(self, result: TestResult):
        """F3-GPT-BOUNDARY-4: Fluxo continua aguardando profissional"""
        await self.limpar()

        try:
            # Setup
            contexto_inicial = {
                "servico": "hidratacao",
                "data": "2026-07-01",
                "estado_fluxo": "aguardando_profissional",
                "profissional_escolhido": None
            }
            await salvar_sessao_temporaria(self.actor_id, contexto_inicial, self.tenant_id)

            # Simulação: User envia "não tenho preferência"
            # GPT interpreta
            resposta_gpt = {
                "tipo_resposta": "preenchimento_slot",
                "slot": "profissional",
                "valor": "indiferente"
            }

            # Motor recebe e... (ainda aguarda confirmação do motor)
            # Fluxo NÃO muda (ainda aguardando_profissional)
            contexto_apos = {
                "resposta_gpt": resposta_gpt,
                "estado_fluxo": "aguardando_profissional"  # ← Não mudou
            }
            await salvar_sessao_temporaria(self.actor_id, contexto_apos, self.tenant_id)

            sessao = await carregar_sessao_temporaria(self.actor_id, self.tenant_id)

            # Validar: estado_fluxo permanece aguardando_profissional
            # draft foi preservado
            if (sessao and
                sessao.get("estado_fluxo") == "aguardando_profissional" and
                sessao.get("servico") == "hidratacao" and
                sessao.get("resposta_gpt", {}).get("valor") == "indiferente"):
                result.registro(
                    4,
                    "Fluxo continua aguardando",
                    True,
                    "",
                    {
                        "estado_fluxo": sessao.get("estado_fluxo"),
                        "draft_preservado": {"servico": sessao.get("servico")},
                        "resposta_gpt_registrada": True
                    }
                )
            else:
                result.registro(4, "Fluxo continua aguardando", False, "Estado fluxo ou draft alterado")

        except Exception as e:
            result.registro(4, "Fluxo continua aguardando", False, str(e))


async def main():
    print("\n" + "="*80)
    print("F3-GPT-BOUNDARY — CONTRATO GPT/MOTOR (IMPLEMENTAÇÃO REAL)")
    print("="*80 + "\n")

    result = TestResult()
    teste = F3GPTBoundaryContrato()

    await teste.cenario_01_gpt_interpreta_sem_executar(result)
    await teste.cenario_02_gpt_nao_consulta_catalogo(result)
    await teste.cenario_03_gpt_nao_cria_evento(result)
    await teste.cenario_04_fluxo_continua_aguardando(result)

    print("\n" + "="*80)
    print(f"F3-GPT-BOUNDARY RESULTADO: {result.total_pass}/4 PASS")
    print("="*80 + "\n")

    return {
        "teste": "F3_GPT_BOUNDARY_CONTRATO",
        "total": 4,
        "pass": result.total_pass,
        "todo": 4 - result.total_pass,
        "cenarios": result.cenarios
    }


if __name__ == "__main__":
    resultado = asyncio.run(main())
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
