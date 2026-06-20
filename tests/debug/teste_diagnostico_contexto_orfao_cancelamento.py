#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTE DIAGNÓSTICO — Contexto Órfão Após Cancelamento

Objetivo:
Provar que ctx.pop(...) + merge=True não remove campos do Firestore.

Fluxo:
1. Criar contexto sujo em Firestore
2. Carregar e validar existência
3. Simular limpeza atual (pop + merge)
4. Recarregar e verificar se campos ainda existem
5. Se existem, testar patch com DELETE_FIELD
6. Gerar relatório JSON
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Adicionar pasta raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from google.cloud import firestore
from services.firebase_service_async import (
    atualizar_dado_em_path,
    buscar_dado_em_path,
    deletar_dado_em_path,
)


class TesteDiagnosticoContextoOrfao:
    """Teste diagnóstico do problema de contexto órfão"""

    def __init__(self):
        self.tenant_id = "dono_test_123"
        self.actor_id = "user_test_7371670478"
        self.path_v2 = f"Clientes/{self.tenant_id}/Sessoes/{self.actor_id}"
        self.resultado = {
            "timestamp": datetime.now().isoformat(),
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
            "path_v2": self.path_v2,
            "etapas": [],
        }

    async def etapa_1_criar_contexto_sujo(self):
        """Etapa 1: Criar contexto sujo em Firestore"""
        print("\n" + "=" * 80)
        print("ETAPA 1: Criar Contexto Sujo")
        print("=" * 80)

        contexto_sujo = {
            "estado_fluxo": "aguardando_confirmacao_cancelamento",
            "cancelamento_pendente": {
                "evento_id": "ev_001",
                "resumo_evento": {"descricao": "Corte com Bruna"},
            },
            "draft_agendamento": {
                "profissional": "Bruna",
                "servico": "Corte",
                "data_hora": "2026-06-20T11:00:00",
            },
            "dados_confirmacao_agendamento": {
                "profissional": "Bruna",
                "servico": "Corte",
                "data_hora": "2026-06-20T11:00:00",
            },
            "aguardando_confirmacao_agendamento": True,
            "_tenant_id_guard": self.tenant_id,
            "_actor_id": self.actor_id,
        }

        resultado = await atualizar_dado_em_path(self.path_v2, contexto_sujo)
        print(f"[OK] Contexto sujo criado em {self.path_v2}")
        print(f"[OK] Resultado: {resultado}")

        self.resultado["etapas"].append(
            {
                "numero": 1,
                "nome": "Criar Contexto Sujo",
                "status": "OK",
                "dados": contexto_sujo,
            }
        )

        return contexto_sujo

    async def etapa_2_carregar_e_validar(self):
        """Etapa 2: Carregar e validar que os campos existem"""
        print("\n" + "=" * 80)
        print("ETAPA 2: Carregar e Validar Contexto Sujo")
        print("=" * 80)

        contexto = await buscar_dado_em_path(self.path_v2)
        print(f"[OK] Contexto carregado de {self.path_v2}")
        print(f"[DEBUG] Chaves presentes: {list(contexto.keys())}")

        validacoes = {
            "estado_fluxo": contexto.get("estado_fluxo") == "aguardando_confirmacao_cancelamento",
            "cancelamento_pendente_existe": "cancelamento_pendente" in contexto,
            "draft_agendamento_existe": "draft_agendamento" in contexto,
            "dados_confirmacao_existe": "dados_confirmacao_agendamento" in contexto,
            "aguardando_confirmacao": contexto.get("aguardando_confirmacao_agendamento") == True,
        }

        print(f"\n[VALIDAÇÃO]")
        for campo, resultado in validacoes.items():
            status = "✅" if resultado else "❌"
            print(f"  {status} {campo}: {resultado}")

        self.resultado["etapas"].append(
            {
                "numero": 2,
                "nome": "Carregar e Validar",
                "status": "OK",
                "validacoes": validacoes,
            }
        )

        return contexto, validacoes

    async def etapa_3_limpeza_atual_pop_merge(self, contexto):
        """Etapa 3: Simular limpeza atual com pop + merge"""
        print("\n" + "=" * 80)
        print("ETAPA 3: Limpeza Atual (pop + merge=True)")
        print("=" * 80)

        # Simular exatamente o que o handler faz
        print("[DEBUG] Antes da limpeza local:")
        print(f"  - cancelamento_pendente: {bool(contexto.get('cancelamento_pendente'))}")
        print(f"  - draft_agendamento: {bool(contexto.get('draft_agendamento'))}")
        print(f"  - dados_confirmacao: {bool(contexto.get('dados_confirmacao_agendamento'))}")

        # Pop local (isso remove da dict Python)
        contexto.pop("cancelamento_pendente", None)
        contexto.pop("draft_agendamento", None)
        contexto.pop("dados_confirmacao_agendamento", None)
        contexto["estado_fluxo"] = "idle"
        contexto["aguardando_confirmacao_agendamento"] = False

        print("\n[DEBUG] Depois da limpeza local:")
        print(f"  - cancelamento_pendente: {bool(contexto.get('cancelamento_pendente'))}")
        print(f"  - draft_agendamento: {bool(contexto.get('draft_agendamento'))}")
        print(f"  - dados_confirmacao: {bool(contexto.get('dados_confirmacao_agendamento'))}")
        print(f"  - estado_fluxo: {contexto.get('estado_fluxo')}")

        # Salvar com merge=True (comportamento atual de atualizar_dado_em_path)
        print("\n[DEBUG] Salvando com merge=True (comportamento atual)...")
        resultado = await atualizar_dado_em_path(self.path_v2, contexto)
        print(f"[OK] Salvo. Resultado: {resultado}")

        self.resultado["etapas"].append(
            {
                "numero": 3,
                "nome": "Limpeza Atual (pop + merge)",
                "status": "OK",
                "metodo": "ctx.pop(...) + atualizar_dado_em_path(merge=True)",
                "contexto_local_apos": contexto,
            }
        )

        return contexto

    async def etapa_4_recarregar_verificar_problema(self):
        """Etapa 4: Recarregar e verificar se campos ainda existem"""
        print("\n" + "=" * 80)
        print("ETAPA 4: Recarregar após Limpeza Atual")
        print("=" * 80)

        contexto_recarregado = await buscar_dado_em_path(self.path_v2)
        print(f"[DEBUG] Contexto recarregado do Firestore")
        print(f"[DEBUG] Chaves presentes: {list(contexto_recarregado.keys())}")

        problemas = {
            "cancelamento_pendente_ainda_existe": "cancelamento_pendente" in contexto_recarregado,
            "draft_agendamento_ainda_existe": "draft_agendamento" in contexto_recarregado,
            "dados_confirmacao_ainda_existe": "dados_confirmacao_agendamento" in contexto_recarregado,
            "estado_fluxo_correto": contexto_recarregado.get("estado_fluxo") == "idle",
        }

        print(f"\n[VERIFICAÇÃO PÓS-LIMPEZA]")
        tem_problema = False
        for campo, existe in problemas.items():
            status = "❌ PROBLEMA!" if existe and "ainda_existe" in campo else "✅"
            print(f"  {status} {campo}: {existe}")
            if existe and "ainda_existe" in campo:
                tem_problema = True

        self.resultado["etapas"].append(
            {
                "numero": 4,
                "nome": "Verificar Após Limpeza Atual",
                "status": "OK",
                "problema_encontrado": tem_problema,
                "problemas": problemas,
                "contexto_recarregado": contexto_recarregado,
            }
        )

        return contexto_recarregado, tem_problema

    async def etapa_5_patch_com_delete_field(self):
        """Etapa 5: Testar patch correto com DELETE_FIELD"""
        print("\n" + "=" * 80)
        print("ETAPA 5: Patch com DELETE_FIELD")
        print("=" * 80)

        # Usar DELETE_FIELD para remover campos explicitamente
        delete_field = firestore.DELETE_FIELD

        payload_patch = {
            "estado_fluxo": "idle",
            "aguardando_confirmacao_agendamento": False,
            "cancelamento_pendente": delete_field,  # REMOVER EXPLICITAMENTE
            "draft_agendamento": delete_field,      # REMOVER EXPLICITAMENTE
            "dados_confirmacao_agendamento": delete_field,  # REMOVER EXPLICITAMENTE
        }

        print(f"[DEBUG] Payload patch com DELETE_FIELD:")
        for chave, valor in payload_patch.items():
            if valor is firestore.DELETE_FIELD:
                print(f"  - {chave}: DELETE_FIELD")
            else:
                print(f"  - {chave}: {valor}")

        # Atualizar usando o mecanismo do projeto (atualizar_dado_em_path)
        print(f"[DEBUG] Aplicando payload com atualizar_dado_em_path()...")
        resultado = await atualizar_dado_em_path(self.path_v2, payload_patch)
        print(f"[OK] Patch com DELETE_FIELD aplicado. Resultado: {resultado}")

        self.resultado["etapas"].append(
            {
                "numero": 5,
                "nome": "Patch com DELETE_FIELD",
                "status": "OK",
                "metodo": "atualizar_dado_em_path() com DELETE_FIELD explícito",
                "payload": str(payload_patch),
            }
        )

    async def etapa_6_recarregar_validar_patch(self):
        """Etapa 6: Recarregar e validar patch com DELETE_FIELD"""
        print("\n" + "=" * 80)
        print("ETAPA 6: Validar Patch com DELETE_FIELD")
        print("=" * 80)

        contexto_final = await buscar_dado_em_path(self.path_v2)
        print(f"[DEBUG] Contexto final recarregado")
        print(f"[DEBUG] Chaves presentes: {list(contexto_final.keys())}")

        validacoes_finais = {
            "estado_fluxo_idle": contexto_final.get("estado_fluxo") == "idle",
            "cancelamento_pendente_removido": "cancelamento_pendente" not in contexto_final,
            "draft_agendamento_removido": "draft_agendamento" not in contexto_final,
            "dados_confirmacao_removido": "dados_confirmacao_agendamento" not in contexto_final,
            "aguardando_confirmacao_false": contexto_final.get("aguardando_confirmacao_agendamento") == False,
        }

        print(f"\n[VALIDAÇÃO PATCH]")
        todas_ok = True
        for campo, resultado in validacoes_finais.items():
            status = "✅" if resultado else "❌"
            print(f"  {status} {campo}: {resultado}")
            if not resultado:
                todas_ok = False

        self.resultado["etapas"].append(
            {
                "numero": 6,
                "nome": "Validar Patch com DELETE_FIELD",
                "status": "OK",
                "todas_validacoes_ok": todas_ok,
                "validacoes": validacoes_finais,
                "contexto_final": contexto_final,
            }
        )

        return contexto_final, todas_ok

    async def etapa_7_limpar_firestore(self):
        """Etapa 7: Limpar dados de teste do Firestore"""
        print("\n" + "=" * 80)
        print("ETAPA 7: Limpeza de Teste")
        print("=" * 80)

        # Usar a função do projeto para deletar
        await deletar_dado_em_path(self.path_v2)
        print(f"[OK] Documento de teste removido de {self.path_v2}")

        self.resultado["etapas"].append(
            {
                "numero": 7,
                "nome": "Limpeza",
                "status": "OK",
            }
        )

    async def run(self):
        """Executar diagnóstico completo"""
        print("\n" + "=" * 80)
        print("TESTE DIAGNÓSTICO — Contexto Órfão Após Cancelamento")
        print("=" * 80)
        print(f"\nTenant: {self.tenant_id}")
        print(f"Actor: {self.actor_id}")
        print(f"Path: {self.path_v2}")

        try:
            # Etapa 1: Criar contexto sujo
            await self.etapa_1_criar_contexto_sujo()

            # Etapa 2: Carregar e validar
            contexto, validacoes = await self.etapa_2_carregar_e_validar()

            # Etapa 3: Limpeza atual (pop + merge)
            contexto_limpo = await self.etapa_3_limpeza_atual_pop_merge(contexto)

            # Etapa 4: Recarregar e verificar problema
            contexto_recarregado, tem_problema = await self.etapa_4_recarregar_verificar_problema()

            # Etapa 5-6: Testar patch com DELETE_FIELD
            await self.etapa_5_patch_com_delete_field()
            contexto_final, patch_ok = await self.etapa_6_recarregar_validar_patch()

            # Etapa 7: Limpeza
            await self.etapa_7_limpar_firestore()

            # Gerar relatório final
            self._gerar_relatorio_final(tem_problema, patch_ok)

        except Exception as e:
            print(f"\n[ERRO] {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            self.resultado["erro"] = str(e)

    def _gerar_relatorio_final(self, tem_problema, patch_ok):
        """Gerar relatório final"""
        print("\n" + "=" * 80)
        print("RESULTADO FINAL")
        print("=" * 80)

        print(f"\n[DIAGNÓSTICO]")
        print(f"  1. Save pós-cancelamento: {'LEGADO (com pop+merge)' if True else 'V2'}")
        print(f"  2. Load seguinte: Firestore (verificou campos)")
        print(f"  3. campos foram removidos: {'NÃO' if tem_problema else 'SIM'}")
        print(f"  4. Problema identificado: {'ctx.pop + merge=True não deleta' if tem_problema else 'NENHUM PROBLEMA'}")
        print(f"  5. Patch DELETE_FIELD funciona: {'SIM' if patch_ok else 'NÃO'}")

        print(f"\n[CONCLUSÃO]")
        if tem_problema:
            print(f"  ✅ HIPÓTESE CONFIRMADA: merge=True não remove campos ausentes")
            print(f"  ✅ SOLUÇÃO: Usar DELETE_FIELD explicitamente")
            print(f"  ✅ IMPLEMENTAÇÃO: Adicionar DELETE_FIELD em salvar_contexto_temporario()")
        else:
            print(f"  ❌ PROBLEMA NÃO ENCONTRADO: merge=True funciona corretamente")
            print(f"  ⚠️ CAUSA RAIZ PODE SER: Cache, carregamento incorreto ou outro")

        self.resultado["conclusao"] = {
            "problema_encontrado": tem_problema,
            "hipotese_confirmada": tem_problema,
            "patch_delete_field_funciona": patch_ok,
            "recomendacao": "Usar DELETE_FIELD em salvar_contexto_temporario()" if tem_problema else "Investigar causa alternativa",
        }

        # Salvar JSON
        self._salvar_resultado_json()

    def _salvar_resultado_json(self):
        """Salvar resultado em JSON"""
        json_path = Path(__file__).parent / "resultado_diagnostico_contexto_orfao_cancelamento.json"

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.resultado, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n[OK] Resultado salvo em: {json_path}")


async def main():
    """Função principal"""
    teste = TesteDiagnosticoContextoOrfao()
    await teste.run()


if __name__ == "__main__":
    asyncio.run(main())
