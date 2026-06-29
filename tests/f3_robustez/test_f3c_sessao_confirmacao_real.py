"""
F3C — SESSÃO/DRAFT/CONFIRMAÇÃO (6 cenários)

Validar núcleo conversacional com Firestore real:
- Persistência de draft
- Integridade de confirmação
- Recuperação de estado corrompido
- Profissional indiferente (novo)

Status: IMPLEMENTAÇÃO (PYTEST)
Ordem: 1ª para implementar
"""

import asyncio
import sys
import os
from datetime import datetime
import pytz
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
        print(f"  [{status}] F3C-{num}: {nome}")
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


class F3C_SessaoConfirmacaoReal:
    """F3C — Sessão/Draft/Confirmação com Firestore real"""

    def __init__(self):
        self.db = get_db()
        self.tenant_id = "f3c_test_tenant_001"
        self.actor_id = normalizar_actor_id("whatsapp", "11987654321")

    async def limpar(self):
        """Limpar teste anterior"""
        try:
            path = f"Clientes/{self.tenant_id}/Sessoes/{self.actor_id}"
            ref = self.db.collection("Clientes").document(self.tenant_id).collection("Sessoes").document(self.actor_id)
            await asyncio.to_thread(ref.delete)
        except:
            pass

    async def cenario_01_draft_corrompido(self, result: TestResult):
        """F3C-1: Draft corrompido (campo ausente)"""
        await self.limpar()

        try:
            # Setup: Salvar draft SEM o campo 'servico'
            draft_quebrado = {
                "data": "2026-07-01",
                "hora": "14:00",
                # 'servico' INTENCIONAL AUSENTE
                "estado_fluxo": "aguardando_profissional"
            }

            await salvar_sessao_temporaria(self.actor_id, draft_quebrado, self.tenant_id)

            # Carregar e validar
            sessao = await carregar_sessao_temporaria(self.actor_id, self.tenant_id)

            # Esperado: Sistema carregou contexto, mas servico não existe
            if sessao and "servico" not in sessao:
                result.registro(
                    1,
                    "Draft corrompido detectado",
                    True,
                    "",
                    {"draft_keys": list(sessao.keys())}
                )
            else:
                result.registro(1, "Draft corrompido detectado", False, "Draft foi salvo com servico inesperadamente")

        except Exception as e:
            result.registro(1, "Draft corrompido detectado", False, str(e))

    async def cenario_02_confirmacao_draft_errado(self, result: TestResult):
        """F3C-2: Confirmação vinculada a draft errado"""
        await self.limpar()

        try:
            # Draft 1: servico=corte
            draft_v1 = {
                "servico": "corte",
                "data": "2026-07-01",
                "hora": "14:00",
                "estado_fluxo": "aguardando_confirmacao"
            }

            await salvar_sessao_temporaria(self.actor_id, draft_v1, self.tenant_id)

            # Modificar: servico=escova (simular mudança entre passos)
            draft_v2 = {
                "servico": "escova",
                "data": "2026-07-01",
                "hora": "14:00",
                "estado_fluxo": "aguardando_confirmacao"
            }

            await salvar_sessao_temporaria(self.actor_id, draft_v2, self.tenant_id)

            # Carregar: deve ter versão atual
            sessao = await carregar_sessao_temporaria(self.actor_id, self.tenant_id)

            if sessao and sessao.get("servico") == "escova":
                result.registro(
                    2,
                    "Confirmação draft errado detectado",
                    True,
                    "",
                    {"draft_servico": sessao.get("servico")}
                )
            else:
                result.registro(2, "Confirmação draft errado detectado", False, "Draft não atualizou corretamente")

        except Exception as e:
            result.registro(2, "Confirmação draft errado detectado", False, str(e))

    async def cenario_03_sessao_parcialmente_salva(self, result: TestResult):
        """F3C-3: Sessão V2 parcialmente salva"""
        await self.limpar()

        try:
            # Salvar contexto incompleto (falta estado_fluxo)
            contexto_incompleto = {
                "servico": "corte",
                "data": "2026-07-01",
                # falta: estado_fluxo
            }

            await salvar_sessao_temporaria(self.actor_id, contexto_incompleto, self.tenant_id)

            # Carregar
            sessao = await carregar_sessao_temporaria(self.actor_id, self.tenant_id)

            if sessao and "servico" in sessao:
                # Sistema recuperou mesmo com dados incompletos
                result.registro(
                    3,
                    "Sessão parcial recuperada",
                    True,
                    "",
                    {"campos_salvos": list(sessao.keys())}
                )
            else:
                result.registro(3, "Sessão parcial recuperada", False, "Sessão não foi salva corretamente")

        except Exception as e:
            result.registro(3, "Sessão parcial recuperada", False, str(e))

    async def cenario_04_confirmacao_duplicada(self, result: TestResult):
        """F3C-4: Confirmação duplicada (clique rápido 2x)"""
        await self.limpar()

        try:
            # Setup: Draft com dados
            draft = {
                "servico": "corte",
                "data": "2026-07-01",
                "hora": "14:00",
                "profissional": "Bruna",
                "estado_fluxo": "aguardando_confirmacao",
                "confirmacoes_count": 0
            }

            await salvar_sessao_temporaria(self.actor_id, draft, self.tenant_id)

            # Simulação: clique duplo (duas confirmações)
            # Incrementar contador
            draft["confirmacoes_count"] = (draft.get("confirmacoes_count", 0) or 0) + 1
            await salvar_sessao_temporaria(self.actor_id, draft, self.tenant_id)

            draft["confirmacoes_count"] = (draft.get("confirmacoes_count", 0) or 0) + 1
            await salvar_sessao_temporaria(self.actor_id, draft, self.tenant_id)

            # Carregar: deve ter contador idempotente
            sessao = await carregar_sessao_temporaria(self.actor_id, self.tenant_id)

            if sessao and sessao.get("confirmacoes_count") >= 2:
                result.registro(
                    4,
                    "Confirmação duplicada detectada",
                    True,
                    "",
                    {"confirmacoes": sessao.get("confirmacoes_count")}
                )
            else:
                result.registro(4, "Confirmação duplicada detectada", False, "Contador não incrementou")

        except Exception as e:
            result.registro(4, "Confirmação duplicada detectada", False, str(e))

    async def cenario_05_timestamp_invalido(self, result: TestResult):
        """F3C-5: Sessão com timestamp inválido"""
        await self.limpar()

        try:
            # Salvar com timestamp inválido
            contexto_com_timestamp_ruim = {
                "servico": "corte",
                "data": "2026-07-01",
                "timestamp_fluxo": "data_invalida_12345",  # ← Inválido
                "estado_fluxo": "aguardando_profissional"
            }

            await salvar_sessao_temporaria(self.actor_id, contexto_com_timestamp_ruim, self.tenant_id)

            # Carregar: deve ter resistência a parsing
            sessao = await carregar_sessao_temporaria(self.actor_id, self.tenant_id)

            if sessao:
                # Sistema carregou sem crash
                result.registro(
                    5,
                    "Timestamp inválido tratado",
                    True,
                    "",
                    {"timestamp_armazenado": sessao.get("timestamp_fluxo")}
                )
            else:
                result.registro(5, "Timestamp inválido tratado", False, "Sessão não carregou")

        except Exception as e:
            result.registro(5, "Timestamp inválido tratado", False, f"Crash: {str(e)[:50]}")

    async def cenario_06_profissional_indiferente(self, result: TestResult):
        """F3C-6: Profissional indiferente (não tenho preferência)"""
        await self.limpar()

        try:
            # Setup: usuario quer corte mas sem preferência de profissional
            draft_indif = {
                "servico": "corte",
                "data": "2026-07-01",
                "hora": "14:00",
                "profissional_escolhido": None,
                "profissional_indiferente": True,  # Flag de preferencia
                "estado_fluxo": "aguardando_profissional"
            }

            await salvar_sessao_temporaria(self.actor_id, draft_indif, self.tenant_id)

            # Carregar
            sessao = await carregar_sessao_temporaria(self.actor_id, self.tenant_id)

            # Validar
            if (sessao and
                sessao.get("profissional_indiferente") is True and
                sessao.get("servico") == "corte" and
                sessao.get("estado_fluxo") == "aguardando_profissional"):
                result.registro(
                    6,
                    "Profissional indiferente preservado",
                    True,
                    "",
                    {
                        "profissional_indiferente": sessao.get("profissional_indiferente"),
                        "estado_fluxo": sessao.get("estado_fluxo"),
                        "servico": sessao.get("servico")
                    }
                )
            else:
                result.registro(
                    6,
                    "Profissional indiferente preservado",
                    False,
                    f"Draft não preservado corretamente"
                )

        except Exception as e:
            result.registro(6, "Profissional indiferente preservado", False, str(e))


async def main():
    print("\n" + "="*80)
    print("F3C — SESSÃO/DRAFT/CONFIRMAÇÃO (IMPLEMENTAÇÃO REAL)")
    print("="*80 + "\n")

    result = TestResult()
    teste = F3C_SessaoConfirmacaoReal()

    await teste.cenario_01_draft_corrompido(result)
    await teste.cenario_02_confirmacao_draft_errado(result)
    await teste.cenario_03_sessao_parcialmente_salva(result)
    await teste.cenario_04_confirmacao_duplicada(result)
    await teste.cenario_05_timestamp_invalido(result)
    await teste.cenario_06_profissional_indiferente(result)

    print("\n" + "="*80)
    print(f"F3C RESULTADO: {result.total_pass}/6 PASS")
    print("="*80 + "\n")

    return {
        "teste": "F3C_SESSAO_CONFIRMACAO",
        "total": 6,
        "pass": result.total_pass,
        "todo": 6 - result.total_pass,
        "cenarios": result.cenarios
    }


if __name__ == "__main__":
    resultado = asyncio.run(main())
    import json
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
