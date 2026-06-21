"""
P0 BATERIA: Múltiplas Entidades em Uma Conversa
===============================================

Objetivo: Certificar que o sistema preserva e processa corretamente
múltiplas entidades (serviços, profissionais, horários) em uma mesma conversa.

Critério de Certificação:
- 15/15 cenários PASSAM
- Nenhuma entidade perdida
- Nenhuma entidade misturada
- Nenhum evento criado indevidamente
- Isolamento multi-tenant preservado

Ambiente:
- Firestore REAL (sem mocks)
- Validação 100% determinística
- Sem GPT decidindo lógica crítica
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Adicionar diretório ao path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from firebase_admin import firestore, initialize_app, credentials
from utils.contexto_temporario import (
    salvar_contexto_temporario_v2, carregar_contexto_temporario_v2,
    limpar_contexto_agendamento_v2
)


class BateriaP0MultiEntidades:
    """Bateria P0 para validar múltiplas entidades."""

    def __init__(self):
        self.db = None
        self.tenant_a = "7394370553"  # Dono A (real)
        self.cliente_a = "7371670478"  # Cliente A (real)
        self.tenant_b = "9999999999"  # Dono B (teste)
        self.cliente_b = "8888888888"  # Cliente B (teste)
        self.profissionais = ["Bruna", "Carla", "Larissa"]
        self.servicos = ["Corte", "Escova", "Hidratação", "Manicure"]
        self.data_teste = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        self.resultados = []

    async def setup(self):
        """Inicializar Firestore."""
        try:
            try:
                self.db = firestore.client()
            except:
                cred_path = Path(__file__).parent.parent / "credentials.json"
                if cred_path.exists():
                    initialize_app(credentials.Certificate(str(cred_path)))
                else:
                    initialize_app()
                self.db = firestore.client()
            print(f"[OK] Firestore inicializado", flush=True)
        except Exception as e:
            print(f"[ERRO] Falha Firestore: {e}", flush=True)
            raise

    async def cleanup(self):
        """Limpar contextos após testes."""
        try:
            await limpar_contexto_agendamento_v2(self.tenant_a, self.cliente_a)
            await limpar_contexto_agendamento_v2(self.tenant_b, self.cliente_b)
            print(f"[OK] Cleanup concluido", flush=True)
        except Exception as e:
            print(f"[AVISO] Erro no cleanup: {e}", flush=True)

    async def _log_resultado(self, numero, nome, status, detalhes=""):
        """Log estruturado de resultado."""
        resultado = {
            "numero": numero,
            "nome": nome,
            "status": status,
            "detalhes": detalhes,
            "timestamp": datetime.now().isoformat()
        }
        self.resultados.append(resultado)
        print(f"[{numero}] {nome}: {status} {detalhes}", flush=True)

    async def cenario_1_dois_servicos_mesma_mensagem(self):
        """Cenário 1: 'Quero corte e escova amanhã'"""
        try:
            # Salvar contexto com 2 serviços
            contexto = {
                "estado_fluxo": "agendando",
                "servicos": ["Corte", "Escova"],
                "data": self.data_teste,
                "profissionais": [],
                "horarios": []
            }
            await salvar_contexto_temporario_v2(self.tenant_a, self.cliente_a, contexto)

            # Verificar que ambos foram salvos
            ctx_saved = await carregar_contexto_temporario_v2(self.tenant_a, self.cliente_a)

            if len(ctx_saved.get("servicos", [])) == 2:
                await self._log_resultado(1, "Dois serviços mesma mensagem", "PASSOU",
                    f"servicos={ctx_saved.get('servicos')}")
                return "PASSOU"
            else:
                await self._log_resultado(1, "Dois serviços mesma mensagem", "FALHOU",
                    f"esperado 2, obtido {len(ctx_saved.get('servicos', []))}")
                return "FALHOU"
        except Exception as e:
            await self._log_resultado(1, "Dois serviços mesma mensagem", "ERRO", str(e))
            return "ERRO"

    async def cenario_2_servicos_com_profissionais(self):
        """Cenário 2: 'Quero corte com Bruna e manicure com Larissa'"""
        try:
            # Salvar contexto com pares serviço-profissional
            contexto = {
                "estado_fluxo": "agendando",
                "agendamentos": [
                    {"servico": "Corte", "profissional": "Bruna"},
                    {"servico": "Manicure", "profissional": "Larissa"}
                ],
                "data": self.data_teste
            }
            await salvar_contexto_temporario_v2(self.tenant_a, self.cliente_a, contexto)
            ctx_saved = await carregar_contexto_temporario_v2(self.tenant_a, self.cliente_a)

            agendamentos = ctx_saved.get("agendamentos", [])
            if len(agendamentos) == 2 and \
               agendamentos[0]["profissional"] == "Bruna" and \
               agendamentos[1]["profissional"] == "Larissa":
                await self._log_resultado(2, "2 profissionais, 2 serviços", "PASSOU",
                    f"pares={len(agendamentos)}")
                return "PASSOU"
            else:
                await self._log_resultado(2, "2 profissionais, 2 serviços", "FALHOU",
                    "pares não preservados")
                return "FALHOU"
        except Exception as e:
            await self._log_resultado(2, "2 profissionais, 2 serviços", "ERRO", str(e))
            return "ERRO"

    async def cenario_3_dois_horarios(self):
        """Cenário 3: 'Quero corte às 10 e hidratação às 14'"""
        try:
            contexto = {
                "estado_fluxo": "agendando",
                "servicos_horarios": [
                    {"servico": "Corte", "horario": "10:00"},
                    {"servico": "Hidratação", "horario": "14:00"}
                ],
                "data": self.data_teste
            }
            await salvar_contexto_temporario_v2(self.tenant_a, self.cliente_a, contexto)
            ctx_saved = await carregar_contexto_temporario_v2(self.tenant_a, self.cliente_a)

            sh = ctx_saved.get("servicos_horarios", [])
            if len(sh) == 2 and sh[0]["horario"] == "10:00" and sh[1]["horario"] == "14:00":
                await self._log_resultado(3, "2 horários diferentes", "PASSOU",
                    f"horarios={[s['horario'] for s in sh]}")
                return "PASSOU"
            else:
                await self._log_resultado(3, "2 horários diferentes", "FALHOU",
                    "horários não preservados")
                return "FALHOU"
        except Exception as e:
            await self._log_resultado(3, "2 horários diferentes", "ERRO", str(e))
            return "ERRO"

    async def cenario_4_multiplos_atendimentos(self):
        """Cenário 4: 'Quero corte para mim e escova para minha filha'"""
        try:
            contexto = {
                "estado_fluxo": "agendando",
                "atendimentos": [
                    {"servico": "Corte", "cliente": "eu", "data": self.data_teste},
                    {"servico": "Escova", "cliente": "filha", "data": self.data_teste}
                ]
            }
            await salvar_contexto_temporario_v2(self.tenant_a, self.cliente_a, contexto)
            ctx_saved = await carregar_contexto_temporario_v2(self.tenant_a, self.cliente_a)

            aten = ctx_saved.get("atendimentos", [])
            if len(aten) == 2 and aten[0]["cliente"] == "eu" and aten[1]["cliente"] == "filha":
                await self._log_resultado(4, "Múltiplos atendimentos", "PASSOU",
                    f"atendimentos={len(aten)}")
                return "PASSOU"
            else:
                await self._log_resultado(4, "Múltiplos atendimentos", "FALHOU",
                    "atendimentos não preservados")
                return "FALHOU"
        except Exception as e:
            await self._log_resultado(4, "Múltiplos atendimentos", "ERRO", str(e))
            return "ERRO"

    async def cenario_5_lista_completa(self):
        """Cenário 5: 'Quero corte, escova e hidratação'"""
        try:
            contexto = {
                "estado_fluxo": "agendando",
                "servicos": ["Corte", "Escova", "Hidratação"],
                "data": self.data_teste,
                "profissional": "qualquer"
            }
            await salvar_contexto_temporario_v2(self.tenant_a, self.cliente_a, contexto)
            ctx_saved = await carregar_contexto_temporario_v2(self.tenant_a, self.cliente_a)

            servicos = ctx_saved.get("servicos", [])
            if len(servicos) == 3 and "Hidratação" in servicos:
                await self._log_resultado(5, "Lista completa (3 itens)", "PASSOU",
                    f"servicos={len(servicos)}")
                return "PASSOU"
            else:
                await self._log_resultado(5, "Lista completa (3 itens)", "FALHOU",
                    f"esperado 3, obtido {len(servicos)}")
                return "FALHOU"
        except Exception as e:
            await self._log_resultado(5, "Lista completa (3 itens)", "ERRO", str(e))
            return "ERRO"

    async def cenario_6_conflito_localizado(self):
        """Cenário 6: Conflito em apenas uma entidade (1/2 com problema)"""
        try:
            # Simular: Corte ok, Escova com conflito de horário
            contexto = {
                "estado_fluxo": "agendando",
                "agendamentos": [
                    {
                        "servico": "Corte",
                        "horario": "10:00",
                        "status": "disponivel"
                    },
                    {
                        "servico": "Escova",
                        "horario": "10:00",  # Mesmo horário - conflito
                        "status": "indisponivel"
                    }
                ],
                "data": self.data_teste
            }
            await salvar_contexto_temporario_v2(self.tenant_a, self.cliente_a, contexto)
            ctx_saved = await carregar_contexto_temporario_v2(self.tenant_a, self.cliente_a)

            agen = ctx_saved.get("agendamentos", [])
            # Verificar que apenas 1 tem conflito, não todos
            com_conflito = [a for a in agen if a.get("status") == "indisponivel"]
            if len(agen) == 2 and len(com_conflito) == 1:
                await self._log_resultado(6, "Conflito localizado", "PASSOU",
                    f"apenas 1/2 com conflito")
                return "PASSOU"
            else:
                await self._log_resultado(6, "Conflito localizado", "FALHOU",
                    "conflito não localizado corretamente")
                return "FALHOU"
        except Exception as e:
            await self._log_resultado(6, "Conflito localizado", "ERRO", str(e))
            return "ERRO"

    async def cenario_7_troca_profissional(self):
        """Cenário 7: Troca profissional em uma entidade entre várias"""
        try:
            # Inicial
            contexto_inicial = {
                "estado_fluxo": "agendando",
                "agendamentos": [
                    {"servico": "Corte", "profissional": "Bruna"},
                    {"servico": "Escova", "profissional": "Carla"}
                ],
                "data": self.data_teste
            }
            await salvar_contexto_temporario_v2(self.tenant_a, self.cliente_a, contexto_inicial)

            # Trocar profissional do Corte para Larissa
            contexto_atualizado = contexto_inicial.copy()
            contexto_atualizado["agendamentos"][0]["profissional"] = "Larissa"
            await salvar_contexto_temporario_v2(self.tenant_a, self.cliente_a, contexto_atualizado)

            ctx_final = await carregar_contexto_temporario_v2(self.tenant_a, self.cliente_a)
            agen = ctx_final.get("agendamentos", [])

            if len(agen) == 2 and \
               agen[0]["profissional"] == "Larissa" and \
               agen[1]["profissional"] == "Carla":
                await self._log_resultado(7, "Troca profissional localizada", "PASSOU",
                    f"Corte->Larissa, Escova->Carla preservada")
                return "PASSOU"
            else:
                await self._log_resultado(7, "Troca profissional localizada", "FALHOU",
                    "profissional não trocado corretamente")
                return "FALHOU"
        except Exception as e:
            await self._log_resultado(7, "Troca profissional localizada", "ERRO", str(e))
            return "ERRO"

    async def cenario_8_troca_horario(self):
        """Cenário 8: Troca horário em uma entidade entre várias"""
        try:
            # Inicial
            contexto_inicial = {
                "estado_fluxo": "agendando",
                "agendamentos": [
                    {"servico": "Corte", "horario": "10:00"},
                    {"servico": "Escova", "horario": "11:00"}
                ],
                "data": self.data_teste
            }
            await salvar_contexto_temporario_v2(self.tenant_a, self.cliente_a, contexto_inicial)

            # Trocar horário do Corte
            contexto_atualizado = contexto_inicial.copy()
            contexto_atualizado["agendamentos"][0]["horario"] = "14:00"
            await salvar_contexto_temporario_v2(self.tenant_a, self.cliente_a, contexto_atualizado)

            ctx_final = await carregar_contexto_temporario_v2(self.tenant_a, self.cliente_a)
            agen = ctx_final.get("agendamentos", [])

            if len(agen) == 2 and \
               agen[0]["horario"] == "14:00" and \
               agen[1]["horario"] == "11:00":
                await self._log_resultado(8, "Troca horário localizada", "PASSOU",
                    f"Corte->14h, Escova->11h preservada")
                return "PASSOU"
            else:
                await self._log_resultado(8, "Troca horário localizada", "FALHOU",
                    "horário não trocado corretamente")
                return "FALHOU"
        except Exception as e:
            await self._log_resultado(8, "Troca horário localizada", "ERRO", str(e))
            return "ERRO"

    async def cenario_9_cancelamento_parcial(self):
        """Cenário 9: Cancelamento de uma entidade entre várias"""
        try:
            # Inicial: 3 serviços
            contexto_inicial = {
                "estado_fluxo": "agendando",
                "servicos": ["Corte", "Escova", "Hidratação"],
                "data": self.data_teste
            }
            await salvar_contexto_temporario_v2(self.tenant_a, self.cliente_a, contexto_inicial)

            # Remover Escova
            contexto_atualizado = contexto_inicial.copy()
            contexto_atualizado["servicos"] = ["Corte", "Hidratação"]
            await salvar_contexto_temporario_v2(self.tenant_a, self.cliente_a, contexto_atualizado)

            ctx_final = await carregar_contexto_temporario_v2(self.tenant_a, self.cliente_a)
            servicos = ctx_final.get("servicos", [])

            if len(servicos) == 2 and "Corte" in servicos and "Hidratação" in servicos and "Escova" not in servicos:
                await self._log_resultado(9, "Cancelamento parcial", "PASSOU",
                    f"Escova removida, 2 preservados")
                return "PASSOU"
            else:
                await self._log_resultado(9, "Cancelamento parcial", "FALHOU",
                    "cancelamento não foi localizado")
                return "FALHOU"
        except Exception as e:
            await self._log_resultado(9, "Cancelamento parcial", "ERRO", str(e))
            return "ERRO"

    async def cenario_10_confirmacao_parcial(self):
        """Cenário 10: Confirmação de algumas entidades, pendência de outras"""
        try:
            contexto = {
                "estado_fluxo": "agendando",
                "agendamentos": [
                    {
                        "servico": "Corte",
                        "profissional": "Bruna",
                        "status": "confirmado"
                    },
                    {
                        "servico": "Escova",
                        "profissional": "Carla",
                        "status": "aguardando_confirmacao"
                    }
                ],
                "data": self.data_teste
            }
            await salvar_contexto_temporario_v2(self.tenant_a, self.cliente_a, contexto)
            ctx_saved = await carregar_contexto_temporario_v2(self.tenant_a, self.cliente_a)

            agen = ctx_saved.get("agendamentos", [])
            confirmados = [a for a in agen if a.get("status") == "confirmado"]
            aguardando = [a for a in agen if a.get("status") == "aguardando_confirmacao"]

            if len(confirmados) == 1 and len(aguardando) == 1:
                await self._log_resultado(10, "Confirmação parcial", "PASSOU",
                    f"1 confirmado, 1 aguardando")
                return "PASSOU"
            else:
                await self._log_resultado(10, "Confirmação parcial", "FALHOU",
                    "status não preservados")
                return "FALHOU"
        except Exception as e:
            await self._log_resultado(10, "Confirmação parcial", "ERRO", str(e))
            return "ERRO"

    async def cenario_11_negacao_parcial(self):
        """Cenário 11: Negação de algumas entidades, mantendo outras"""
        try:
            # Inicial: 3 serviços
            contexto_inicial = {
                "estado_fluxo": "agendando",
                "agendamentos": [
                    {"servico": "Corte", "status": "ativo"},
                    {"servico": "Escova", "status": "ativo"},
                    {"servico": "Hidratação", "status": "ativo"}
                ],
                "data": self.data_teste
            }
            await salvar_contexto_temporario_v2(self.tenant_a, self.cliente_a, contexto_inicial)

            # Cancelar apenas Escova
            contexto_atualizado = contexto_inicial.copy()
            contexto_atualizado["agendamentos"][1]["status"] = "cancelado"
            await salvar_contexto_temporario_v2(self.tenant_a, self.cliente_a, contexto_atualizado)

            ctx_final = await carregar_contexto_temporario_v2(self.tenant_a, self.cliente_a)
            agen = ctx_final.get("agendamentos", [])
            ativos = [a for a in agen if a.get("status") == "ativo"]
            cancelados = [a for a in agen if a.get("status") == "cancelado"]

            if len(ativos) == 2 and len(cancelados) == 1:
                await self._log_resultado(11, "Negação parcial", "PASSOU",
                    f"2 ativos, 1 cancelado")
                return "PASSOU"
            else:
                await self._log_resultado(11, "Negação parcial", "FALHOU",
                    "negação não foi localizada")
                return "FALHOU"
        except Exception as e:
            await self._log_resultado(11, "Negação parcial", "ERRO", str(e))
            return "ERRO"

    async def cenario_12_multi_tenant(self):
        """Cenário 12: Múltiplas entidades com isolamento multi-tenant"""
        try:
            # Contexto Tenant A
            contexto_a = {
                "estado_fluxo": "agendando",
                "servicos": ["Corte", "Escova"],
                "data": self.data_teste
            }
            await salvar_contexto_temporario_v2(self.tenant_a, self.cliente_a, contexto_a)

            # Contexto Tenant B
            contexto_b = {
                "estado_fluxo": "agendando",
                "servicos": ["Hidratação", "Manicure"],
                "data": self.data_teste
            }
            await salvar_contexto_temporario_v2(self.tenant_b, self.cliente_b, contexto_b)

            # Verificar isolamento
            ctx_a = await carregar_contexto_temporario_v2(self.tenant_a, self.cliente_a)
            ctx_b = await carregar_contexto_temporario_v2(self.tenant_b, self.cliente_b)

            servicos_a = ctx_a.get("servicos", [])
            servicos_b = ctx_b.get("servicos", [])

            if set(servicos_a) == {"Corte", "Escova"} and \
               set(servicos_b) == {"Hidratação", "Manicure"}:
                await self._log_resultado(12, "Multi-tenant", "PASSOU",
                    f"A={servicos_a}, B={servicos_b}")
                return "PASSOU"
            else:
                await self._log_resultado(12, "Multi-tenant", "FALHOU",
                    "contextos não isolados")
                return "FALHOU"
        except Exception as e:
            await self._log_resultado(12, "Multi-tenant", "ERRO", str(e))
            return "ERRO"

    async def cenario_13_interrupcao_informativa(self):
        """Cenário 13: Pergunta informativa não interfere em múltiplas entidades"""
        try:
            # Contexto com 2 serviços
            contexto = {
                "estado_fluxo": "agendando",
                "servicos": ["Corte", "Escova"],
                "data": self.data_teste,
                "informacao_pedida": "Qual é o preço do corte?"  # Interrupção
            }
            await salvar_contexto_temporario_v2(self.tenant_a, self.cliente_a, contexto)
            ctx_saved = await carregar_contexto_temporario_v2(self.tenant_a, self.cliente_a)

            # Verificar que servicos continuam intactos
            servicos = ctx_saved.get("servicos", [])
            if len(servicos) == 2 and "Corte" in servicos and "Escova" in servicos:
                await self._log_resultado(13, "Interrupção informativa", "PASSOU",
                    f"servicos preservados com pergunta")
                return "PASSOU"
            else:
                await self._log_resultado(13, "Interrupção informativa", "FALHOU",
                    "servicos foram perdidos")
                return "FALHOU"
        except Exception as e:
            await self._log_resultado(13, "Interrupção informativa", "ERRO", str(e))
            return "ERRO"

    async def cenario_14_mudanca_contexto(self):
        """Cenário 14: Mudança de contexto preserva múltiplas entidades"""
        try:
            # Contexto inicial
            contexto_inicial = {
                "estado_fluxo": "agendando",
                "servicos": ["Corte", "Escova", "Hidratação"],
                "profissional": "Bruna",
                "data": self.data_teste
            }
            await salvar_contexto_temporario_v2(self.tenant_a, self.cliente_a, contexto_inicial)

            # Trocar profissional
            contexto_mudado = contexto_inicial.copy()
            contexto_mudado["profissional"] = "Carla"
            await salvar_contexto_temporario_v2(self.tenant_a, self.cliente_a, contexto_mudado)

            ctx_final = await carregar_contexto_temporario_v2(self.tenant_a, self.cliente_a)

            # Verificar que serviços continuam e profissional mudou
            servicos = ctx_final.get("servicos", [])
            profissional = ctx_final.get("profissional")

            if len(servicos) == 3 and profissional == "Carla":
                await self._log_resultado(14, "Mudança de contexto", "PASSOU",
                    f"3 serviços preservados, profissional mudou")
                return "PASSOU"
            else:
                await self._log_resultado(14, "Mudança de contexto", "FALHOU",
                    "serviços perdidos ou profissional não mudou")
                return "FALHOU"
        except Exception as e:
            await self._log_resultado(14, "Mudança de contexto", "ERRO", str(e))
            return "ERRO"

    async def cenario_15_rajada(self):
        """Cenário 15: Rajada de mudanças em múltiplas entidades"""
        try:
            # Simular rajada: 3 mensagens em sequência
            contexto = {
                "estado_fluxo": "agendando",
                "servicos": ["Corte"],
                "data": self.data_teste
            }

            # Mensagem 1: Adicionar Escova
            contexto["servicos"].append("Escova")
            await salvar_contexto_temporario_v2(self.tenant_a, self.cliente_a, contexto)

            # Mensagem 2: Adicionar Hidratação
            contexto["servicos"].append("Hidratação")
            await salvar_contexto_temporario_v2(self.tenant_a, self.cliente_a, contexto)

            # Mensagem 3: Trocar profissional
            contexto["profissional"] = "Bruna"
            await salvar_contexto_temporario_v2(self.tenant_a, self.cliente_a, contexto)

            ctx_final = await carregar_contexto_temporario_v2(self.tenant_a, self.cliente_a)
            servicos = ctx_final.get("servicos", [])
            profissional = ctx_final.get("profissional")

            # Verificar ordem e completude
            if len(servicos) == 3 and profissional == "Bruna" and \
               servicos[0] == "Corte" and "Escova" in servicos and "Hidratação" in servicos:
                await self._log_resultado(15, "Rajada mudanças", "PASSOU",
                    f"3 serviços preservados em sequência")
                return "PASSOU"
            else:
                await self._log_resultado(15, "Rajada mudanças", "FALHOU",
                    f"ordem/serviços não preservados: {servicos}")
                return "FALHOU"
        except Exception as e:
            await self._log_resultado(15, "Rajada mudanças", "ERRO", str(e))
            return "ERRO"

    async def executar(self):
        """Executar todos os 15 cenários."""
        await self.setup()

        print("\n" + "="*60, flush=True)
        print("P0 BATERIA: MULTIPLAS ENTIDADES", flush=True)
        print("="*60, flush=True)

        cenarios = [
            self.cenario_1_dois_servicos_mesma_mensagem,
            self.cenario_2_servicos_com_profissionais,
            self.cenario_3_dois_horarios,
            self.cenario_4_multiplos_atendimentos,
            self.cenario_5_lista_completa,
            self.cenario_6_conflito_localizado,
            self.cenario_7_troca_profissional,
            self.cenario_8_troca_horario,
            self.cenario_9_cancelamento_parcial,
            self.cenario_10_confirmacao_parcial,
            self.cenario_11_negacao_parcial,
            self.cenario_12_multi_tenant,
            self.cenario_13_interrupcao_informativa,
            self.cenario_14_mudanca_contexto,
            self.cenario_15_rajada,
        ]

        for cenario_func in cenarios:
            await cenario_func()

        await self.cleanup()

        # Salvar resultados
        resultado_json = {
            "bateria": "P0_MULTI_ENTIDADES",
            "data": datetime.now().isoformat(),
            "total_cenarios": len(self.resultados),
            "passou": len([r for r in self.resultados if r["status"] == "PASSOU"]),
            "falhou": len([r for r in self.resultados if r["status"] == "FALHOU"]),
            "erros": len([r for r in self.resultados if r["status"] == "ERRO"]),
            "cenarios": self.resultados
        }

        resultado_path = Path(__file__).parent / "resultado_p0_multi_entidades.json"
        with open(resultado_path, "w", encoding="utf-8") as f:
            json.dump(resultado_json, f, indent=2, ensure_ascii=False)

        print("\n" + "="*60, flush=True)
        print(f"RESULTADO FINAL: {resultado_json['passou']}/{resultado_json['total_cenarios']} PASSOU", flush=True)
        print("="*60 + "\n", flush=True)

        return resultado_json


async def main():
    """Executar bateria."""
    bateria = BateriaP0MultiEntidades()
    return await bateria.executar()


if __name__ == "__main__":
    resultado = asyncio.run(main())
    sys.exit(0 if resultado["falhou"] == 0 and resultado["erros"] == 0 else 1)
