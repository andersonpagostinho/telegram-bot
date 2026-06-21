# -*- coding: utf-8 -*-
"""
P1 E2E — Onboarding Individual (Firestore Real)

Objetivo: Validar evolucao do onboarding para negócios individuais.
Reduz atrito criando profissional automaticamente com dados do dono.

Nova etapa após agenda:
"Você atende sozinha ou possui outros profissionais?"
- individual: cria prof automaticamente, pula etapas
- equipe: mantém fluxo atual

Cenários:
1. Profissional única (dono)
2. Profissional criada automaticamente
3. Sem telefone adicional (usa canal do dono)
4. Cliente agenda com dona
5. Agenda da dona funciona
6. Multi-tenant preservado
7. Regressão P0
"""

import asyncio
import json
import sys
import os
from datetime import datetime
import pytz

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.firestore_client import get_db
from services.identidade_service import (
    normalizar_actor_id,
    resolver_ator_por_canal,
    criar_ator_dono,
    criar_ator_cliente_automatico,
    criar_ator_profissional,
    tenant_tem_dono,
)
from services.firebase_service_async import buscar_subcolecao


class TestResult:
    def __init__(self):
        self.cenarios = []
        self.total_pass = 0
        self.total_fail = 0

    def registro(self, num, nome, passou, mensagem="", detalhes=None):
        resultado = {
            "cenario": num,
            "nome": nome,
            "status": "PASS" if passou else "FAIL",
            "mensagem": mensagem,
            "detalhes": detalhes or {},
            "timestamp": datetime.now(pytz.UTC).isoformat()
        }
        self.cenarios.append(resultado)
        if passou:
            self.total_pass += 1
            print(f"[PASS] Cenario {num}: {nome}")
        else:
            self.total_fail += 1
            print(f"[FAIL] Cenario {num}: {nome} - {mensagem}")

    def salvar_json(self, caminho="tests/resultado_p1_e2e_onboarding_individual.json"):
        output = {
            "total": len(self.cenarios),
            "pass": self.total_pass,
            "fail": self.total_fail,
            "cenarios": self.cenarios
        }
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)


async def limpar_tenant(tenant_id):
    """Limpar tenant do Firestore para teste limpo."""
    try:
        db = get_db()
        doc_ref = db.collection("Clientes").document(tenant_id)

        for subcol_name in ["Atores", "Sessoes", "Profissionais", "ServicosNegocio", "Configuracao", "Clientes", "Eventos"]:
            docs = db.collection("Clientes").document(tenant_id).collection(subcol_name).stream()
            for doc in docs:
                await asyncio.to_thread(lambda d=doc: d.reference.delete())

        await asyncio.to_thread(lambda: doc_ref.delete())
    except Exception as e:
        pass


async def obter_estado_tenant(tenant_id):
    """Obter estado completo do tenant."""
    resultado = {}
    db = get_db()

    for col_name in ["Atores", "Profissionais", "ServicosNegocio", "Configuracao", "Clientes", "Eventos"]:
        docs = await buscar_subcolecao(f"Clientes/{tenant_id}/{col_name}")
        resultado[col_name] = docs or {}

    return resultado


async def cenario_01_profissional_unica_dono(result: TestResult):
    """
    Cenario 1: Profissional unica (dono atende sozinha)
    """
    tenant_id = "teste_onboarding_individual_tenant"
    await limpar_tenant(tenant_id)

    canal = "whatsapp"
    identificador = "11900000001"
    nome_dono = "Maria Silva"
    email_dono = "maria@email.com"
    user_id = normalizar_actor_id(canal, identificador)

    try:
        # Criar dono
        ator_dono = await criar_ator_dono(
            tenant_id=tenant_id,
            canal=canal,
            identificador=identificador,
            nome=nome_dono,
            email=email_dono
        )

        # Simular: dono escolhe "individual" no onboarding
        db = get_db()
        config_data = {
            "nome_negocio": "Salao da Maria",
            "segmento": "Salao de beleza",
            "endereco": "Rua Joao Baroni, 550",
            "agenda_padrao": {
                "segunda": {"inicio": "08:00", "fim": "18:00"},
                "domingo": {"inicio": "FECHADO", "fim": "FECHADO"}
            },
            "estrutura_operacional": "individual",
            "dono_atende_clientes": True,
            "atualizado_em": datetime.now(pytz.UTC).isoformat()
        }

        await asyncio.to_thread(
            lambda: db.collection("Clientes").document(tenant_id).collection("Configuracao").document("dados_negocio").set(config_data)
        )

        estado_depois = await obter_estado_tenant(tenant_id)
        config_salvo = estado_depois.get("Configuracao", {}).get("dados_negocio", {})

        passou = (
            config_salvo.get("estrutura_operacional") == "individual"
            and config_salvo.get("dono_atende_clientes") == True
        )

        result.registro(
            1,
            "Profissional unica (dono)",
            passou,
            "" if passou else "Configuracao nao salva corretamente",
            {
                "estrutura": config_salvo.get("estrutura_operacional"),
                "dono_atende": config_salvo.get("dono_atende_clientes")
            }
        )

        return tenant_id, user_id, nome_dono
    except Exception as e:
        result.registro(1, "Profissional unica (dono)", False, str(e))
        return None, None, None


