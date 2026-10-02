#!/usr/bin/env python3
"""
Teste mínimo para reiteração idêntica durante confirmação pendente.

Cenário:
- Estado: estado_fluxo="agendando", aguardando_confirmacao_agendamento=True
- Draft: corte + Bruna + amanhã 09:00
- Mensagem: "quero corte amanha as 9 com a bruna" (idêntica ao draft)

Resultado esperado:
- Permanece no mesmo fluxo (estado_fluxo="agendando")
- Draft permanece idêntico
- Confirmação continua pendente
- Não cria evento
- Não entra em ajuste_incremental
- Reapresenta a confirmação
- Retorna imediatamente

Execução:
python tests/test_reiteration_identical_draft.py
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import sys

projeto_dir = Path(__file__).parent.parent
sys.path.insert(0, str(projeto_dir))


class TesteReiteracaoIdentica:
    """Teste mínimo para reiteração idêntica de dados do draft"""

    def __init__(self):
        self.resultados = {
            "teste": "reiteration_identical_draft",
            "data_execucao": datetime.now().isoformat(),
            "ambiente": "FIREBASE_REAL",
            "cenarios_totais": 1,
            "cenarios_passou": 0,
            "cenarios_falhou": 0,
            "erros": [],
        }

    async def setup(self):
        """Preparar contexto de confirmação pendente"""
        print("\n" + "="*80)
        print("SETUP - Preparando contexto de confirmação pendente")
        print("="*80)

        try:
            from services.firebase_service_async import salvar_dado_em_path
            from utils.contexto_temporario import salvar_contexto_temporario_v2

            dono_id = "7394370553"
            cliente_id = "7371670478"

            amanhã = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            data_hora = f"{amanhã}T09:00:00"

            # Contexto: confirmação pendente com draft
            ctx_confirmacao = {
                "estado_fluxo": "agendando",
                "aguardando_confirmacao_agendamento": True,
                "tem_draft": True,
                "draft_agendamento": {
                    "profissional": "Bruna",
                    "servico": "corte",
                    "data_hora": data_hora,
                },
                "dados_confirmacao_agendamento": {
                    "profissional": "Bruna",
                    "servico": "corte",
                    "data_hora": data_hora,
                    "duracao": 30,
                    "descricao": "Corte com Bruna",
                },
                "profissional_escolhido": "Bruna",
                "servico": "corte",
                "data_hora": data_hora,
                "intencao_conversacional": "ajuste_incremental",
                "objetivo_conversacional": "ajustar_draft_existente",
                "tipo_ajuste_incremental": "profissional",
            }

            await salvar_contexto_temporario_v2(dono_id, cliente_id, ctx_confirmacao)
            print(f"\n[SETUP] Contexto salvo com sucesso")
            print(f"  dono_id: {dono_id}")
            print(f"  cliente_id: {cliente_id}")
            print(f"  estado_fluxo: agendando")
            print(f"  aguardando_confirmacao: True")
            print(f"  draft: corte + Bruna + {data_hora}")

            return dono_id, cliente_id, ctx_confirmacao

        except Exception as e:
            print(f"\n[ERRO] Setup falhou: {e}")
            self.resultados["erros"].append(str(e))
            raise

    async def testar_reiteration(self, dono_id, cliente_id, ctx_esperado):
        """
        Testar reiteração idêntica:
        - Mensagem: "quero corte amanha as 9 com a bruna"
        - Deve reapresentar confirmação, não criar novo evento
        """
        print("\n" + "="*80)
        print("TESTE - Reiteração idêntica de dados do draft")
        print("="*80)

        try:
            from router.principal_router import roteador_principal
            from utils.contexto_temporario import carregar_contexto_temporario_v2

            # Simular mensagem do usuário (idêntica ao draft)
            texto_usuario = "quero corte amanha as 9 com a bruna"

            print(f"\n[TESTE] Enviando mensagem: {texto_usuario!r}")
            print(f"[TESTE] Estado esperado:")
            print(f"  - estado_fluxo: agendando (deve PRESERVAR)")
            print(f"  - draft: {ctx_esperado['draft_agendamento']} (deve PRESERVAR)")
            print(f"  - aguardando_confirmacao: True (deve PRESERVAR)")
            print(f"  - Comportamento: reapresentar confirmação")

            # Executar router com mensagem
            resultado = await roteador_principal(
                mensagem=texto_usuario,
                user_id=cliente_id,
                update=None,  # WhatsApp
                context=None,
                dono_id=dono_id,
                cliente_id=cliente_id
            )

            # Carregar contexto após execução
            ctx_depois = await carregar_contexto_temporario_v2(dono_id, cliente_id)

            # Validações
            passou = True
            validacoes = []

            # V1: Estado_fluxo preservado
            if ctx_depois.get("estado_fluxo") == "agendando":
                validacoes.append("[PASS] estado_fluxo='agendando' PRESERVADO")
            else:
                validacoes.append(f"[FAIL] estado_fluxo={ctx_depois.get('estado_fluxo')} (esperado: agendando)")
                passou = False

            # V2: Draft preservado
            draft_antes = ctx_esperado.get("draft_agendamento", {})
            draft_depois = ctx_depois.get("draft_agendamento", {})
            if draft_antes == draft_depois:
                validacoes.append("[PASS] draft_agendamento IDÊNTICO")
            else:
                validacoes.append(f"[FAIL] draft alterado: {draft_antes} → {draft_depois}")
                passou = False

            # V3: Aguardando confirmação preservado
            if ctx_depois.get("aguardando_confirmacao_agendamento") is True:
                validacoes.append("[PASS] aguardando_confirmacao_agendamento=True PRESERVADO")
            else:
                validacoes.append(f"[FAIL] aguardando_confirmacao={ctx_depois.get('aguardando_confirmacao_agendamento')}")
                passou = False

            # V4: Resposta contém mensagem de confirmação
            resposta = resultado.get("resposta", "")
            if "Confirmando:" in resposta and "Responda *sim*" in resposta:
                validacoes.append("[PASS] Confirmação REAPRESENTADA")
            else:
                validacoes.append(f"[FAIL] Resposta não é confirmação: {resposta[:100]}")
                passou = False

            # V5: Early return (handled=True)
            if resultado.get("handled") is True:
                validacoes.append("[PASS] Early return executado (handled=True)")
            else:
                validacoes.append(f"[FAIL] handled={resultado.get('handled')}")
                passou = False

            # Imprimir resultados
            print(f"\n[VALIDAÇÕES]")
            for v in validacoes:
                print(f"  {v}")

            if passou:
                print(f"\n[RESULTADO] ✅ TESTE PASSOU")
                self.resultados["cenarios_passou"] += 1
            else:
                print(f"\n[RESULTADO] ❌ TESTE FALHOU")
                self.resultados["cenarios_falhou"] += 1
                self.resultados["erros"].extend(validacoes)

            self.resultados["cenarios_totais"] = 1
            self.resultados["cenarios_executados"] = 1

            return passou

        except Exception as e:
            print(f"\n[ERRO] Teste falhou com exceção: {e}")
            import traceback
            traceback.print_exc()
            self.resultados["erros"].append(f"Exceção: {str(e)}")
            self.resultados["cenarios_falhou"] += 1
            return False

    async def executar(self):
        """Executar bateria de testes"""
        print("\n" + "="*80)
        print("BATERIA MÍNIMA - Reiteração Idêntica Durante Confirmação Pendente")
        print("="*80)

        try:
            # Setup
            dono_id, cliente_id, ctx_esperado = await self.setup()

            # Teste
            passou = await self.testar_reiteration(dono_id, cliente_id, ctx_esperado)

            # Resultado final
            print("\n" + "="*80)
            print("RESUMO")
            print("="*80)
            print(f"\nTestes executados: {self.resultados['cenarios_executados']}")
            print(f"Testes passaram: {self.resultados['cenarios_passou']}")
            print(f"Testes falharam: {self.resultados['cenarios_falhou']}")

            if self.resultados["erros"]:
                print(f"\nErros:")
                for erro in self.resultados["erros"]:
                    print(f"  - {erro}")

            status_final = "✅ PASSOU" if passou else "❌ FALHOU"
            print(f"\nStatus: {status_final}")
            print("="*80 + "\n")

            return passou

        except Exception as e:
            print(f"\n[ERRO CRÍTICO] {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    teste = TesteReiteracaoIdentica()
    sucesso = await teste.executar()
    sys.exit(0 if sucesso else 1)


if __name__ == "__main__":
    asyncio.run(main())
