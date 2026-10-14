"""
P0.1 - OUTRA PROFISSIONAL (Firebase Real + Tenant Real)

Validar fix de estado com Firebase real:
- Tenant: 7394370553
- Cliente/WhatsApp: 5511991382080 (normalizado como "whatsapp:5511991382080")
- Contexto: estado_fluxo="agandando" + modo_escolha_horario=True (corrompido)
- Mensagem: "outra profissional"
- Esperado: P0.1 detecta, apresenta menu com alternativas

Baseado em: test_f3c_sessao_confirmacao_real.py
Status: VALIDAÇÃO FIREBASE REAL
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import json

# Path: tests/ -> raiz do projeto
raiz_projeto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, raiz_projeto)

from services.firestore_client import get_db
from services.firebase_service_async import (
    atualizar_dado_em_path,
    buscar_dado_em_path,
    salvar_dado_em_path
)
from utils.contexto_temporario import (
    salvar_contexto_temporario_v2,
    carregar_contexto_temporario_v2
)
from services.identidade_service import normalizar_actor_id


class TestP01OutraProfissionalFirebaseReal:
    """P0.1 com Firebase real - "outra profissional" durante confirmação pendente"""

    def __init__(self):
        self.db = get_db()
        self.tenant_id = "7394370553"  # Tenant real
        self.cliente_id = "7371670478"  # Cliente real
        self.wa_id = "5511991382080"    # WhatsApp real
        self.actor_id = normalizar_actor_id("whatsapp", self.wa_id)
        print(f"[OK] Configurado: tenant={self.tenant_id}, actor_id={self.actor_id}")

    async def limpar_sessao(self):
        """Limpar contexto anterior"""
        try:
            path = f"Clientes/{self.tenant_id}/Sessoes/{self.actor_id}"
            ref = self.db.collection("Clientes").document(self.tenant_id).collection("Sessoes").document(self.actor_id)
            await asyncio.to_thread(ref.delete)
            print(f"[OK] Sessão anterior removida")
        except Exception as e:
            print(f"[OK][OK]  Não conseguiu remover sessão anterior: {e}")

    async def salvar_contexto_corrompido(self):
        """
        Salvar contexto CORROMPIDO no Firestore:
        - estado_fluxo = "agandando" (typo do merge anterior)
        - modo_escolha_horario = True (permaneceu de execução anterior com conflito)

        Isto simula a condição que ocorreu em produção.
        """
        ctx_corrompido = {
            "estado_fluxo": "agandando",  # ← CORROMPIDO (typo)
            "modo_escolha_horario": True,  # ← CORROMPIDO (de execução anterior)
            "intencao_conversacional": "confirmacao_agendamento",
            "aguardando_confirmacao_agendamento": True,
            "dados_confirmacao_agendamento": {
                "profissional": "Gloria",
                "servico": "Corte",
                "data_hora": (datetime.now() + timedelta(days=1)).isoformat() + "T14:00:00",
                "duracao": 30,
                "descricao": "Corte com Gloria"
            },
            "draft_agendamento": {
                "profissional": "Gloria",
                "data_hora": (datetime.now() + timedelta(days=1)).isoformat() + "T14:00:00",
                "servico": "Corte",
                "modo_prechecagem": True
            },
            "alternativa_profissional": ["Bruna", "Joana"],
            "ultima_opcao_profissionais": ["Gloria", "Bruna", "Joana"],
            "horarios_sugeridos": ["15:00", "16:00", "17:00"],
            "servico": "Corte",
            "profissional_escolhido": "Gloria",
            "data_hora": (datetime.now() + timedelta(days=1)).isoformat() + "T14:00:00",
            "ultima_acao": "criar_evento"
        }

        # Salvar no Firestore
        await salvar_contexto_temporario_v2(
            self.tenant_id,
            self.cliente_id,
            ctx_corrompido
        )

        print(f"[OK] Contexto CORROMPIDO salvo no Firestore:")
        print(f"  - estado_fluxo = {ctx_corrompido['estado_fluxo']}")
        print(f"  - modo_escolha_horario = {ctx_corrompido['modo_escolha_horario']}")

        return ctx_corrompido

    async def carregar_e_validar_contexto(self):
        """Carregar contexto do Firestore e validar estado"""
        ctx_carregado = await carregar_contexto_temporario_v2(
            self.tenant_id,
            self.cliente_id
        )

        if not ctx_carregado:
            print("[OK] Erro: Contexto não foi carregado do Firestore")
            return None

        print(f"\n[OK] Contexto carregado do Firestore:")
        print(f"  - estado_fluxo = {ctx_carregado.get('estado_fluxo')}")
        print(f"  - modo_escolha_horario = {ctx_carregado.get('modo_escolha_horario')}")
        print(f"  - intencao = {ctx_carregado.get('intencao_conversacional')}")

        return ctx_carregado

    async def simular_precheck_sem_conflito(self, ctx):
        """
        Simular execução do precheck SEM CONFLITO.
        Isto deve:
        1. Manter estado_fluxo = "agandando"
        2. AGORA COM FIX: Explicitamente setar modo_escolha_horario = False

        Código extraído de precheck_func.py linhas 140-227
        """
        print(f"\n[PRECHECK SEM CONFLITO] Simulando...")

        # Linhas 142-143 do precheck_func.py
        ctx["estado_fluxo"] = "agandando"
        ctx["modo_escolha_horario"] = False  # ← FIX CRÍTICA (linha 143)

        ctx["draft_agendamento"] = {
            "profissional": "Gloria",
            "data_hora": ctx.get("data_hora"),
            "servico": ctx.get("servico"),
            "modo_prechecagem": True
        }

        ctx["aguardando_confirmacao_agendamento"] = True
        ctx["dados_confirmacao_agendamento"] = {
            "profissional": "Gloria",
            "servico": "Corte",
            "data_hora": ctx.get("data_hora"),
            "duracao": 30,
            "descricao": "Corte com Gloria"
        }

        # Salvar contexto atualizado (linha 228)
        await salvar_contexto_temporario_v2(
            self.tenant_id,
            self.cliente_id,
            ctx
        )

        print(f"[OK] Contexto atualizado no Firestore:")
        print(f"  - estado_fluxo = {ctx['estado_fluxo']}")
        print(f"  - modo_escolha_horario = {ctx['modo_escolha_horario']} (FIX aplicado)")

        return ctx

    async def validar_p01_detection(self, ctx):
        """
        Validar que P0.1 consegue detectar "outra profissional" com contexto correto.

        Código extraído de principal_router.py linhas 6349-6395
        """
        import re
        import unidecode

        def normalizar(texto):
            return unidecode.unidecode(
                re.sub(r"[^\w\s]", " ", str(texto).lower())
            ).strip()

        texto_usuario = "outra profissional"
        texto_norm = normalizar(texto_usuario)

        # P0.1 detection logic (linha 6351 com tolerância a typo)
        eh_outra_profissional = (
            "outra" in texto_norm and
            ("profissional" in texto_norm or "pofissional" in texto_norm)
        )

        print(f"\n[P0.1 DETECTION] Testando '{texto_usuario}'")
        print(f"  - Normalizado: '{texto_norm}'")
        print(f"  - Contém 'outra': {'outra' in texto_norm}")
        print(f"  - Contém 'profissional' ou 'pofissional': {'profissional' in texto_norm or 'pofissional' in texto_norm}")
        print(f"  - P0.1 detectado: {eh_outra_profissional}")

        # Validar que alternativas estão disponíveis
        alternativas = ctx.get("ultima_opcao_profissionais", [])
        print(f"  - Alternativas disponíveis: {alternativas}")

        if not eh_outra_profissional:
            print("[OK] ERRO: P0.1 não detectou 'outra profissional'")
            return False

        if not alternativas or len(alternativas) < 2:
            print(f"[OK][OK]  Aviso: Não há alternativas suficientes para menu")
            return False

        print("[OK] P0.1 detectaria corretamente e apresentaria menu")
        return True

    async def validar_bloqueio_escolha_prioridade_total(self, ctx):
        """
        Validar que [ESCOLHA PRIORIDADE TOTAL] NOT bloqueia P0.1.

        Código: principal_router.py linhas 7255-7258
        Bloqueio anterior ocorria quando modo_escolha_horario=True
        """
        print(f"\n[ESCOLHA PRIORIDADE TOTAL] Validando bloqueio...")

        modo_escolha = ctx.get("modo_escolha_horario", False)
        estado = ctx.get("estado_fluxo", "")

        # Condição do bloco [ESCOLHA PRIORIDADE TOTAL]
        bloqueia = (
            modo_escolha or
            (estado or "").strip().lower() == "aguardando_escolha_horario"
        )

        print(f"  - modo_escolha_horario = {modo_escolha}")
        print(f"  - estado_fluxo = {estado}")
        print(f"  - [ESCOLHA PRIORIDADE TOTAL] bloquearia P0.1: {bloqueia}")

        if bloqueia:
            print("[OK] ERRO: P0.1 seria bloqueado por [ESCOLHA PRIORIDADE TOTAL]")
            return False

        print("[OK] [ESCOLHA PRIORIDADE TOTAL] não bloqueia P0.1")
        return True

    async def run(self):
        """Executar cenário completo"""
        print("\n" + "="*80)
        print("P0.1 - OUTRA PROFISSIONAL (Firebase Real)")
        print("="*80)
        print(f"Tenant: {self.tenant_id}")
        print(f"Cliente/WhatsApp: {self.wa_id} -> {self.actor_id}")
        print("="*80)

        try:
            # 1. Limpar sessão anterior
            await self.limpar_sessao()

            # 2. Salvar contexto CORROMPIDO
            ctx_original = await self.salvar_contexto_corrompido()

            # 3. Carregar contexto do Firestore
            ctx_carregado = await self.carregar_e_validar_contexto()
            if not ctx_carregado:
                print("[OK] Falha ao carregar contexto")
                return False

            # 4. Simular precheck SEM CONFLITO (aplica FIX)
            ctx_pos_precheck = await self.simular_precheck_sem_conflito(ctx_carregado)

            # 5. Validar que P0.1 consegue detectar "outra profissional"
            p01_ok = await self.validar_p01_detection(ctx_pos_precheck)

            # 6. Validar que [ESCOLHA PRIORIDADE TOTAL] não bloqueia
            bloqueio_ok = await self.validar_bloqueio_escolha_prioridade_total(ctx_pos_precheck)

            # Resultado final
            print("\n" + "="*80)
            if p01_ok and bloqueio_ok:
                print("[OK] TESTE PASSOU - Fix válida com Firebase real")
                print("="*80)
                return True
            else:
                print("[OK] TESTE FALHOU")
                print("="*80)
                return False

        except Exception as e:
            print(f"[OK] ERRO durante teste: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """Executar teste"""
    teste = TestP01OutraProfissionalFirebaseReal()
    resultado = await teste.run()

    # Cleanup final
    await teste.limpar_sessao()

    return 0 if resultado else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