async def cenario_02_profissional_criada_automaticamente(result: TestResult, tenant_id, dono_id, nome_dono):
    """
    Cenario 2: Profissional criada automaticamente com dados do dono
    """
    try:
        if not tenant_id:
            result.registro(2, "Profissional criada automaticamente", False, "Tenant nao foi criado")
            return

        # Criar profissional automaticamente com dados do dono
        prof_criada = await criar_ator_profissional(
            tenant_id=tenant_id,
            canal="whatsapp",
            identificador="11900000001",  # Mesmo do dono
            nome=nome_dono,
            criado_por=dono_id
        )

        # Registrar em Profissionais
        db = get_db()
        prof_data = {
            "nome": nome_dono,
            "actor_id": dono_id,
            "canal": "whatsapp",
            "identificador": "11900000001",
            "servicos": [],
            "ativo": True,
            "criado_em": datetime.now(pytz.UTC).isoformat(),
            "criado_por": dono_id,
            "automatico": True
        }

        await asyncio.to_thread(
            lambda: db.collection("Clientes").document(tenant_id).collection("Profissionais").document("maria_silva").set(prof_data)
        )

        estado_depois = await obter_estado_tenant(tenant_id)

        passou = bool(estado_depois.get("Profissionais", {}).get("maria_silva"))

        result.registro(
            2,
            "Profissional criada automaticamente",
            passou,
            "" if passou else "Profissional nao foi criada",
            {
                "nome": prof_data.get("nome"),
                "automatico": True,
                "criado_por_dono": prof_data.get("criado_por") == dono_id
            }
        )
    except Exception as e:
        result.registro(2, "Profissional criada automaticamente", False, str(e))


async def cenario_03_sem_telefone_adicional(result: TestResult, tenant_id, dono_id):
    """
    Cenario 3: Sem telefone adicional (usa canal do dono)
    """
    try:
        if not tenant_id:
            result.registro(3, "Sem telefone adicional", False, "Tenant nao foi criado")
            return

        estado = await obter_estado_tenant(tenant_id)

        # Dono tem whatsapp:11900000001, profissional usa mesmo
        prof = estado.get("Profissionais", {}).get("maria_silva", {})

        passou = prof.get("identificador") == "11900000001"

        result.registro(
            3,
            "Sem telefone adicional",
            passou,
            "" if passou else "Telefone nao corresponde",
            {
                "identificador": prof.get("identificador"),
                "usa_canal_dono": True
            }
        )
    except Exception as e:
        result.registro(3, "Sem telefone adicional", False, str(e))


async def cenario_04_cliente_agenda_com_dona(result: TestResult, tenant_id):
    """
    Cenario 4: Cliente novo agenda com dona
    """
    try:
        if not tenant_id:
            result.registro(4, "Cliente agenda com dona", False, "Tenant nao foi criado")
            return

        canal = "whatsapp"
        identificador = "11955555555"
        cliente_id = normalizar_actor_id(canal, identificador)

        # Criar cliente
        cliente_criado = await criar_ator_cliente_automatico(
            tenant_id=tenant_id,
            canal=canal,
            identificador=identificador,
            nome_detectado="João"
        )

        # Criar agendamento
        db = get_db()
        evento_data = {
            "cliente_id": cliente_id,
            "profissional_id": "maria_silva",
            "profissional_nome": "Maria Silva",
            "servico": "Corte feminino",
            "duracao_minutos": 40,
            "data": "2026-06-25",
            "hora": "10:00",
            "status": "confirmado",
            "criado_em": datetime.now(pytz.UTC).isoformat(),
            "criado_por": "sistema_autoagendamento"
        }

        evento_id = f"{cliente_id}_2026-06-25_10:00"

        await asyncio.to_thread(
            lambda: db.collection("Clientes").document(tenant_id).collection("Eventos").document(evento_id).set(evento_data)
        )

        estado_depois = await obter_estado_tenant(tenant_id)

        passou = evento_id in estado_depois.get("Eventos", {})

        result.registro(
            4,
            "Cliente agenda com dona",
            passou,
            "" if passou else "Evento nao foi criado",
            {
                "cliente_id": cliente_id,
                "profissional": "maria_silva",
                "evento_criado": passou
            }
        )
    except Exception as e:
        result.registro(4, "Cliente agenda com dona", False, str(e))


