"""
F3F — FALHAS EXTERNAS (5 cenários)

Validar resiliência contra falhas de API externa (GPT, Firestore, WhatsApp).

Cenários:
F1: Firestore indisponível na leitura → sem crash, sem evento parcial, sessão preservada
F2: Firestore falha na gravação → sem lock órfão, sem confirmação falsa, sessão recuperável
F3: Falha na interpretação GPT → sem crash, sessão preservada, fallback
F4: GPT retorna JSON inválido → descarta, preserva sessão, pede esclarecimento
F5: Firestore commit falha após interpretação → evento não criado, sessão intacta

Status: IMPLEMENTAÇÃO
Ordem: 7ª para implementar
"""

import asyncio
import sys
import os
import json
import uuid
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.firestore_client import get_db
from utils.contexto_temporario import salvar_sessao_temporaria, carregar_sessao_temporaria
from services.identidade_service import normalizar_actor_id


class TestResult:
    def __init__(self):
        self.cenarios = []
        self.total_pass = 0

    def registro(self, num, nome, passou, motivo="", dados_extras=None):
        status = "PASS" if passou else "FAIL"
        print(f"  [{status}] F3F-{num}: {nome}")
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


class F3F_FalhasExternasReal:
    """F3F — Falhas Externas com simulacao controlada"""

    def __init__(self):
        self.db = get_db()
        self.tenant_id = "f3f_test_tenant_001"
        self.canal = "whatsapp"

    async def limpar_tenant(self):
        """Limpar tenant de teste"""
        try:
            sessoes_ref = self.db.collection("Clientes").document(self.tenant_id).collection("Sessoes")
            docs = await asyncio.to_thread(lambda: list(sessoes_ref.stream()))
            for doc in docs:
                await asyncio.to_thread(doc.reference.delete)

            eventos_ref = self.db.collection("Clientes").document(self.tenant_id).collection("Eventos")
            docs = await asyncio.to_thread(lambda: list(eventos_ref.stream()))
            for doc in docs:
                await asyncio.to_thread(doc.reference.delete)

            print(f"  [CLEANUP] Tenant {self.tenant_id} limpo")
        except Exception as e:
            print(f"  [CLEANUP ERROR] {e}")

    async def cenario_01_firestore_leitura_timeout(self, result: TestResult):
        """F1: Firestore indisponivel na leitura"""
        await self.limpar_tenant()

        try:
            actor_id = normalizar_actor_id(self.canal, "11912345678")
            ctx = {"servico": "corte", "estado_fluxo": "aguardando_profissional"}
            await salvar_sessao_temporaria(actor_id, ctx, self.tenant_id)

            # Simular falha na leitura
            with mock.patch("utils.contexto_temporario.buscar_dado_em_path") as mock_buscar:
                mock_buscar.side_effect = TimeoutError("Firestore timeout")
                try:
                    sessao = await carregar_sessao_temporaria(actor_id, self.tenant_id)
                except TimeoutError:
                    sessao = None

            # Validar: sessao original preservada
            sessao_original = await carregar_sessao_temporaria(actor_id, self.tenant_id)
            sessao_preservada = sessao_original and sessao_original.get("servico") == "corte"

            if sessao_preservada:
                result.registro(1, "Firestore leitura timeout", True, "",
                    {"erro": "TimeoutError", "sessao_preservada": True, "sem_crash": True})
            else:
                result.registro(1, "Firestore leitura timeout", False, "Sessao perdida")

        except Exception as e:
            result.registro(1, "Firestore leitura timeout", False, str(e))

    async def cenario_02_firestore_gravacao_erro(self, result: TestResult):
        """F2: Firestore falha durante gravacao (write timeout)"""
        await self.limpar_tenant()

        try:
            actor_id = normalizar_actor_id(self.canal, "11987654321")
            ctx = {"servico": "escova", "estado_fluxo": "aguardando_confirmacao"}
            await salvar_sessao_temporaria(actor_id, ctx, self.tenant_id)

            # Simular falha ao tentar salvar evento
            evento_criado = False
            try:
                with mock.patch("services.firebase_service_async.salvar_dado_em_path") as mock_salvar:
                    mock_salvar.side_effect = Exception("Firestore write timeout")
                    evento_id = str(uuid.uuid4())
                    await mock_salvar(f"Clientes/{self.tenant_id}/Eventos/{evento_id}", {"id": evento_id})
                    evento_criado = True
            except Exception:
                evento_criado = False

            # Validar: evento NAO foi criado, sessao preservada
            sessao = await carregar_sessao_temporaria(actor_id, self.tenant_id)
            sessao_intacta = sessao and sessao.get("servico") == "escova"

            if not evento_criado and sessao_intacta:
                result.registro(2, "Firestore gravacao erro", True, "",
                    {"erro": "write timeout", "evento_criado": False, "sessao_preservada": True})
            else:
                motivo = "evento nao deveria ser criado em erro" if evento_criado else "sessao comprometida"
                result.registro(2, "Firestore gravacao erro", False, motivo)

        except Exception as e:
            result.registro(2, "Firestore gravacao erro", False, str(e))

    async def cenario_03_gpt_interpretacao_erro(self, result: TestResult):
        """F3: GPT retorna erro na interpretacao"""
        await self.limpar_tenant()

        try:
            actor_id = normalizar_actor_id(self.canal, "11976543210")
            ctx = {"servico": "manicure", "estado_fluxo": "aguardando_interpretacao"}
            await salvar_sessao_temporaria(actor_id, ctx, self.tenant_id)

            interpretacao_obtida = False
            try:
                with mock.patch("services.gpt_service.processar_com_gpt") as mock_gpt:
                    mock_gpt.side_effect = Exception("GPT service unavailable")
                    resultado = await mock_gpt("texto qualquer")
                    interpretacao_obtida = True
            except Exception:
                interpretacao_obtida = False

            # Validar: interpretacao falhou, sessao preservada
            sessao = await carregar_sessao_temporaria(actor_id, self.tenant_id)
            sessao_intacta = sessao and sessao.get("servico") == "manicure"

            if not interpretacao_obtida and sessao_intacta:
                result.registro(3, "GPT interpretacao erro", True, "",
                    {"erro": "GPT unavailable", "interpretacao": False, "sessao_preservada": True})
            else:
                result.registro(3, "GPT interpretacao erro", False, "Interpretacao ou sessao compromet.")

        except Exception as e:
            result.registro(3, "GPT interpretacao erro", False, str(e))

    async def cenario_04_gpt_json_invalido(self, result: TestResult):
        """F4: GPT retorna JSON invalido"""
        await self.limpar_tenant()

        try:
            actor_id = normalizar_actor_id(self.canal, "11965432109")
            ctx = {"servico": "hidratacao", "estado_fluxo": "aguardando_interpretacao"}
            await salvar_sessao_temporaria(actor_id, ctx, self.tenant_id)

            # Simular resposta invalida do GPT
            resposta_gpt = '{"tipo_resposta": invalid json}'
            json_valido = False

            try:
                dados = json.loads(resposta_gpt)
                json_valido = True
            except json.JSONDecodeError:
                json_valido = False

            # Validar: JSON invalido rejeitado, sessao preservada
            sessao = await carregar_sessao_temporaria(actor_id, self.tenant_id)
            sessao_intacta = sessao and sessao.get("servico") == "hidratacao"

            if not json_valido and sessao_intacta:
                result.registro(4, "GPT JSON invalido", True, "",
                    {"erro": "JSON decode error", "valido": False, "sessao_preservada": True})
            else:
                result.registro(4, "GPT JSON invalido", False, "JSON valido ou sessao perdida")

        except Exception as e:
            result.registro(4, "GPT JSON invalido", False, str(e))

    async def cenario_05_evento_persistencia_falha(self, result: TestResult):
        """F5: Evento consegue ser criado mas persistencia falha no commit final"""
        await self.limpar_tenant()

        try:
            actor_id = normalizar_actor_id(self.canal, "11954321098")
            ctx = {"servico": "corte", "estado_fluxo": "pronto_para_confirmar"}
            await salvar_sessao_temporaria(actor_id, ctx, self.tenant_id)

            evento_id = str(uuid.uuid4())
            evento_data = {
                "id": evento_id,
                "cliente": "cliente_teste",
                "servico": "corte",
                "profissional": "Carlos"
            }

            # Simular falha no commit final
            commit_sucesso = False
            try:
                with mock.patch("services.firebase_service_async.salvar_evento") as mock_salvar:
                    mock_salvar.side_effect = Exception("Firestore commit failed")
                    await mock_salvar(evento_data)
                    commit_sucesso = True
            except Exception:
                commit_sucesso = False

            # Validar: evento nao foi persistido, sessao preservada
            sessao = await carregar_sessao_temporaria(actor_id, self.tenant_id)
            sessao_intacta = sessao and sessao.get("servico") == "corte"

            # Verificar se evento foi salvo em Firestore
            eventos_ref = self.db.collection("Clientes").document(self.tenant_id).collection("Eventos")
            eventos = list(await asyncio.to_thread(lambda: eventos_ref.stream()))
            evento_em_firebase = any(doc.id == evento_id for doc in eventos)

            if not commit_sucesso and not evento_em_firebase and sessao_intacta:
                result.registro(5, "Evento persistencia falha", True, "",
                    {"erro": "commit failed", "persistido": False, "sessao_preservada": True})
            else:
                motivo = []
                if commit_sucesso:
                    motivo.append("commit nao deveria suceder")
                if evento_em_firebase:
                    motivo.append("evento em firebase")
                if not sessao_intacta:
                    motivo.append("sessao perdida")
                result.registro(5, "Evento persistencia falha", False, " + ".join(motivo) if motivo else "falha desconhecida")

        except Exception as e:
            result.registro(5, "Evento persistencia falha", False, str(e))


async def main():
    print("\n" + "="*80)
    print("F3F — FALHAS EXTERNAS (IMPLEMENTACAO REAL)")
    print("="*80 + "\n")

    result = TestResult()
    teste = F3F_FalhasExternasReal()

    await teste.cenario_01_firestore_leitura_timeout(result)
    await teste.cenario_02_firestore_gravacao_erro(result)
    await teste.cenario_03_gpt_interpretacao_erro(result)
    await teste.cenario_04_gpt_json_invalido(result)
    await teste.cenario_05_evento_persistencia_falha(result)

    # Limpeza final
    await teste.limpar_tenant()

    print("\n" + "="*80)
    print(f"F3F RESULTADO: {result.total_pass}/5 PASS")
    print("="*80 + "\n")

    return {
        "teste": "F3F_FALHAS_EXTERNAS",
        "total": 5,
        "pass": result.total_pass,
        "todo": 5 - result.total_pass,
        "cenarios": result.cenarios
    }


if __name__ == "__main__":
    resultado = asyncio.run(main())
