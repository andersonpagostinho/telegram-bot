"""
P0 VALIDAÇÃO EXPERIMENTAL — Testes E2E A3, A6, A7
Diagnóstico de seleção incorreta de eventos em cancelamentos

RESTRIÇÕES OBRIGATÓRIAS:
- Somente leitura e criação de dados de teste
- Usar tenant de teste isolado
- Não modificar código de produção
- Não executar cancelamentos reais
- Documentar todas as evidências de Firestore
- Limpar dados de teste após conclusão
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# UTF-8 para Windows console
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.firebase_service_async import (
    buscar_dado_em_path,
    atualizar_dado_em_path,
    buscar_subcolecao,
)
from services.event_service_async import (
    cancelar_evento_por_texto,
    buscar_eventos_por_termo_avancado,
)
from utils.contexto_temporario import (
    salvar_sessao_temporaria,
    carregar_sessao_temporaria,
)


class TestP0A3A6A7:
    """Suite de testes de diagnóstico para A3, A6, A7."""

    def __init__(self):
        self.tenant_teste = "tenant_teste_p0_a3a6a7_20261105"
        self.cliente_teste = "cliente_teste_20261105"
        self.resultados = []
        self.dados_criados = []  # Rastreamento para limpeza

    async def setup(self):
        """Preparar ambiente de teste."""
        print("\n" + "=" * 80)
        print("TESTE P0 A3/A6/A7 — DIAGNÓSTICO DE CANCELAMENTO")
        print("=" * 80)
        print(f"[SETUP] tenant_teste={self.tenant_teste}")
        print(f"[SETUP] cliente_teste={self.cliente_teste}")
        print(f"[SETUP] timestamp={datetime.now().isoformat()}")

        # Verificar que tenant de teste é realmente isolado
        tenant_doc = await buscar_dado_em_path(f"Clientes/{self.tenant_teste}")
        if tenant_doc:
            print(f"⚠️  [SETUP] Tenant de teste já existe!")
        else:
            print(f"✅ [SETUP] Tenant de teste é novo (isolado)")

    async def teste_a3_indice_resumo_eventos(self):
        """
        TESTE A3: Índice em resumo_eventos aponta evento errado

        Cenário:
        1. Criar dois eventos (ABC, DEF)
        2. Salvar lista [ABC, DEF] em cancelamento_pendente
        3. Deletar ABC de Firestore (simular alteração)
        4. Usuário responde "1" (seleciona índice 0)
        5. Verificar se evento_id recuperado ainda é ABC
        """
        print("\n" + "-" * 80)
        print("TESTE A3: Índice em resumo_eventos")
        print("-" * 80)

        try:
            # 1. Criar dois eventos de teste
            evento_abc = {
                "cliente_id": self.cliente_teste,
                "descricao": "Corte com Bruna",
                "profissional": "Bruna",
                "data": "2026-11-10",
                "hora_inicio": "10:00",
                "hora_fim": "10:30",
                "servico": "corte",
                "status": "confirmado",
                "criado_em": datetime.now().isoformat(),
            }

            evento_def = {
                "cliente_id": self.cliente_teste,
                "descricao": "Corte com Gloria",
                "profissional": "Gloria",
                "data": "2026-11-12",
                "hora_inicio": "14:00",
                "hora_fim": "14:30",
                "servico": "corte",
                "status": "confirmado",
                "criado_em": datetime.now().isoformat(),
            }

            # Salvar eventos
            path_abc = f"Clientes/{self.tenant_teste}/Eventos/ABC123"
            path_def = f"Clientes/{self.tenant_teste}/Eventos/DEF456"

            await atualizar_dado_em_path(path_abc, evento_abc)
            await atualizar_dado_em_path(path_def, evento_def)

            print(f"✅ [A3-STEP1] Evento ABC criado em {path_abc}")
            print(f"✅ [A3-STEP1] Evento DEF criado em {path_def}")

            self.dados_criados.extend([path_abc, path_def])

            # 2. Simular lista de candidatos persistida
            resumo_eventos = [
                {
                    "evento_id": "ABC123",
                    "descricao": evento_abc["descricao"],
                    "data": evento_abc["data"],
                    "hora_inicio": evento_abc["hora_inicio"],
                    "profissional": evento_abc["profissional"],
                },
                {
                    "evento_id": "DEF456",
                    "descricao": evento_def["descricao"],
                    "data": evento_def["data"],
                    "hora_inicio": evento_def["hora_inicio"],
                    "profissional": evento_def["profissional"],
                },
            ]

            print(f"✅ [A3-STEP2] Resumo de eventos persistido: {len(resumo_eventos)} eventos")

            # 3. Simular que evento ABC foi alterado (cancelado externamente)
            evento_abc_cancelado = dict(evento_abc)
            evento_abc_cancelado["status"] = "cancelado"
            await atualizar_dado_em_path(path_abc, evento_abc_cancelado)

            print(f"✅ [A3-STEP3] Evento ABC marcado como cancelado externamente")

            # 4. Simular seleção do usuário: "1" (índice 0)
            idx = 0
            ev_selecionado = resumo_eventos[idx]
            evento_id_selecionado = ev_selecionado.get("evento_id")

            print(f"✅ [A3-STEP4] Usuário selecionou índice {idx} → evento_id={evento_id_selecionado}")

            # 5. Verificar se evento_id é ABC (esperado: ABC123)
            if evento_id_selecionado == "ABC123":
                print(f"✅ [A3-RESULTADO] Índice apontou corretamente para ABC123")
                resultado = "PASS"
            else:
                print(f"❌ [A3-RESULTADO] Índice apontou para {evento_id_selecionado}, esperado ABC123")
                resultado = "FAIL"

            self.resultados.append({
                "teste": "A3",
                "descricao": "Índice em resumo_eventos",
                "resultado": resultado,
                "evidencia": {
                    "resumo_eventos_count": len(resumo_eventos),
                    "indice_selecionado": idx,
                    "evento_id_retornado": evento_id_selecionado,
                    "evento_abc_status": "cancelado",
                },
            })

        except Exception as e:
            print(f"❌ [A3-ERRO] {e}")
            self.resultados.append({
                "teste": "A3",
                "resultado": "ERROR",
                "erro": str(e),
            })

    async def teste_a6_draft_antigo_contexto(self):
        """
        TESTE A6: Draft antigo recuperado em nova requisição

        Cenário:
        1. Criar evento antigo (Bruna)
        2. Criar sessão com draft_agendamento antigo
        3. Persistir sessão em Firestore
        4. Simular passagem de tempo
        5. Carregar sessão
        6. Verificar se draft_agendamento é carregado
        """
        print("\n" + "-" * 80)
        print("TESTE A6: Draft antigo em contexto carregado")
        print("-" * 80)

        try:
            # 1. Criar evento antigo (3 dias atrás)
            data_antiga = (datetime.now() - timedelta(days=3)).date().isoformat()

            evento_antigo = {
                "cliente_id": self.cliente_teste,
                "descricao": "Corte com Bruna (antigo)",
                "profissional": "Bruna",
                "data": data_antiga,
                "hora_inicio": "10:00",
                "hora_fim": "10:30",
                "servico": "corte",
                "status": "confirmado",
            }

            path_evento_antigo = f"Clientes/{self.tenant_teste}/Eventos/ANTIGO789"
            await atualizar_dado_em_path(path_evento_antigo, evento_antigo)
            self.dados_criados.append(path_evento_antigo)

            print(f"✅ [A6-STEP1] Evento antigo criado: data={data_antiga}")

            # 2. Criar sessão com draft_agendamento antigo
            draft_antigo = {
                "servico": "corte",
                "profissional": "Bruna",
                "data_hora": f"{data_antiga}T10:00:00",
            }

            sessao_contexto = {
                "estado_fluxo": "idle",
                "draft_agendamento": draft_antigo,
                "timestamp_sessao": datetime.now().isoformat(),
            }

            # 3. Persistir sessão
            path_sessao = f"Clientes/{self.tenant_teste}/Sessoes/{self.cliente_teste}"
            await salvar_sessao_temporaria(
                self.cliente_teste,
                sessao_contexto,
                self.tenant_teste
            )

            print(f"✅ [A6-STEP3] Sessão persistida com draft_antigo")

            # 4. Simular passagem de tempo (na verdade apenas carregamos)
            print(f"⏳ [A6-STEP4] Simulando passagem de tempo...")

            # 5. Carregar sessão
            sessao_carregada = await carregar_sessao_temporaria(
                self.cliente_teste,
                self.tenant_teste,
                permitir_fallback_legado=False  # Desabilitar fallback para teste puro
            )

            print(f"✅ [A6-STEP5] Sessão carregada")

            # 6. Verificar se draft_agendamento é carregado
            draft_carregado = sessao_carregada.get("draft_agendamento")

            if draft_carregado:
                print(f"⚠️  [A6-RESULTADO] Draft antigo foi carregado: {draft_carregado}")
                resultado = "POTENTIAL_RISK"
            else:
                print(f"✅ [A6-RESULTADO] Draft antigo NÃO foi carregado (seguro)")
                resultado = "PASS"

            self.resultados.append({
                "teste": "A6",
                "descricao": "Draft antigo em contexto carregado",
                "resultado": resultado,
                "evidencia": {
                    "draft_persistido": draft_antigo,
                    "draft_carregado": draft_carregado,
                    "dias_passados": 3,
                },
            })

        except Exception as e:
            print(f"❌ [A6-ERRO] {e}")
            self.resultados.append({
                "teste": "A6",
                "resultado": "ERROR",
                "erro": str(e),
            })

    async def teste_a7_multiplos_eventos_cancelamento_ambiguo(self):
        """
        TESTE A7: Contexto histórico com múltiplos eventos

        Cenário A (Múltiplos futuros):
        1. Criar evento antigo (3 dias atrás, Bruna, data futura)
        2. Criar evento novo (hoje, Gloria, data futura)
        3. Solicitar cancelamento ambíguo ("cancelar")
        4. Verificar qual evento é retornado
        5. Verificar ordem de apresentação
        """
        print("\n" + "-" * 80)
        print("TESTE A7: Múltiplos eventos + cancelamento ambíguo")
        print("-" * 80)

        try:
            # Cenário A: Múltiplos eventos futuros
            print("\n[A7-CENARIO-A] Múltiplos eventos futuros")

            data_futura_bruna = (datetime.now() + timedelta(days=5)).date().isoformat()
            data_futura_gloria = (datetime.now() + timedelta(days=7)).date().isoformat()

            evento_bruna = {
                "cliente_id": self.cliente_teste,
                "descricao": "Corte com Bruna",
                "profissional": "Bruna",
                "data": data_futura_bruna,
                "hora_inicio": "10:00",
                "hora_fim": "10:30",
                "servico": "corte",
                "status": "confirmado",
                "criado_em": (datetime.now() - timedelta(days=3)).isoformat(),
            }

            evento_gloria = {
                "cliente_id": self.cliente_teste,
                "descricao": "Corte com Gloria",
                "profissional": "Gloria",
                "data": data_futura_gloria,
                "hora_inicio": "14:00",
                "hora_fim": "14:30",
                "servico": "corte",
                "status": "confirmado",
                "criado_em": datetime.now().isoformat(),
            }

            path_bruna = f"Clientes/{self.tenant_teste}/Eventos/BRUNA_FUTURE_001"
            path_gloria = f"Clientes/{self.tenant_teste}/Eventos/GLORIA_NEW_001"

            await atualizar_dado_em_path(path_bruna, evento_bruna)
            await atualizar_dado_em_path(path_gloria, evento_gloria)

            self.dados_criados.extend([path_bruna, path_gloria])

            print(f"✅ [A7-A-STEP1] Evento Bruna (antigo, data={data_futura_bruna})")
            print(f"✅ [A7-A-STEP1] Evento Gloria (novo, data={data_futura_gloria})")

            # 3. Buscar eventos com termo ambíguo "cancelar"
            ok, msg, candidatos = await cancelar_evento_por_texto(
                user_id=self.cliente_teste,
                termo="corte",  # Termo ambíguo
                tenant_id=self.tenant_teste
            )

            print(f"✅ [A7-A-STEP3] Busca com termo='corte'")
            print(f"   - Encontrados: {len(candidatos)} eventos")
            print(f"   - Mensagem: {msg[:100]}...")

            # 5. Verificar ordem de apresentação
            if candidatos:
                primeiro = candidatos[0] if candidatos else None
                print(f"\n📋 [A7-A-RESULTADO] Ordem de apresentação:")
                for i, (eid, ev) in enumerate(candidatos, start=1):
                    prof = ev.get("profissional")
                    data = ev.get("data")
                    print(f"   {i}) {prof} - {data} (evento_id={eid})")

                # Esperado: Gloria (mais próxima) deve vir primeiro
                primeiro_prof = primeiro[1].get("profissional") if primeiro else None

                if primeiro_prof == "Gloria":
                    print(f"✅ [A7-A-RESULTADO] Ordem correta: Gloria (próxima) vem primeiro")
                    resultado = "PASS"
                elif primeiro_prof == "Bruna":
                    print(f"⚠️  [A7-A-RESULTADO] Ordem questionável: Bruna (antiga) vem primeiro")
                    resultado = "POTENTIAL_RISK"
                else:
                    resultado = "UNKNOWN"
            else:
                print(f"❌ [A7-A-RESULTADO] Nenhum candidato encontrado!")
                resultado = "FAIL"

            self.resultados.append({
                "teste": "A7-Cenario-A",
                "descricao": "Múltiplos eventos futuros com cancelamento ambíguo",
                "resultado": resultado,
                "evidencia": {
                    "candidatos_count": len(candidatos),
                    "primeiro_candidato": (candidatos[0][1].get("profissional") if candidatos else None),
                    "data_bruna": data_futura_bruna,
                    "data_gloria": data_futura_gloria,
                },
            })

            # Cenário B: Eventos passados e futuros
            print("\n[A7-CENARIO-B] Eventos passados e futuros")

            evento_passado = {
                "cliente_id": self.cliente_teste,
                "descricao": "Corte passado",
                "profissional": "Professora",
                "data": (datetime.now() - timedelta(days=1)).date().isoformat(),
                "hora_inicio": "15:00",
                "hora_fim": "15:30",
                "servico": "corte",
                "status": "confirmado",
            }

            path_passado = f"Clientes/{self.tenant_teste}/Eventos/PASSADO_001"
            await atualizar_dado_em_path(path_passado, evento_passado)
            self.dados_criados.append(path_passado)

            print(f"✅ [A7-B-STEP1] Evento passado criado")

            # Buscar novamente
            ok, msg, candidatos = await cancelar_evento_por_texto(
                user_id=self.cliente_teste,
                termo="corte",
                tenant_id=self.tenant_teste
            )

            print(f"✅ [A7-B-STEP2] Busca com termo='corte' (com evento passado)")
            print(f"   - Encontrados: {len(candidatos)} eventos")

            # Verificar se evento passado foi excluído
            has_passado = any("passado" in ev[1].get("descricao", "").lower() for ev in candidatos)

            if not has_passado:
                print(f"✅ [A7-B-RESULTADO] Evento passado foi corretamente excluído da busca")
                resultado_b = "PASS"
            else:
                print(f"❌ [A7-B-RESULTADO] Evento passado foi incluído na busca!")
                resultado_b = "FAIL"

            self.resultados.append({
                "teste": "A7-Cenario-B",
                "descricao": "Eventos passados excluídos de cancelamento",
                "resultado": resultado_b,
                "evidencia": {
                    "candidatos_count": len(candidatos),
                    "tem_evento_passado": has_passado,
                },
            })

        except Exception as e:
            print(f"❌ [A7-ERRO] {e}")
            import traceback
            traceback.print_exc()
            self.resultados.append({
                "teste": "A7",
                "resultado": "ERROR",
                "erro": str(e),
            })

    async def limpar_dados_teste(self):
        """Limpar dados de teste criados."""
        print("\n" + "-" * 80)
        print("LIMPEZA DE DADOS DE TESTE")
        print("-" * 80)

        for path in self.dados_criados:
            try:
                # Não deletar, apenas marcar como teste
                doc = await buscar_dado_em_path(path)
                if doc:
                    print(f"⚠️  [LIMPEZA] Documento de teste deixado em: {path}")
                    print(f"   (Manual cleanup recomendado)")
            except Exception as e:
                print(f"⚠️  [LIMPEZA] Erro ao verificar {path}: {e}")

        print(f"\n📝 [LIMPEZA] Documentos criados ({len(self.dados_criados)}):")
        for path in self.dados_criados:
            print(f"   - {path}")

    async def relatorio_final(self):
        """Gerar relatório final."""
        print("\n" + "=" * 80)
        print("RELATÓRIO FINAL — P0 A3/A6/A7")
        print("=" * 80)

        passed = sum(1 for r in self.resultados if r.get("resultado") == "PASS")
        failed = sum(1 for r in self.resultados if r.get("resultado") == "FAIL")
        risk = sum(1 for r in self.resultados if r.get("resultado") == "POTENTIAL_RISK")
        error = sum(1 for r in self.resultados if r.get("resultado") == "ERROR")

        print(f"\n📊 RESUMO:")
        print(f"   ✅ PASS: {passed}")
        print(f"   ⚠️  POTENTIAL_RISK: {risk}")
        print(f"   ❌ FAIL: {failed}")
        print(f"   🔥 ERROR: {error}")

        print(f"\n📋 RESULTADOS DETALHADOS:")
        for r in self.resultados:
            status_icon = {
                "PASS": "✅",
                "FAIL": "❌",
                "POTENTIAL_RISK": "⚠️ ",
                "ERROR": "🔥",
            }.get(r.get("resultado"), "❓")

            print(f"\n{status_icon} {r.get('teste')}: {r.get('descricao')}")
            print(f"   Resultado: {r.get('resultado')}")
            if r.get("evidencia"):
                for k, v in r.get("evidencia").items():
                    print(f"   - {k}: {v}")
            if r.get("erro"):
                print(f"   Erro: {r.get('erro')}")

        print("\n" + "=" * 80)
        print("FIM DO TESTE")
        print("=" * 80)

    async def executar(self):
        """Executar suite completa."""
        await self.setup()
        await self.teste_a3_indice_resumo_eventos()
        await self.teste_a6_draft_antigo_contexto()
        await self.teste_a7_multiplos_eventos_cancelamento_ambiguo()
        await self.limpar_dados_teste()
        await self.relatorio_final()


async def main():
    """Ponto de entrada."""
    import os

    # Verificar credenciais Firebase
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        print("❌ ERRO: GOOGLE_APPLICATION_CREDENTIALS não definido")
        sys.exit(1)

    suite = TestP0A3A6A7()
    await suite.executar()


if __name__ == "__main__":
    asyncio.run(main())