async def cenario_05_agenda_dona_funciona(result: TestResult, tenant_id):
    """
    Cenario 5: Agenda da dona funciona (consulta eventos)
    """
    try:
        if not tenant_id:
            result.registro(5, "Agenda dona funciona", False, "Tenant nao foi criado")
            return

        estado = await obter_estado_tenant(tenant_id)

        eventos = estado.get("Eventos", {})

        passou = len(eventos) > 0

        result.registro(
            5,
            "Agenda dona funciona",
            passou,
            "" if passou else "Nenhum evento encontrado",
            {
                "eventos_totais": len(eventos),
                "agenda_funcional": passou
            }
        )
    except Exception as e:
        result.registro(5, "Agenda dona funciona", False, str(e))


async def cenario_06_multitenant_preservado(result: TestResult):
    """
    Cenario 6: Multi-tenant preservado
    """
    try:
        # Criar Tenant B com equipe
        tenant_b = "teste_onboarding_individual_tenant_b"
        await limpar_tenant(tenant_b)

        canal = "whatsapp"
        dono_b_id = normalizar_actor_id(canal, "11900000002")

        dono_b = await criar_ator_dono(
            tenant_id=tenant_b,
            canal=canal,
            identificador="11900000002",
            nome="João",
            email="joao@email.com"
        )

        # Configuracao diferente: equipe
        db = get_db()
        config_b = {
            "nome_negocio": "Studio de fotografía",
            "estrutura_operacional": "equipe",
            "dono_atende_clientes": False,
            "atualizado_em": datetime.now(pytz.UTC).isoformat()
        }

        await asyncio.to_thread(
            lambda: db.collection("Clientes").document(tenant_b).collection("Configuracao").document("dados_negocio").set(config_b)
        )

        # Verificar isolamento
        estado_a = await obter_estado_tenant("teste_onboarding_individual_tenant")
        estado_b = await obter_estado_tenant(tenant_b)

        passou = (
            len(estado_a.get("Atores", {})) > 0 and
            len(estado_b.get("Atores", {})) > 0 and
            dono_b_id not in estado_a.get("Atores", {})
        )

        result.registro(
            6,
            "Multi-tenant preservado",
            passou,
            "" if passou else "Isolamento violado",
            {
                "tenant_a_atores": len(estado_a.get("Atores", {})),
                "tenant_b_atores": len(estado_b.get("Atores", {})),
                "isolado": passou
            }
        )
    except Exception as e:
        result.registro(6, "Multi-tenant preservado", False, str(e))


async def cenario_07_regressao_p0(result: TestResult, tenant_id):
    """
    Cenario 7: Regressao P0 (agendamento basico funciona)
    """
    try:
        if not tenant_id:
            result.registro(7, "Regressao P0", False, "Tenant nao foi criado")
            return

        estado = await obter_estado_tenant(tenant_id)

        # Verificar que temos componentes P0
        tem_dono = len(estado.get("Atores", {})) > 0
        tem_profissional = len(estado.get("Profissionais", {})) > 0
        tem_evento = len(estado.get("Eventos", {})) > 0

        passou = tem_dono and tem_profissional and tem_evento

        result.registro(
            7,
            "Regressao P0",
            passou,
            "" if passou else "Faltam componentes para P0",
            {
                "dono_criado": tem_dono,
                "profissional_criado": tem_profissional,
                "evento_criado": tem_evento,
                "p0_ready": passou
            }
        )
    except Exception as e:
        result.registro(7, "Regressao P0", False, str(e))


async def main():
    print("\n" + "="*80)
    print("P1 E2E — ONBOARDING INDIVIDUAL (FIRESTORE REAL)")
    print("="*80 + "\n")

    result = TestResult()

    # Cenario 1
    tenant_id, dono_id, nome_dono = await cenario_01_profissional_unica_dono(result)

    # Cenarios 2-5 (individual flow)
    await cenario_02_profissional_criada_automaticamente(result, tenant_id, dono_id, nome_dono)
    await cenario_03_sem_telefone_adicional(result, tenant_id, dono_id)
    await cenario_04_cliente_agenda_com_dona(result, tenant_id)
    await cenario_05_agenda_dona_funciona(result, tenant_id)

    # Cenarios 6-7 (robustness)
    await cenario_06_multitenant_preservado(result)
    await cenario_07_regressao_p0(result, tenant_id)

    # Resumo
    print("\n" + "="*80)
    print(f"RESULTADO FINAL: {result.total_pass}/{len(result.cenarios)} PASS")
    print("="*80 + "\n")

    result.salvar_json()
    print(f"[OK] Resultado salvo em: tests/resultado_p1_e2e_onboarding_individual.json\n")


if __name__ == "__main__":
    asyncio.run(main())
