#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BATERIA P0 — FLUXO REAL COM FIRESTORE
Objetivo: Provar conflito → sugestão → criação → limpeza com Firestore real

7 ETAPAS CRÍTICAS:
1. Conflito detectado (lock_existente)
2. Lock existente bloqueado
3. Sugestões geradas (função existente)
4. Aceite de sugestão (novo horário)
5. Confirmação final (evento criado)
6. Criação do evento
7. Limpeza de contexto (DELETE_FIELD)

VALIDAÇÃO: JSON final mostra PASS/FAIL por etapa
"""

import asyncio
import json
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import firestore
from services.firebase_service_async import (
    atualizar_dado_em_path,
    buscar_dado_em_path,
    deletar_dado_em_path,
    obter_id_dono,
    buscar_subcolecao,
)
from services.event_service_async import (
    verificar_conflito_e_sugestoes_profissional,
    salvar_evento,
    criar_evento_com_lock,
)
from services.agenda_lock_service import criar_evento_com_lock as criar_com_lock_real
from utils.contexto_temporario import (
    carregar_contexto_temporario,
    salvar_contexto_temporario,
)


class BateriaP0FluxoCompleto:
    """Teste completo: conflito → sugestão → criação"""

    def __init__(self):
        self.tenant_id = "bateria_p0_dono_teste"
        self.actor_id = "bateria_p0_user_teste_001"
        self.profissional = "Bruna"
        self.servico = "Corte"

        self.resultado = {
            "timestamp": datetime.now().isoformat(),
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
            "etapas": [],
            "resumo": {
                "total_etapas": 7,
                "passaram": 0,
                "falharam": 0,
            }
        }

    async def setup_cliente_teste(self):
        """SETUP: Registrar actor como cliente com id_negocio correto"""
        print("\n" + "="*80)
        print("SETUP: Registrando cliente teste")
        print("="*80)

        cliente_doc = {
            "nome": "Bateria Test Actor",
            "id_negocio": self.tenant_id,
            "email": "test@bateria.com",
            "tipo_usuario": "cliente"
        }

        cliente_path = f"Clientes/{self.actor_id}"

        print(f"\n[SETUP] Criando cliente: {cliente_path}")
        print(f"[SETUP] id_negocio: {self.tenant_id}")

        resultado_criar = await atualizar_dado_em_path(cliente_path, cliente_doc)
        print(f"[SETUP] Resultado: {resultado_criar}")

        # Validacao: confirmar que obter_id_dono retorna o tenant correto
        print(f"\n[SETUP] Validando que obter_id_dono retorna tenant correto...")
        tenant_retornado = await obter_id_dono(self.actor_id)

        print(f"[SETUP] obter_id_dono('{self.actor_id}') = '{tenant_retornado}'")
        print(f"[SETUP] Esperado: '{self.tenant_id}'")

        if tenant_retornado != self.tenant_id:
            print(f"\n*** ABORTANDO TESTE ***")
            print(f"obter_id_dono() retornou '{tenant_retornado}' em vez de '{self.tenant_id}'")
            print(f"Cliente pode nao ter sido registrado corretamente")
            raise ValueError(
                f"Validacao de tenant falhou. "
                f"Esperado: {self.tenant_id}, Obtido: {tenant_retornado}"
            )

        print(f"\n[SETUP] Validacao OK: tenant resolvido corretamente")
        print(f"[SETUP] Cliente teste pronto para bateria P0")

    async def etapa_1_conflito_detectado(self):
        """ETAPA 1: Detectar conflito (lock_existente)"""
        etapa = {
            "numero": 1,
            "nome": "Conflito Detectado (lock_existente)",
            "status": "INICIANDO",
            "detalhes": {}
        }

        try:
            print("\n" + "="*80)
            print("ETAPA 1: Conflito Detectado")
            print("="*80)

            # Pré-condição: Criar evento já ocupado com Bruna
            data_hoje = datetime.now().strftime("%Y-%m-%d")

            # Evento 1: Bruna 10:00-10:20 (ocupado)
            evento_ocupado = {
                "descricao": "Corte com Bruna (ocupado)",
                "profissional": "Bruna",
                "servico": "Corte",
                "data": data_hoje,
                "hora_inicio": "10:00",
                "hora_fim": "10:20",
                "duracao": 20,
                "confirmado": True,
                "status": "confirmado",
                "cliente_id": "cliente_teste_001",
                "cliente_nome": "João Ocupado"
            }

            print(f"[PRÉ] Criando evento ocupado: {evento_ocupado['profissional']} {evento_ocupado['hora_inicio']}")
            resultado_pre = await criar_com_lock_real(
                dono_id=self.tenant_id,
                evento=evento_ocupado,
                event_id=f"evt_ocupado_{data_hoje}_1000"
            )

            print(f"[PRÉ] Resultado: {resultado_pre}")
            etapa["detalhes"]["evento_pre_criado"] = resultado_pre.get("ok", False)

            # Agora tentar agendar NO MESMO HORÁRIO
            print(f"\n[TESTE] Tentando agendar {self.profissional} no mesmo horário (10:00)...")

            evento_conflito = {
                "descricao": f"{self.servico} com {self.profissional}",
                "profissional": self.profissional,
                "servico": self.servico,
                "data": data_hoje,
                "hora_inicio": "10:00",  # ← MESMO HORÁRIO!
                "hora_fim": "10:20",     # ← OBRIGATÓRIO para criar_evento_com_lock
                "duracao": 20,
                "confirmado": True,
                "status": "confirmado",
                "cliente_id": self.actor_id,
                "cliente_nome": "Teste Conflito"
            }

            # Tentar criar com lock (deve falhar)
            resultado_conflito = await criar_com_lock_real(
                dono_id=self.tenant_id,
                evento=evento_conflito,
                event_id=f"evt_conflito_{data_hoje}_1000"
            )

            print(f"[TESTE] Resultado: {resultado_conflito}")

            # VALIDAÇÃO
            passou = (
                resultado_conflito.get("ok") is False and
                resultado_conflito.get("tipo_erro") == "lock_existente"
            )

            etapa["status"] = "PASSOU" if passou else "FALHOU"
            etapa["detalhes"]["resultado"] = resultado_conflito
            etapa["detalhes"]["passou"] = passou

            if passou:
                print("[OK] ETAPA 1 PASSOU: Conflito lock_existente detectado corretamente")
                self.resultado["resumo"]["passaram"] += 1
            else:
                print("[FALHA] ETAPA 1 FALHOU: Conflito não foi detectado como lock_existente")
                self.resultado["resumo"]["falharam"] += 1

        except Exception as e:
            print(f"[FALHA] ERRO na Etapa \1: Execucao falhou")
            etapa["status"] = "ERRO"
            etapa["detalhes"]["erro"] = "Erro durante execucao"
            self.resultado["resumo"]["falharam"] += 1

        self.resultado["etapas"].append(etapa)
        return etapa["detalhes"].get("passou", False)

    async def etapa_2_lock_existente_bloqueado(self):
        """ETAPA 2: Validar que lock_existente bloqueia múltiplas tentativas"""
        etapa = {
            "numero": 2,
            "nome": "Lock Existente Bloqueado",
            "status": "INICIANDO",
            "detalhes": {}
        }

        try:
            print("\n" + "="*80)
            print("ETAPA 2: Lock Existente Bloqueado")
            print("="*80)

            data_hoje = datetime.now().strftime("%Y-%m-%d")

            # Tentar segunda vez no mesmo horário
            print("[TESTE] Segunda tentativa no mesmo horário...")

            evento_conflito_2 = {
                "descricao": f"{self.servico} com {self.profissional} (tentativa 2)",
                "profissional": self.profissional,
                "servico": self.servico,
                "data": data_hoje,
                "hora_inicio": "10:00",
                "hora_fim": "10:20",     # ← OBRIGATÓRIO para criar_evento_com_lock
                "duracao": 20,
                "confirmado": True,
                "cliente_id": self.actor_id,
                "cliente_nome": "Teste Conflito 2"
            }

            resultado_2 = await criar_com_lock_real(
                dono_id=self.tenant_id,
                evento=evento_conflito_2,
                event_id=f"evt_conflito_{data_hoje}_1000_2"  # ID diferente, mesmo horário
            )

            print(f"[TESTE] Resultado 2ª tentativa: {resultado_2}")

            passou = (
                resultado_2.get("ok") is False and
                resultado_2.get("tipo_erro") == "lock_existente"
            )

            etapa["status"] = "PASSOU" if passou else "FALHOU"
            etapa["detalhes"]["resultado_segunda_tentativa"] = resultado_2
            etapa["detalhes"]["passou"] = passou

            if passou:
                print("[OK] ETAPA 2 PASSOU: Lock bloqueou segunda tentativa")
                self.resultado["resumo"]["passaram"] += 1
            else:
                print("[FALHA] ETAPA 2 FALHOU: Lock não bloqueou segunda tentativa")
                self.resultado["resumo"]["falharam"] += 1

        except Exception as e:
            print(f"[FALHA] ERRO na Etapa \1: Execucao falhou")
            etapa["status"] = "ERRO"
            etapa["detalhes"]["erro"] = "Erro durante execucao"
            self.resultado["resumo"]["falharam"] += 1

        self.resultado["etapas"].append(etapa)
        return etapa["detalhes"].get("passou", False)

    async def etapa_3_sugestoes_geradas(self):
        """ETAPA 3: Gerar sugestões após conflito"""
        etapa = {
            "numero": 3,
            "nome": "Sugestões Geradas Após Conflito",
            "status": "INICIANDO",
            "detalhes": {}
        }

        try:
            print("\n" + "="*80)
            print("ETAPA 3: Sugestoes Geradas")
            print("="*80)

            data_hoje = datetime.now().strftime("%Y-%m-%d")

            print(f"[TESTE] Gerando sugestoes para {self.profissional}...")

            # Chamar função real de sugestão
            conflito_info = await verificar_conflito_e_sugestoes_profissional(
                user_id=self.actor_id,
                data=data_hoje,
                hora_inicio="10:00",
                duracao_min=20,
                profissional=self.profissional,
                servico=self.servico
            )

            print("[DEBUG] Funcao retornou resultado")

            # VALIDACAO
            passou = (
                conflito_info.get("conflito") is True and
                len(conflito_info.get("sugestoes", [])) > 0
            )

            etapa["status"] = "PASSOU" if passou else "FALHOU"
            etapa["detalhes"]["num_sugestoes"] = len(conflito_info.get("sugestoes", []))
            etapa["detalhes"]["passou"] = passou

            if passou:
                print(f"[OK] ETAPA 3 PASSOU: {etapa['detalhes']['num_sugestoes']} sugestoes geradas")
                print(f"   Sugestoes encontradas: {len(conflito_info.get('sugestoes', []))}")
                self.resultado["resumo"]["passaram"] += 1
            else:
                print("[FALHA] ETAPA 3 FALHOU: Nenhuma sugestao gerada")
                self.resultado["resumo"]["falharam"] += 1

            self.resultado["etapas"].append(etapa)
            return etapa["detalhes"].get("passou", False), conflito_info

        except Exception as e:
            # Capturar traceback de forma segura com encoding ASCII
            erro_traceback = traceback.format_exc()
            erro_ascii = erro_traceback.encode("ascii", errors="backslashreplace").decode("ascii")

            print(f"[FALHA] ERRO na Etapa 3: Excecao ao processar")
            print(f"[TRACEBACK]\n{erro_ascii}")

            etapa["status"] = "ERRO"
            etapa["detalhes"]["erro"] = "Erro ao processar conflito_info"
            etapa["detalhes"]["erro_traceback_ascii"] = erro_ascii
            self.resultado["resumo"]["falharam"] += 1
            self.resultado["etapas"].append(etapa)
            return False, {}

    async def etapa_4_aceite_sugestao(self):
        """ETAPA 4: Usuário aceita uma sugestão"""
        etapa = {
            "numero": 4,
            "nome": "Aceite de Sugestão",
            "status": "INICIANDO",
            "detalhes": {}
        }

        try:
            print("\n" + "="*80)
            print("ETAPA 4: Aceite de Sugestão")
            print("="*80)

            # Extrair primeira sugestão retornada por ETAPA 3
            sugestoes = self.conflito_info_etapa3.get("sugestoes", [])
            if not sugestoes:
                print("[FALHA] Nenhuma sugestão disponível de ETAPA 3")
                etapa["status"] = "FALHOU"
                etapa["detalhes"]["erro"] = "Sem sugestoes da ETAPA 3"
                etapa["detalhes"]["passou"] = False
                self.resultado["resumo"]["falharam"] += 1
                self.resultado["etapas"].append(etapa)
                return False

            # Pegar primeira sugestão (formato: "HH:MM - HH:MM")
            sugestao_escolhida = sugestoes[0]
            hora_inicio_sugestao = sugestao_escolhida.split(" - ")[0]

            data_hoje = datetime.now().strftime("%Y-%m-%d")
            hora_aceita = hora_inicio_sugestao

            print(f"[SIMULACAO] Usuario aceita sugestao: {self.profissional} as {hora_aceita} (de {sugestoes})")

            # Salvar no contexto que usuário escolheu esse horário
            # Usar dados da sugestão, não valores hardcoded
            contexto_aceite = {
                "estado_fluxo": "aguardando_confirmacao_agendamento",
                "draft_agendamento": {
                    "profissional": self.profissional,
                    "servico": self.servico,
                    "data": data_hoje,
                    "hora_inicio": hora_aceita,
                    "duracao": 20
                },
                "ultima_acao": "aceite_sugestao"
            }

            resultado_save = await salvar_contexto_temporario(
                self.actor_id,
                contexto_aceite,
                tenant_id=self.tenant_id
            )

            print(f"[TESTE] Contexto salvo: {resultado_save}")

            # VALIDAÇÃO
            passou = resultado_save is True or resultado_save == True

            etapa["status"] = "PASSOU" if passou else "FALHOU"
            etapa["detalhes"]["sugestao_escolhida"] = sugestao_escolhida
            etapa["detalhes"]["hora_aceita"] = hora_aceita
            etapa["detalhes"]["contexto_salvo"] = resultado_save
            etapa["detalhes"]["passou"] = passou

            if passou:
                print(f"[OK] ETAPA 4 PASSOU: Sugestão {hora_aceita} aceita e salva")
                self.resultado["resumo"]["passaram"] += 1
            else:
                print("[FALHA] ETAPA 4 FALHOU: Erro ao salvar aceite")
                self.resultado["resumo"]["falharam"] += 1

        except Exception as e:
            erro_traceback = traceback.format_exc()
            erro_ascii = erro_traceback.encode("ascii", errors="backslashreplace").decode("ascii")
            print(f"[FALHA] ERRO na Etapa 4: Execucao falhou")
            print(f"[TRACEBACK]\n{erro_ascii}")
            etapa["status"] = "ERRO"
            etapa["detalhes"]["erro"] = "Erro durante execucao"
            etapa["detalhes"]["erro_traceback_ascii"] = erro_ascii
            self.resultado["resumo"]["falharam"] += 1

        self.resultado["etapas"].append(etapa)
        return etapa["detalhes"].get("passou", False)

    async def etapa_5_confirmacao_final(self):
        """ETAPA 5: Usuário confirma agendamento (sim)"""
        etapa = {
            "numero": 5,
            "nome": "Confirmação Final",
            "status": "INICIANDO",
            "detalhes": {}
        }

        try:
            print("\n" + "="*80)
            print("ETAPA 5: Confirmação Final")
            print("="*80)

            # Carregar contexto para confirmar
            contexto = await carregar_contexto_temporario(
                self.actor_id,
                tenant_id=self.tenant_id
            )

            print(f"[TESTE] Contexto carregado: estado={contexto.get('estado_fluxo')}")

            # Marcar como confirmado
            contexto["estado_fluxo"] = "confirmando_agendamento"
            contexto["aguardando_confirmacao_agendamento"] = True

            resultado_confirm = await salvar_contexto_temporario(
                self.actor_id,
                contexto,
                tenant_id=self.tenant_id
            )

            print(f"[TESTE] Contexto confirmado: {resultado_confirm}")

            passou = resultado_confirm is True

            etapa["status"] = "PASSOU" if passou else "FALHOU"
            etapa["detalhes"]["estado_final"] = contexto.get("estado_fluxo")
            etapa["detalhes"]["passou"] = passou

            if passou:
                print("[OK] ETAPA 5 PASSOU: Agendamento confirmado")
                self.resultado["resumo"]["passaram"] += 1
            else:
                print("[FALHA] ETAPA 5 FALHOU: Erro ao confirmar")
                self.resultado["resumo"]["falharam"] += 1

        except Exception as e:
            erro_traceback = traceback.format_exc()
            erro_ascii = erro_traceback.encode("ascii", errors="backslashreplace").decode("ascii")
            print(f"[FALHA] ERRO na Etapa 5: Execucao falhou")
            print(f"[TRACEBACK]\n{erro_ascii}")
            etapa["status"] = "ERRO"
            etapa["detalhes"]["erro"] = "Erro durante execucao"
            etapa["detalhes"]["erro_traceback_ascii"] = erro_ascii
            self.resultado["resumo"]["falharam"] += 1

        self.resultado["etapas"].append(etapa)
        return etapa["detalhes"].get("passou", False)

    async def etapa_6_criacao_evento(self):
        """ETAPA 6: Criar evento com horário aceito"""
        etapa = {
            "numero": 6,
            "nome": "Criação do Evento",
            "status": "INICIANDO",
            "detalhes": {}
        }

        try:
            print("\n" + "="*80)
            print("ETAPA 6: Criação do Evento")
            print("="*80)

            # Carregar draft final
            contexto = await carregar_contexto_temporario(
                self.actor_id,
                tenant_id=self.tenant_id
            )

            draft = contexto.get("draft_agendamento", {})
            print(f"[TESTE] Draft para criação: {draft}")

            # Calcular hora_fim baseado em hora_inicio + duracao
            from datetime import datetime, timedelta
            hora_inicio_str = draft.get("hora_inicio", "00:00")
            duracao = draft.get("duracao", 20)

            try:
                hora_inicio_dt = datetime.strptime(hora_inicio_str, "%H:%M")
                hora_fim_dt = hora_inicio_dt + timedelta(minutes=duracao)
                hora_fim_str = hora_fim_dt.strftime("%H:%M")
            except Exception as e:
                print(f"[AVISO] Erro ao calcular hora_fim: {e}, usando fallback")
                hora_fim_str = "10:50"

            # Criar evento com dados do draft
            evento_final = {
                "descricao": f"{draft.get('servico')} com {draft.get('profissional')}",
                "profissional": draft.get("profissional"),
                "servico": draft.get("servico"),
                "data": draft.get("data"),
                "hora_inicio": draft.get("hora_inicio"),
                "hora_fim": hora_fim_str,
                "duracao": duracao,
                "confirmado": True,
                "status": "confirmado",
                "cliente_id": self.actor_id,
                "cliente_nome": "Teste P0"
            }

            print(f"[TESTE] Criando evento: {evento_final['profissional']} {evento_final['hora_inicio']}")

            resultado_criacao = await criar_com_lock_real(
                dono_id=self.tenant_id,
                evento=evento_final,
                event_id=f"evt_final_{evento_final['data']}_{evento_final['hora_inicio'].replace(':', '')}"
            )

            print(f"[TESTE] Resultado criação: {resultado_criacao}")

            passou = resultado_criacao.get("ok") is True

            etapa["status"] = "PASSOU" if passou else "FALHOU"
            etapa["detalhes"]["evento_criado"] = resultado_criacao
            etapa["detalhes"]["passou"] = passou

            if passou:
                print("[OK] ETAPA 6 PASSOU: Evento criado com sucesso")
                self.resultado["resumo"]["passaram"] += 1
            else:
                print(f"[FALHA] ETAPA 6 FALHOU: {resultado_criacao.get('motivo')}")
                self.resultado["resumo"]["falharam"] += 1

        except Exception as e:
            erro_traceback = traceback.format_exc()
            erro_ascii = erro_traceback.encode("ascii", errors="backslashreplace").decode("ascii")
            print(f"[FALHA] ERRO na Etapa 6: Execucao falhou")
            print(f"[TRACEBACK]\n{erro_ascii}")
            etapa["status"] = "ERRO"
            etapa["detalhes"]["erro"] = "Erro durante execucao"
            etapa["detalhes"]["erro_traceback_ascii"] = erro_ascii
            self.resultado["resumo"]["falharam"] += 1

        self.resultado["etapas"].append(etapa)
        return etapa["detalhes"].get("passou", False)

    async def etapa_7_limpeza_contexto(self):
        """ETAPA 7: Limpeza de contexto com DELETE_FIELD"""
        etapa = {
            "numero": 7,
            "nome": "Limpeza de Contexto (DELETE_FIELD)",
            "status": "INICIANDO",
            "detalhes": {}
        }

        try:
            print("\n" + "="*80)
            print("ETAPA 7: Limpeza de Contexto")
            print("="*80)

            print("[TESTE] Limpando contexto com DELETE_FIELD...")

            # Payload de limpeza
            from utils.contexto_temporario import limpar_contexto_agendamento_v2

            resultado_limpeza = await limpar_contexto_agendamento_v2(
                dono_id=self.tenant_id,
                cliente_id=self.actor_id
            )

            print(f"[TESTE] Resultado limpeza: {resultado_limpeza}")

            # Validar que campos foram removidos (carregar direto da path v2, sem fallback legado)
            from services.firebase_service_async import buscar_dado_em_path
            path_v2 = f"Clientes/{self.tenant_id}/Sessoes/{self.actor_id}"
            contexto_final = await buscar_dado_em_path(path_v2) or {}

            # Campos que DEVEM estar ausentes
            campos_removidos = {
                "draft_agendamento": "draft_agendamento" not in contexto_final,
                "dados_confirmacao_agendamento": "dados_confirmacao_agendamento" not in contexto_final,
                "estado_fluxo_idle": contexto_final.get("estado_fluxo") == "idle"
            }

            passou = all(campos_removidos.values())

            etapa["status"] = "PASSOU" if passou else "FALHOU"
            etapa["detalhes"]["campos_validacao"] = campos_removidos
            etapa["detalhes"]["contexto_final"] = {k: v for k, v in contexto_final.items() if not k.startswith("_")}
            etapa["detalhes"]["passou"] = passou

            if passou:
                print("[OK] ETAPA 7 PASSOU: Contexto limpo corretamente")
                self.resultado["resumo"]["passaram"] += 1
            else:
                print("[FALHA] ETAPA 7 FALHOU: Contexto não foi limpo")
                print(f"   Campos: {campos_removidos}")
                self.resultado["resumo"]["falharam"] += 1

        except Exception as e:
            erro_traceback = traceback.format_exc()
            erro_ascii = erro_traceback.encode("ascii", errors="backslashreplace").decode("ascii")
            print(f"[FALHA] ERRO na Etapa 7: Execucao falhou")
            print(f"[TRACEBACK]\n{erro_ascii}")
            etapa["status"] = "ERRO"
            etapa["detalhes"]["erro"] = "Erro durante execucao"
            etapa["detalhes"]["erro_traceback_ascii"] = erro_ascii
            self.resultado["resumo"]["falharam"] += 1

        self.resultado["etapas"].append(etapa)
        return etapa["detalhes"].get("passou", False)

    async def limpar_dados_teste(self):
        """Limpar dados de teste do Firestore antes de nova execução"""
        from services.firebase_service_async import buscar_subcolecao, deletar_dado_em_path
        try:
            print("\n[LIMPEZA] Removendo dados de teste anteriores...")

            # Limpar locks de Bruna
            locks_path = f"Clientes/{self.tenant_id}/AgendaLocks"
            locks = await buscar_subcolecao(locks_path) or {}
            for lock_id in locks:
                if "bruna" in lock_id.lower():
                    await deletar_dado_em_path(f"{locks_path}/{lock_id}")
                    print(f"  Deletado: {lock_id}")

            # Limpar eventos de teste
            eventos_path = f"Clientes/{self.tenant_id}/Eventos"
            eventos = await buscar_subcolecao(eventos_path) or {}
            for evt_id in eventos:
                if evt_id.startswith("evt_"):
                    await deletar_dado_em_path(f"{eventos_path}/{evt_id}")
                    print(f"  Deletado evento: {evt_id}")

            print("[LIMPEZA] Dados de teste removidos")
        except Exception as e:
            print(f"[LIMPEZA] Erro ao limpar: {e}")

    async def run(self):
        """Executar todas as 7 etapas"""
        print("\n" + "="*80)
        print("BATERIA P0 — FLUXO COMPLETO COM FIRESTORE REAL")
        print("="*80)

        try:
            # PRÉ-SETUP: Limpar dados de teste anteriores
            await self.limpar_dados_teste()

            # SETUP: Registrar cliente teste (OBRIGATÓRIO antes de etapa 1)
            await self.setup_cliente_teste()

            # Executar etapas em sequência
            await self.etapa_1_conflito_detectado()
            await self.etapa_2_lock_existente_bloqueado()
            passou_3, conflito_info = await self.etapa_3_sugestoes_geradas()
            self.conflito_info_etapa3 = conflito_info  # Salvar para ETAPA 4 usar
            await self.etapa_4_aceite_sugestao()
            await self.etapa_5_confirmacao_final()
            await self.etapa_6_criacao_evento()
            await self.etapa_7_limpeza_contexto()

            # Gerar JSON final
            self.resultado["conclusao"] = {
                "total_etapas": 7,
                "passaram": self.resultado["resumo"]["passaram"],
                "falharam": self.resultado["resumo"]["falharam"],
                "sucesso_geral": self.resultado["resumo"]["falharam"] == 0,
                "fluxo_validado": self.resultado["resumo"]["passaram"] == 7
            }

            # Salvar JSON
            json_path = Path(__file__).parent / "resultado_bateria_p0_fluxo.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(self.resultado, f, indent=2, ensure_ascii=False, default=str)

            print(f"\n[OK] Resultado salvo em: {json_path}")

            # Resumo final
            print("\n" + "="*80)
            print("RESULTADO FINAL")
            print("="*80)
            print(f"[OK] Passaram: {self.resultado['resumo']['passaram']}/7")
            print(f"[FALHA] Falharam: {self.resultado['resumo']['falharam']}/7")
            print(f" Fluxo validado: {self.resultado['conclusao']['fluxo_validado']}")

        finally:
            await self.limpar_dados_teste()


async def main():
    bateria = BateriaP0FluxoCompleto()
    await bateria.run()


if __name__ == "__main__":
    asyncio.run(main())
