#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTE CRÍTICO — ALTERAÇÃO DE DURAÇÃO PRÉ-CONFIRMAÇÃO (FIREBASE REAL)
Objetivo: Validar se o sistema consegue detectar mudança de duração ANTES da confirmação

CENÁRIO:
  1. Cliente quer: Corte às 14h (45 min) → 14:00-14:45
  2. MAS MUDA DE IDEIA ANTES DE CONFIRMAR
  3. Novo desejo: Corte + Hidratação (90 min) → 14:00-15:30
  4. Sistema PRECISA revalidar conflitos com novo intervalo

TESTE COM FIREBASE REAL:
  - Criar eventos reais em Firestore com criar_com_lock_real()
  - Validar com verificar_conflito_e_sugestoes_profissional()
  - ETAPA CRÍTICA: Detectar novo conflito quando duração muda

STATUS: Isto revela se o sistema está preparado para alteração de agendamento
"""

import asyncio
import json
import sys
import traceback
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.firebase_service_async import (
    atualizar_dado_em_path,
    obter_id_dono,
)
from services.event_service_async import (
    verificar_conflito_e_sugestoes_profissional,
)
from services.agenda_lock_service import criar_evento_com_lock as criar_com_lock_real


class TesteAlteracaoDuracaoPreConfirmacao:
    """Teste Firebase Real: Cliente muda serviço (duração) ANTES de confirmar"""

    def __init__(self):
        self.tenant_id = "teste_alteracao_duracao_dono"
        self.cliente_id = "teste_cliente_alteracao_001"
        self.profissional = "Carla"
        self.data_teste = datetime.now().strftime("%Y-%m-%d")

        self.resultado = {
            "timestamp": datetime.now().isoformat(),
            "cenario": "Cliente muda de Corte (45 min) para Corte+Hidratacao (90 min) PRE-CONFIRMACAO",
            "tenant_id": self.tenant_id,
            "cliente_id": self.cliente_id,
            "data_teste": self.data_teste,
            "etapas": [],
            "resumo": {
                "total_etapas": 3,
                "passaram": 0,
                "falharam": 0,
            }
        }

    async def setup_cliente_teste(self):
        """SETUP: Registrar cliente e tenant em Firestore"""
        print("\n" + "="*80)
        print("SETUP: Registrando cliente e tenant em Firestore")
        print("="*80)

        print(f"\nTenant (dono): {self.tenant_id}")
        print(f"Cliente: {self.cliente_id}")
        print(f"Profissional: {self.profissional}")
        print(f"Data teste: {self.data_teste}")

        # Setup: Registrar cliente com id_negocio correto
        cliente_path = f"Clientes/{self.cliente_id}"
        cliente_doc = {
            "nome": "Cliente Teste Alteracao Duracao",
            "id_negocio": self.tenant_id,
            "email": "teste@alteracao.com",
            "tipo_usuario": "cliente"
        }

        print(f"\n[SETUP] Criando cliente: {cliente_path}")
        resultado_criar = await atualizar_dado_em_path(cliente_path, cliente_doc)
        print(f"[SETUP] Resultado: {resultado_criar}")

        # Validar que obter_id_dono retorna o tenant correto
        print(f"\n[SETUP] Validando obter_id_dono...")
        tenant_retornado = await obter_id_dono(self.cliente_id)
        print(f"[SETUP] obter_id_dono('{self.cliente_id}') = '{tenant_retornado}'")

        if tenant_retornado != self.tenant_id:
            raise ValueError(
                f"Setup falhou: obter_id_dono retornou '{tenant_retornado}' "
                f"em vez de '{self.tenant_id}'"
            )

        print(f"\n[OK] Setup concluido com sucesso")

    async def etapa_1_criar_evento_bloqueante(self):
        """ETAPA 1: Criar evento bloqueante em Firestore (14:30-15:00)"""
        etapa = {
            "numero": 1,
            "nome": "Criar Evento Bloqueante (Manicure 14:30-15:00)",
            "status": "INICIANDO",
            "detalhes": {}
        }

        try:
            print("\n" + "="*80)
            print("ETAPA 1: Criar Evento Bloqueante em Firestore")
            print("="*80)
            print("\nSimula: Outro cliente já agendou Manicure com Carla")
            print("  Manicure: 14:30-15:00 (30 min)")

            evento_bloqueante = {
                "descricao": "Manicure (outro cliente)",
                "profissional": "Carla",
                "servico": "Manicure",
                "data": self.data_teste,
                "hora_inicio": "14:30",
                "hora_fim": "15:00",
                "duracao": 30,
                "duracao_minutos": 30,
                "confirmado": True,
                "status": "confirmado",
                "cliente_id": "outro_cliente_123",
                "cliente_nome": "Maria"
            }

            print(f"\n[PRÉ] Criando evento bloqueante em Firestore...")
            resultado_pre = await criar_com_lock_real(
                dono_id=self.tenant_id,
                evento=evento_bloqueante,
                event_id=f"evt_bloqueante_{self.data_teste}_1430"
            )

            print(f"[PRÉ] Resultado: {resultado_pre}")

            passou = resultado_pre.get("ok", False)
            etapa["status"] = "PASSOU" if passou else "FALHOU"
            etapa["detalhes"]["evento_criado"] = resultado_pre.get("ok", False)
            etapa["detalhes"]["resultado"] = resultado_pre

            if passou:
                print("[OK] ETAPA 1 PASSOU: Evento bloqueante criado em Firestore")
                self.resultado["resumo"]["passaram"] += 1
            else:
                print("[FALHA] ETAPA 1 FALHOU: Evento bloqueante não foi criado")
                self.resultado["resumo"]["falharam"] += 1

        except Exception as e:
            print(f"[FALHA] ERRO na Etapa 1: {e}")
            etapa["status"] = "ERRO"
            etapa["detalhes"]["erro"] = str(e)
            etapa["detalhes"]["erro_traceback"] = traceback.format_exc()
            self.resultado["resumo"]["falharam"] += 1

        self.resultado["etapas"].append(etapa)

        # Aguardar replicacao Firestore (eventual consistency)
        print("\n[WAIT] Aguardando 2s para replicacao Firestore...")
        await asyncio.sleep(2)

        return etapa["detalhes"].get("evento_criado", False)

    async def etapa_2_cliente_quer_corte_simples(self):
        """ETAPA 2: Validar disponibilidade para Corte 14:00-14:45 (45 min)"""
        etapa = {
            "numero": 2,
            "nome": "Validar Corte 14:00-14:45 (45 min)",
            "status": "INICIANDO",
            "detalhes": {}
        }

        try:
            print("\n" + "="*80)
            print("ETAPA 2: Cliente Propõe Corte (45 min)")
            print("="*80)
            print("\nCliente: 'Quero um corte às 14h'")
            print("  Serviço: Corte")
            print("  Horário: 14:00")
            print("  Duração: 45 min")
            print("  Intervalo: 14:00-14:45")

            print(f"\n[VALIDAÇÃO] Verificando disponibilidade...")

            resultado = await verificar_conflito_e_sugestoes_profissional(
                user_id=self.tenant_id,
                data=self.data_teste,
                hora_inicio="14:00",
                duracao_min=45,
                profissional="Carla",
                servico="Corte"
            )

            tem_conflito = resultado.get("conflito", False)
            sugestoes = resultado.get("sugestoes", [])

            print(f"\n📊 Resultado:")
            print(f"   Conflito: {tem_conflito}")
            print(f"   Intervalo validado: 14:00-14:45 (45 min)")
            print(f"   Sugestões: {len(sugestoes)}")

            etapa["status"] = "PASSOU"
            etapa["detalhes"]["conflito_etapa2"] = tem_conflito
            etapa["detalhes"]["intervalo"] = "14:00-14:45"
            etapa["detalhes"]["duracao"] = 45
            etapa["detalhes"]["resultado"] = resultado

            print("[OK] ETAPA 2 PASSOU: Validação concluída")
            self.resultado["resumo"]["passaram"] += 1

        except Exception as e:
            print(f"[FALHA] ERRO na Etapa 2: {e}")
            etapa["status"] = "ERRO"
            etapa["detalhes"]["erro"] = str(e)
            etapa["detalhes"]["erro_traceback"] = traceback.format_exc()
            self.resultado["resumo"]["falharam"] += 1

        self.resultado["etapas"].append(etapa)
        return etapa["status"] == "PASSOU"

    async def etapa_3_cliente_muda_de_ideia(self):
        """ETAPA 3: CRÍTICA — Cliente muda para Corte+Hidratação (90 min)"""
        etapa = {
            "numero": 3,
            "nome": "CRÍTICA: Cliente ALTERA para Corte+Hidratação 14:00-15:30 (90 min)",
            "status": "INICIANDO",
            "detalhes": {}
        }

        try:
            print("\n" + "="*80)
            print("ETAPA 3: CRÍTICA — Cliente MUDA DE IDEIA (PRÉ-CONFIRMAÇÃO)")
            print("="*80)
            print("\nCliente: 'Na verdade, quero corte + hidratação'")
            print("  Novo serviço: Corte + Hidratação")
            print("  Horário: 14:00 (MANTÉM)")
            print("  Duração: 90 min (MUDOU DE 45!)")
            print("  Novo intervalo: 14:00-15:30")

            print("\n⚠️  PERGUNTA CRÍTICA:")
            print("    Manicure: 14:30-15:00")
            print("    Novo intervalo: 14:00-15:30")
            print("    SOBREPOSIÇÃO: 30 min (14:30-15:00)")
            print("    Motor consegue detectar?")

            print(f"\n[REVALIDAÇÃO] Verificando com nova duração (90 min)...")

            resultado = await verificar_conflito_e_sugestoes_profissional(
                user_id=self.tenant_id,
                data=self.data_teste,
                hora_inicio="14:00",
                duracao_min=90,
                profissional="Carla",
                servico="Corte + Hidratacao"
            )

            tem_conflito = resultado.get("conflito", False)
            sugestoes = resultado.get("sugestoes", [])

            print(f"\n📊 Resultado da REVALIDAÇÃO:")
            print(f"   Conflito DETECTADO: {tem_conflito}")
            print(f"   Intervalo novo: 14:00-15:30 (90 min)")
            print(f"   Sugestões oferecidas: {len(sugestoes)}")

            # VALIDAÇÃO CRÍTICA
            if not tem_conflito:
                print(f"\n   [ERRO] PROBLEMA CRITICO!")
                print(f"      Motor NÃO detectou conflito com Manicure 14:30-15:00")
                print(f"      DEVERIA ter detectado 30 min de sobreposição")
                print(f"\n   CONCLUSÃO: Sistema NÃO está pronto para reagendamento")
                etapa["status"] = "FALHOU"
                self.resultado["resumo"]["falharam"] += 1
            else:
                print(f"\n   [OK] FUNCIONOU CORRETAMENTE!")
                print(f"      Motor detectou conflito com sucesso")
                print(f"      Sistema pode oferecer alternativas")

                if sugestoes:
                    print(f"\n   Sugestões oferecidas:")
                    for i, sugestao in enumerate(sugestoes[:3], 1):
                        print(f"      {i}. {sugestao}")

                print(f"\n   CONCLUSÃO: Sistema ESTÁ PRONTO para reagendamento")
                etapa["status"] = "PASSOU"
                self.resultado["resumo"]["passaram"] += 1

            etapa["detalhes"]["conflito_detectado"] = tem_conflito
            etapa["detalhes"]["intervalo"] = "14:00-15:30"
            etapa["detalhes"]["duracao"] = 90
            etapa["detalhes"]["duracao_mudou"] = True
            etapa["detalhes"]["sugestoes_oferecidas"] = len(sugestoes)
            etapa["detalhes"]["resultado"] = resultado

        except Exception as e:
            print(f"[FALHA] ERRO na Etapa 3: {e}")
            etapa["status"] = "ERRO"
            etapa["detalhes"]["erro"] = str(e)
            etapa["detalhes"]["erro_traceback"] = traceback.format_exc()
            self.resultado["resumo"]["falharam"] += 1

        self.resultado["etapas"].append(etapa)
        return etapa["detalhes"].get("conflito_detectado", False)

    async def conclusao(self):
        """Analisar resultado final"""
        print("\n" + "="*80)
        print("CONCLUSÃO DO TESTE")
        print("="*80)

        print(f"\nResumo:")
        print(f"  Total etapas: {self.resultado['resumo']['total_etapas']}")
        print(f"  Passaram: {self.resultado['resumo']['passaram']}")
        print(f"  Falharam: {self.resultado['resumo']['falharam']}")

        etapa_3 = self.resultado["etapas"][2] if len(self.resultado["etapas"]) > 2 else {}
        conflito_detectado = etapa_3.get("detalhes", {}).get("conflito_detectado", False)

        if conflito_detectado:
            print(f"\n✅ SISTEMA ESTÁ PRONTO PARA REAGENDAMENTO")
            print(f"   Motor revalida corretamente quando duração muda")
            print(f"   Implementação de alteração de agendamento é VIÁVEL")
            self.resultado["conclusao"] = "VIÁVEL: Motor detecta conflitos com duração alterada"
        else:
            print(f"\n[FALHA] BLOQUEADOR CRITICO")
            print(f"   Motor NAO revalida conflitos quando duracao muda")
            print(f"   Implementacao de alteracao é INSEGURA")
            self.resultado["conclusao"] = "BLOQUEADO: Motor não valida duração alterada"

        return self.resultado

    async def executar(self):
        """Executar teste completo"""
        try:
            await self.setup_cliente_teste()
            await self.etapa_1_criar_evento_bloqueante()
            await self.etapa_2_cliente_quer_corte_simples()
            await self.etapa_3_cliente_muda_de_ideia()
            resultado_final = await self.conclusao()

            # Salvar resultado
            print(f"\n📝 Resultado completo (JSON):")
            print(json.dumps(resultado_final, indent=2, ensure_ascii=False))

            return resultado_final

        except Exception as e:
            print(f"\n[ERRO] ERRO CRITICO DURANTE TESTE: {e}")
            print(traceback.format_exc())
            return {"erro": str(e), "resultado": "ABORTADO"}


async def main():
    """Executar teste com Firebase real"""
    teste = TesteAlteracaoDuracaoPreConfirmacao()
    await teste.executar()


if __name__ == "__main__":
    asyncio.run(main())
