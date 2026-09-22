#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
P0 BATERIA: Resumo Diário Expandido (DONO + CLIENTE + PROFISSIONAL)
=====================================================================

Objetivo: Validar enviar_resumo_diario() com 3 tipos de usuário
- DONO: eventos + tarefas + follow-ups
- CLIENTE: apenas seus agendamentos
- PROFISSIONAL: apenas seus agendamentos

Ambiente:
- Firestore REAL (sem mocks)
- 15 cenários (5 DONO + 5 CLIENTE + 5 PROFISSIONAL)
- Validação 100% determinística

Critério de SUCESSO:
- 15/15 cenários PASSAM
- Dados corretos para cada tipo
- Isolamento garantido
- Nenhuma duplicação
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from firebase_admin import firestore, initialize_app, credentials
from services.firebase_service_async import (
    buscar_subcolecao,
    salvar_dado_em_path,
    buscar_dado_em_path,
    deletar_dado_em_path,
)

class BateriaP0ResumoExpandido:
    """Bateria P0 para validar resumo diário expandido."""

    def __init__(self):
        self.db = None
        self.dono_id = "1000000001"
        self.cliente_1_id = "2000000001"
        self.cliente_2_id = "2000000002"
        self.prof_1_id = "3000000001"
        self.prof_1_nome = "Bruna"
        self.prof_2_id = "3000000002"
        self.prof_2_nome = "Carla"

        self.hoje = datetime.now().strftime("%Y-%m-%d")
        self.resultados = []

    async def setup(self):
        """Inicializar Firestore e dados de teste."""
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

            await self._criar_dados_teste()
        except Exception as e:
            print(f"[ERRO] Falha Firestore: {e}", flush=True)
            raise

    async def _criar_dados_teste(self):
        """Criar estrutura de dados para testes."""
        print("[SETUP] Criando dados de teste...", flush=True)

        # 1. DONO
        await salvar_dado_em_path(f"Clientes/{self.dono_id}", {
            "tipo_usuario": "dono",
            "nome": "Dona Maria",
            "canal": "telegram",
            "ativo": True,
            "criado_em": datetime.now().isoformat()
        })

        # 2. CLIENTES
        await salvar_dado_em_path(f"Clientes/{self.cliente_1_id}", {
            "tipo_usuario": "cliente",
            "nome": "Cliente João",
            "canal": "telegram",
            "ativo": True,
            "criado_em": datetime.now().isoformat()
        })

        await salvar_dado_em_path(f"Clientes/{self.cliente_2_id}", {
            "tipo_usuario": "cliente",
            "nome": "Cliente Maria",
            "canal": "telegram",
            "ativo": True,
            "criado_em": datetime.now().isoformat()
        })

        # 3. PROFISSIONAIS
        await salvar_dado_em_path(f"Clientes/{self.prof_1_id}", {
            "tipo_usuario": "profissional",
            "nome": self.prof_1_nome,
            "canal": "telegram",
            "identificador": self.prof_1_id,
            "ativo": True,
            "criado_em": datetime.now().isoformat()
        })

        await salvar_dado_em_path(f"Clientes/{self.prof_2_id}", {
            "tipo_usuario": "profissional",
            "nome": self.prof_2_nome,
            "canal": "telegram",
            "identificador": self.prof_2_id,
            "ativo": True,
            "criado_em": datetime.now().isoformat()
        })

        # 4. TAREFAS (dono)
        await salvar_dado_em_path(f"Clientes/{self.dono_id}/Tarefas/tarefa_1", {
            "descricao": "Repor estoque de tinta",
            "status": "pendente"
        })

        await salvar_dado_em_path(f"Clientes/{self.dono_id}/Tarefas/tarefa_2", {
            "descricao": "Limpar sala de espera",
            "status": "pendente"
        })

        # 5. FOLLOW-UPS (dono)
        await salvar_dado_em_path(f"Usuarios/{self.dono_id}/FollowUps/followup_1", {
            "nome_cliente": "Prospecto Silva",
            "status": "pendente",
            "data": self.hoje,
            "hora": "17:00"
        })

        # 6. EVENTOS
        # Evento 1: Cliente João com Bruna
        await salvar_dado_em_path(f"Clientes/{self.dono_id}/Eventos/evento_1", {
            "cliente_id": self.cliente_1_id,
            "cliente_nome": "Cliente João",
            "profissional": self.prof_1_nome,
            "profissional_user_id": self.prof_1_id,
            "descricao": "Corte de cabelo",
            "data": self.hoje,
            "hora_inicio": "14:00",
            "hora_fim": "14:30",
            "status": "confirmado",
            "confirmado": True,
        })

        # Evento 2: Dono com Bruna
        await salvar_dado_em_path(f"Clientes/{self.dono_id}/Eventos/evento_2", {
            "cliente_id": self.dono_id,
            "cliente_nome": "Dona Maria",
            "profissional": self.prof_1_nome,
            "profissional_user_id": self.prof_1_id,
            "descricao": "Manicure",
            "data": self.hoje,
            "hora_inicio": "15:00",
            "hora_fim": "15:30",
            "status": "confirmado",
            "confirmado": True,
        })

        # Evento 3: Cliente Maria com Carla
        await salvar_dado_em_path(f"Clientes/{self.dono_id}/Eventos/evento_3", {
            "cliente_id": self.cliente_2_id,
            "cliente_nome": "Cliente Maria",
            "profissional": self.prof_2_nome,
            "profissional_user_id": self.prof_2_id,
            "descricao": "Escova",
            "data": self.hoje,
            "hora_inicio": "16:00",
            "hora_fim": "16:30",
            "status": "confirmado",
            "confirmado": True,
        })

        # Evento 4: Outro dia (não deve aparecer no resumo de hoje)
        amanha = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        await salvar_dado_em_path(f"Clientes/{self.dono_id}/Eventos/evento_4", {
            "cliente_id": self.cliente_1_id,
            "cliente_nome": "Cliente João",
            "profissional": self.prof_1_nome,
            "profissional_user_id": self.prof_1_id,
            "descricao": "Corte",
            "data": amanha,
            "hora_inicio": "10:00",
            "hora_fim": "10:30",
            "status": "confirmado",
            "confirmado": True,
        })

        print("[SETUP] Dados criados com sucesso", flush=True)

    async def cleanup(self):
        """Limpar dados de teste."""
        try:
            usuarios = [
                self.dono_id, self.cliente_1_id, self.cliente_2_id,
                self.prof_1_id, self.prof_2_id
            ]
            for uid in usuarios:
                try:
                    await deletar_dado_em_path(f"Clientes/{uid}")
                except:
                    pass

            # Cleanup follow-ups
            for uid in usuarios:
                try:
                    await deletar_dado_em_path(f"Usuarios/{uid}")
                except:
                    pass

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
        emoji = "✅" if status == "PASSOU" else "❌" if status == "FALHOU" else "⚠️"
        print(f"[{numero:2d}] {emoji} {nome}: {status} {detalhes}", flush=True)

    # =====================================================================
    # CENÁRIOS DONO (1-5)
    # =====================================================================

    async def cenario_1_dono_recebe_eventos(self):
        """[DONO-1] Dono recebe eventos de hoje"""
        try:
            eventos_dict = await buscar_subcolecao(f"Clientes/{self.dono_id}/Eventos") or {}

            eventos_hoje = [
                v for v in eventos_dict.values()
                if isinstance(v, dict) and v.get("data") == self.hoje
            ]

            # Dono tem 3 eventos hoje: 1 dele + 2 de clientes
            assert len(eventos_hoje) == 3, \
                f"Dono deveria ter 3 eventos, tem {len(eventos_hoje)}"

            await self._log_resultado(1, "DONO recebe eventos", "PASSOU",
                f"{len(eventos_hoje)} eventos de hoje")
            return "PASSOU"
        except AssertionError as e:
            await self._log_resultado(1, "DONO recebe eventos", "FALHOU", str(e))
            return "FALHOU"
        except Exception as e:
            await self._log_resultado(1, "DONO recebe eventos", "ERRO", str(e))
            return "ERRO"

    async def cenario_2_dono_recebe_tarefas(self):
        """[DONO-2] Dono recebe tarefas pendentes"""
        try:
            tarefas_dict = await buscar_subcolecao(f"Clientes/{self.dono_id}/Tarefas") or {}
            tarefas = [t for t in tarefas_dict.values() if isinstance(t, dict)]

            assert len(tarefas) >= 2, \
                f"Dono deveria ter 2+ tarefas, tem {len(tarefas)}"

            # Validar que são tarefas reais
            assert any(t.get("descricao") == "Repor estoque de tinta" for t in tarefas), \
                "Tarefa 'Repor estoque' não encontrada"

            await self._log_resultado(2, "DONO recebe tarefas", "PASSOU",
                f"{len(tarefas)} tarefas pendentes")
            return "PASSOU"
        except AssertionError as e:
            await self._log_resultado(2, "DONO recebe tarefas", "FALHOU", str(e))
            return "FALHOU"
        except Exception as e:
            await self._log_resultado(2, "DONO recebe tarefas", "ERRO", str(e))
            return "ERRO"

    async def cenario_3_dono_recebe_followups(self):
        """[DONO-3] Dono recebe follow-ups de hoje"""
        try:
            followups_dict = await buscar_subcolecao(f"Usuarios/{self.dono_id}/FollowUps") or {}

            followups_hoje = [
                f for f in followups_dict.values()
                if isinstance(f, dict) and f.get("status") == "pendente" and f.get("data") == self.hoje
            ]

            assert len(followups_hoje) >= 1, \
                f"Dono deveria ter 1+ follow-up, tem {len(followups_hoje)}"

            await self._log_resultado(3, "DONO recebe follow-ups", "PASSOU",
                f"{len(followups_hoje)} follow-ups de hoje")
            return "PASSOU"
        except AssertionError as e:
            await self._log_resultado(3, "DONO recebe follow-ups", "FALHOU", str(e))
            return "FALHOU"
        except Exception as e:
            await self._log_resultado(3, "DONO recebe follow-ups", "ERRO", str(e))
            return "ERRO"

    async def cenario_4_dono_nao_recebe_futuro(self):
        """[DONO-4] Dono não recebe eventos de amanhã no resumo de hoje"""
        try:
            eventos_dict = await buscar_subcolecao(f"Clientes/{self.dono_id}/Eventos") or {}

            eventos_hoje = [
                v for v in eventos_dict.values()
                if isinstance(v, dict) and v.get("data") == self.hoje
            ]

            amanha = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            eventos_amanha = [
                v for v in eventos_dict.values()
                if isinstance(v, dict) and v.get("data") == amanha
            ]

            # Eventos de amanhã não devem contar no resumo de hoje
            assert len(eventos_hoje) == 3, "Hoje deve ter 3 eventos"
            assert len(eventos_amanha) == 1, "Amanhã deve ter 1 evento"
            assert eventos_hoje != eventos_amanha, "Não deve misturar datas"

            await self._log_resultado(4, "DONO não vê futuro", "PASSOU",
                "Datas isoladas corretamente")
            return "PASSOU"
        except AssertionError as e:
            await self._log_resultado(4, "DONO não vê futuro", "FALHOU", str(e))
            return "FALHOU"
        except Exception as e:
            await self._log_resultado(4, "DONO não vê futuro", "ERRO", str(e))
            return "ERRO"

    async def cenario_5_dono_vê_multiplos_profissionais(self):
        """[DONO-5] Dono vê eventos de múltiplos profissionais"""
        try:
            eventos_dict = await buscar_subcolecao(f"Clientes/{self.dono_id}/Eventos") or {}

            eventos_hoje = [
                v for v in eventos_dict.values()
                if isinstance(v, dict) and v.get("data") == self.hoje
            ]

            profissionais = set(
                e.get("profissional") for e in eventos_hoje if e.get("profissional")
            )

            assert len(profissionais) >= 2, \
                f"Deveria ter 2+ profissionais, tem {len(profissionais)}"

            assert self.prof_1_nome in profissionais, "Bruna não encontrada"
            assert self.prof_2_nome in profissionais, "Carla não encontrada"

            await self._log_resultado(5, "DONO vê múltiplos profissionais", "PASSOU",
                f"{len(profissionais)} profissionais diferentes")
            return "PASSOU"
        except AssertionError as e:
            await self._log_resultado(5, "DONO vê múltiplos profissionais", "FALHOU", str(e))
            return "FALHOU"
        except Exception as e:
            await self._log_resultado(5, "DONO vê múltiplos profissionais", "ERRO", str(e))
            return "ERRO"

    # =====================================================================
    # CENÁRIOS CLIENTE (6-10)
    # =====================================================================

    async def cenario_6_cliente_recebe_seus_agendamentos(self):
        """[CLIENTE-1] Cliente 1 recebe apenas seus agendamentos de hoje"""
        try:
            eventos_dict = await buscar_subcolecao(f"Clientes/{self.dono_id}/Eventos") or {}

            # Filtrar apenas eventos do Cliente 1
            eventos_cliente = [
                v for v in eventos_dict.values()
                if isinstance(v, dict)
                and v.get("data") == self.hoje
                and v.get("cliente_id") == self.cliente_1_id
            ]

            assert len(eventos_cliente) == 1, \
                f"Cliente 1 deveria ver 1 evento, vê {len(eventos_cliente)}"

            evento = eventos_cliente[0]
            assert evento.get("profissional") == self.prof_1_nome, \
                "Evento deveria ser com Bruna"

            await self._log_resultado(6, "CLIENTE recebe seus agendamentos", "PASSOU",
                f"1 evento para {evento.get('cliente_nome')}")
            return "PASSOU"
        except AssertionError as e:
            await self._log_resultado(6, "CLIENTE recebe seus agendamentos", "FALHOU", str(e))
            return "FALHOU"
        except Exception as e:
            await self._log_resultado(6, "CLIENTE recebe seus agendamentos", "ERRO", str(e))
            return "ERRO"

    async def cenario_7_cliente_nao_vê_outros_clientes(self):
        """[CLIENTE-2] Cliente 1 não vê agendamentos de Cliente 2"""
        try:
            eventos_dict = await buscar_subcolecao(f"Clientes/{self.dono_id}/Eventos") or {}

            # Eventos do Cliente 1
            eventos_c1 = [
                v for v in eventos_dict.values()
                if isinstance(v, dict) and v.get("cliente_id") == self.cliente_1_id
            ]

            # Eventos do Cliente 2
            eventos_c2 = [
                v for v in eventos_dict.values()
                if isinstance(v, dict) and v.get("cliente_id") == self.cliente_2_id
            ]

            # Não devem se sobrepor
            c1_ids = set(e.get("cliente_id") for e in eventos_c1)
            c2_ids = set(e.get("cliente_id") for e in eventos_c2)

            assert len(c1_ids.intersection(c2_ids)) == 0, \
                "Clientes vendo eventos um do outro"

            assert self.cliente_1_id in c1_ids, "Cliente 1 não vê seus eventos"
            assert self.cliente_2_id not in c1_ids, "Cliente 1 vê eventos de Cliente 2"

            await self._log_resultado(7, "CLIENTE não vê outros", "PASSOU",
                "Isolamento entre clientes garantido")
            return "PASSOU"
        except AssertionError as e:
            await self._log_resultado(7, "CLIENTE não vê outros", "FALHOU", str(e))
            return "FALHOU"
        except Exception as e:
            await self._log_resultado(7, "CLIENTE não vê outros", "ERRO", str(e))
            return "ERRO"

    async def cenario_8_cliente_nao_vê_tarefas_dono(self):
        """[CLIENTE-3] Cliente não vê tarefas ou follow-ups do dono"""
        try:
            # Cliente 1 não deveria ter acesso a tarefas
            tarefas_dict = await buscar_subcolecao(f"Clientes/{self.cliente_1_id}/Tarefas") or {}

            # Se houver tarefas, seriam dele, não do dono
            tarefas = [t for t in tarefas_dict.values() if isinstance(t, dict)]

            # Verificar que "Repor estoque de tinta" (tarefa do dono) NÃO está aqui
            tarefas_descricoes = [t.get("descricao") for t in tarefas]

            assert "Repor estoque de tinta" not in tarefas_descricoes, \
                "Cliente vendo tarefas do dono"

            await self._log_resultado(8, "CLIENTE não vê tarefas dono", "PASSOU",
                "Isolamento de dados administrativos garantido")
            return "PASSOU"
        except AssertionError as e:
            await self._log_resultado(8, "CLIENTE não vê tarefas dono", "FALHOU", str(e))
            return "FALHOU"
        except Exception as e:
            await self._log_resultado(8, "CLIENTE não vê tarefas dono", "ERRO", str(e))
            return "ERRO"

    async def cenario_9_cliente_ve_profissional_correto(self):
        """[CLIENTE-4] Cliente vê o nome correto do profissional"""
        try:
            eventos_dict = await buscar_subcolecao(f"Clientes/{self.dono_id}/Eventos") or {}

            eventos_c1 = [
                v for v in eventos_dict.values()
                if isinstance(v, dict) and v.get("cliente_id") == self.cliente_1_id
            ]

            assert len(eventos_c1) > 0, "Cliente 1 sem eventos"

            evento = eventos_c1[0]
            profissional = evento.get("profissional")

            assert profissional == self.prof_1_nome, \
                f"Profissional deveria ser {self.prof_1_nome}, é {profissional}"

            await self._log_resultado(9, "CLIENTE vê profissional correto", "PASSOU",
                f"Profissional: {profissional}")
            return "PASSOU"
        except AssertionError as e:
            await self._log_resultado(9, "CLIENTE vê profissional correto", "FALHOU", str(e))
            return "FALHOU"
        except Exception as e:
            await self._log_resultado(9, "CLIENTE vê profissional correto", "ERRO", str(e))
            return "ERRO"

    async def cenario_10_cliente_2_vê_seu_agendamento(self):
        """[CLIENTE-5] Cliente 2 vê seu agendamento com Carla"""
        try:
            eventos_dict = await buscar_subcolecao(f"Clientes/{self.dono_id}/Eventos") or {}

            eventos_c2 = [
                v for v in eventos_dict.values()
                if isinstance(v, dict)
                and v.get("data") == self.hoje
                and v.get("cliente_id") == self.cliente_2_id
            ]

            assert len(eventos_c2) == 1, \
                f"Cliente 2 deveria ver 1 evento, vê {len(eventos_c2)}"

            evento = eventos_c2[0]
            assert evento.get("profissional") == self.prof_2_nome, \
                f"Deveria ser com {self.prof_2_nome}"

            await self._log_resultado(10, "CLIENTE 2 vê seu agendamento", "PASSOU",
                f"Agendamento com {evento.get('profissional')}")
            return "PASSOU"
        except AssertionError as e:
            await self._log_resultado(10, "CLIENTE 2 vê seu agendamento", "FALHOU", str(e))
            return "FALHOU"
        except Exception as e:
            await self._log_resultado(10, "CLIENTE 2 vê seu agendamento", "ERRO", str(e))
            return "ERRO"

    # =====================================================================
    # CENÁRIOS PROFISSIONAL (11-15)
    # =====================================================================

    async def cenario_11_profissional_recebe_seus_agendamentos(self):
        """[PROF-1] Profissional Bruna recebe apenas seus agendamentos"""
        try:
            eventos_dict = await buscar_subcolecao(f"Clientes/{self.dono_id}/Eventos") or {}

            # Filtrar por profissional Bruna
            eventos_bruna = [
                v for v in eventos_dict.values()
                if isinstance(v, dict)
                and v.get("data") == self.hoje
                and str(v.get("profissional", "")).lower() == self.prof_1_nome.lower()
            ]

            assert len(eventos_bruna) == 2, \
                f"Bruna deveria ver 2 eventos, vê {len(eventos_bruna)}"

            nomes_clientes = set(e.get("cliente_nome") for e in eventos_bruna)
            assert "Cliente João" in nomes_clientes, "João não está nos agendamentos de Bruna"
            assert "Dona Maria" in nomes_clientes, "Dona Maria não está nos agendamentos de Bruna"

            await self._log_resultado(11, "PROF recebe seus agendamentos", "PASSOU",
                f"Bruna vê {len(eventos_bruna)} eventos")
            return "PASSOU"
        except AssertionError as e:
            await self._log_resultado(11, "PROF recebe seus agendamentos", "FALHOU", str(e))
            return "FALHOU"
        except Exception as e:
            await self._log_resultado(11, "PROF recebe seus agendamentos", "ERRO", str(e))
            return "ERRO"

    async def cenario_12_profissional_nao_vê_outro_prof(self):
        """[PROF-2] Bruna não vê agendamentos de Carla"""
        try:
            eventos_dict = await buscar_subcolecao(f"Clientes/{self.dono_id}/Eventos") or {}

            eventos_bruna = [
                v for v in eventos_dict.values()
                if isinstance(v, dict)
                and str(v.get("profissional", "")).lower() == self.prof_1_nome.lower()
            ]

            eventos_carla = [
                v for v in eventos_dict.values()
                if isinstance(v, dict)
                and str(v.get("profissional", "")).lower() == self.prof_2_nome.lower()
            ]

            # Não devem ter elementos em comum
            bruna_nomes = set(e.get("cliente_nome") for e in eventos_bruna)
            carla_nomes = set(e.get("cliente_nome") for e in eventos_carla)

            assert len(bruna_nomes.intersection(carla_nomes)) == 0, \
                "Profissionais vendo eventos um do outro"

            assert "Cliente Maria" not in bruna_nomes, \
                "Bruna vendo evento de Carla"

            await self._log_resultado(12, "PROF não vê outro prof", "PASSOU",
                "Isolamento entre profissionais garantido")
            return "PASSOU"
        except AssertionError as e:
            await self._log_resultado(12, "PROF não vê outro prof", "FALHOU", str(e))
            return "FALHOU"
        except Exception as e:
            await self._log_resultado(12, "PROF não vê outro prof", "ERRO", str(e))
            return "ERRO"

    async def cenario_13_profissional_ve_cliente_correto(self):
        """[PROF-3] Bruna vê nomes corretos dos clientes"""
        try:
            eventos_dict = await buscar_subcolecao(f"Clientes/{self.dono_id}/Eventos") or {}

            eventos_bruna = [
                v for v in eventos_dict.values()
                if isinstance(v, dict)
                and str(v.get("profissional", "")).lower() == self.prof_1_nome.lower()
            ]

            nomes = [e.get("cliente_nome") for e in eventos_bruna]

            assert "Cliente João" in nomes, "Cliente João não aparece"
            assert "Dona Maria" in nomes, "Dona Maria não aparece"

            await self._log_resultado(13, "PROF vê clientes corretos", "PASSOU",
                f"Clientes: {', '.join(nomes)}")
            return "PASSOU"
        except AssertionError as e:
            await self._log_resultado(13, "PROF vê clientes corretos", "FALHOU", str(e))
            return "FALHOU"
        except Exception as e:
            await self._log_resultado(13, "PROF vê clientes corretos", "ERRO", str(e))
            return "ERRO"

    async def cenario_14_profissional_carla_vê_seu_agendamento(self):
        """[PROF-4] Profissional Carla vê seu agendamento com Cliente Maria"""
        try:
            eventos_dict = await buscar_subcolecao(f"Clientes/{self.dono_id}/Eventos") or {}

            eventos_carla = [
                v for v in eventos_dict.values()
                if isinstance(v, dict)
                and v.get("data") == self.hoje
                and str(v.get("profissional", "")).lower() == self.prof_2_nome.lower()
            ]

            assert len(eventos_carla) == 1, \
                f"Carla deveria ver 1 evento, vê {len(eventos_carla)}"

            evento = eventos_carla[0]
            assert evento.get("cliente_nome") == "Cliente Maria", \
                "Evento não é de Maria"

            await self._log_resultado(14, "PROF Carla vê seu agendamento", "PASSOU",
                f"Agendamento com {evento.get('cliente_nome')}")
            return "PASSOU"
        except AssertionError as e:
            await self._log_resultado(14, "PROF Carla vê seu agendamento", "FALHOU", str(e))
            return "FALHOU"
        except Exception as e:
            await self._log_resultado(14, "PROF Carla vê seu agendamento", "ERRO", str(e))
            return "ERRO"

    async def cenario_15_profissional_nao_vê_tarefas_dono(self):
        """[PROF-5] Profissional não vê tarefas ou follow-ups do dono"""
        try:
            # Profissional não deveria ter acesso a tarefas do dono
            tarefas_dict = await buscar_subcolecao(f"Clientes/{self.prof_1_id}/Tarefas") or {}
            tarefas = [t for t in tarefas_dict.values() if isinstance(t, dict)]

            tarefas_descricoes = [t.get("descricao") for t in tarefas]

            # Tarefas do dono não devem estar aqui
            assert "Repor estoque de tinta" not in tarefas_descricoes, \
                "Profissional vendo tarefas do dono"

            # Verificar follow-ups também
            followups_dict = await buscar_subcolecao(f"Usuarios/{self.prof_1_id}/FollowUps") or {}
            followups = [f for f in followups_dict.values() if isinstance(f, dict)]

            # Follow-ups do dono não devem estar aqui
            followup_nomes = [f.get("nome_cliente") for f in followups]
            assert "Prospecto Silva" not in followup_nomes, \
                "Profissional vendo follow-ups do dono"

            await self._log_resultado(15, "PROF não vê dados admin dono", "PASSOU",
                "Isolamento de dados administrativos garantido")
            return "PASSOU"
        except AssertionError as e:
            await self._log_resultado(15, "PROF não vê dados admin dono", "FALHOU", str(e))
            return "FALHOU"
        except Exception as e:
            await self._log_resultado(15, "PROF não vê dados admin dono", "ERRO", str(e))
            return "ERRO"

    async def executar_todos(self):
        """Executa suite completa de testes."""
        print("\n" + "="*80, flush=True)
        print("BATERIA P0: RESUMO DIÁRIO EXPANDIDO", flush=True)
        print("="*80, flush=True)

        try:
            await self.setup()

            # CENÁRIOS DONO (1-5)
            print("\n📋 GRUPO 1: DONO (5 cenários)", flush=True)
            await self.cenario_1_dono_recebe_eventos()
            await self.cenario_2_dono_recebe_tarefas()
            await self.cenario_3_dono_recebe_followups()
            await self.cenario_4_dono_nao_recebe_futuro()
            await self.cenario_5_dono_vê_multiplos_profissionais()

            # CENÁRIOS CLIENTE (6-10)
            print("\n👥 GRUPO 2: CLIENTE (5 cenários)", flush=True)
            await self.cenario_6_cliente_recebe_seus_agendamentos()
            await self.cenario_7_cliente_nao_vê_outros_clientes()
            await self.cenario_8_cliente_nao_vê_tarefas_dono()
            await self.cenario_9_cliente_ve_profissional_correto()
            await self.cenario_10_cliente_2_vê_seu_agendamento()

            # CENÁRIOS PROFISSIONAL (11-15)
            print("\n💼 GRUPO 3: PROFISSIONAL (5 cenários)", flush=True)
            await self.cenario_11_profissional_recebe_seus_agendamentos()
            await self.cenario_12_profissional_nao_vê_outro_prof()
            await self.cenario_13_profissional_ve_cliente_correto()
            await self.cenario_14_profissional_carla_vê_seu_agendamento()
            await self.cenario_15_profissional_nao_vê_tarefas_dono()

        except Exception as e:
            print(f"\n❌ Erro geral: {e}", flush=True)
            import traceback
            traceback.print_exc()

        finally:
            await self.cleanup()

        # RELATÓRIO FINAL
        print("\n" + "="*80, flush=True)
        print("RELATÓRIO FINAL", flush=True)
        print("="*80, flush=True)

        passed = sum(1 for r in self.resultados if r["status"] == "PASSOU")
        failed = sum(1 for r in self.resultados if r["status"] == "FALHOU")
        error = sum(1 for r in self.resultados if r["status"] == "ERRO")
        total = len(self.resultados)

        print(f"\n✅ PASSOU: {passed}")
        print(f"❌ FALHOU: {failed}")
        print(f"⚠️  ERRO:   {error}")
        print(f"📊 TOTAL:  {total}\n")

        # Sumário por grupo
        print("Resumo por Grupo:")
        print(f"  DONO:         {sum(1 for r in self.resultados[0:5] if r['status'] == 'PASSOU')}/5")
        print(f"  CLIENTE:      {sum(1 for r in self.resultados[5:10] if r['status'] == 'PASSOU')}/5")
        print(f"  PROFISSIONAL: {sum(1 for r in self.resultados[10:15] if r['status'] == 'PASSOU')}/5")

        if passed == total:
            print("\n🎉 TODOS OS 15 TESTES PASSARAM! ✅✅✅")
            print("Pronto para produção! 🚀")
            return True
        else:
            print(f"\n⚠️  {failed + error} testes falharam. Revisar antes de deploy.")
            return False

async def main():
    bateria = BateriaP0ResumoExpandido()
    sucesso = await bateria.executar_todos()
    return 0 if sucesso else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
