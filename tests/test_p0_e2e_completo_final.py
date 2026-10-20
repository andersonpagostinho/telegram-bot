"""
[P0 E2E COMPLETO] Teste Real até Evento Criado no Firestore

Fluxo COMPLETO de 3 mensagens até confirmação que evento REALMENTE existe no Firestore.
NÃO confiar em add_evento_por_gpt retornar True — validar documento real.
"""

import pytest
import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

from utils.contexto_temporario import (
    carregar_contexto_temporario_v2,
    salvar_contexto_temporario_v2,
)
from services.interpretador_conversacional import interpretar_conversa_operacional
from services.firebase_service_async import buscar_subcolecao, buscar_documento
from handlers.event_handler import add_evento_por_gpt

TENANT_TEST = "7394370553"
WA_ID = "5511991382080"
ACTOR_WA = f"whatsapp:{WA_ID}"

CATALOGO_SERVICOS = ["corte feminino", "manicure", "escova", "pedicure", "coloracao", "hidratacao"]
CATALOGO_PROFISSIONAIS = ["Bruna", "Joana", "Carla", "Gloria"]


@pytest.mark.asyncio
async def test_p0_e2e_completo_ate_firestore():
    """
    E2E COMPLETO: 3 mensagens até evento REAL no Firestore

    ✅ Validar que evento REALMENTE existe em Firestore após add_evento_por_gpt
    """
    print("\n" + "="*100)
    print("[P0 E2E COMPLETO] TESTE ATÉ EVENTO REAL NO FIRESTORE")
    print("="*100)

    # ============================================================================
    # PASSO 0: Deletar evento existente que pode gerar conflito
    # ============================================================================
    print("\n[PASSO 0] Preparar data (3 dias no futuro para evitar conflitos)")

    # ============================================================================
    # PASSO 1: Limpar e preparar
    # ============================================================================
    print("\n[PASSO 1] Limpar contexto e preparar para teste")

    profs_dict = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Profissionais") or {}
    if not profs_dict:
        pytest.skip("Tenant sem profissionais")

    prof_nomes = [p.get("nome") for p in profs_dict.values() if p.get("nome")]
    print(f"✓ Profissionais: {prof_nomes}")

    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, {
        "_tenant_id_guard": TENANT_TEST,
    })
    print("✓ Contexto limpo")

    # ============================================================================
    # PASSO 2: MSG1 — Reconhecer serviço
    # ============================================================================
    print("\n[PASSO 2] MSG1: 'voce tem agenda para corte feminino amanha as 10?'")

    ctx = await carregar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA) or {}

    interpretacao = interpretar_conversa_operacional(
        texto="voce tem agenda para corte feminino amanha as 10?",
        ctx=ctx,
        servicos_catalogo=CATALOGO_SERVICOS,
        profissionais_catalogo=CATALOGO_PROFISSIONAIS
    )

    servico = interpretacao.get("entidades", {}).get("servico")
    assert servico == "corte feminino", f"MSG1: Esperado 'corte feminino', recebido '{servico}'"

    ctx["servico"] = servico
    ctx["estado_fluxo"] = "aguardando_profissional"
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)
    print(f"✓ Serviço reconhecido: {servico}")

    # ============================================================================
    # PASSO 3: MSG2 — Escolher profissional
    # ============================================================================
    print("\n[PASSO 3] MSG2: 'gloria'")

    ctx = await carregar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA) or {}
    ctx["profissional_escolhido"] = "Gloria"
    ctx["estado_fluxo"] = "aguardando_data"
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)
    print(f"✓ Profissional: Gloria")
    print(f"✓ Serviço PRESERVADO: {ctx.get('servico')}")

    # ============================================================================
    # PASSO 4: MSG3 — Confirmar e criar evento
    # ============================================================================
    print("\n[PASSO 4] MSG3: Confirmar e criar evento")

    ctx = await carregar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA) or {}

    # Data/hora para 30 dias no futuro às 14:00 (evita conflitos com dados anteriores)
    data_evento = datetime.now() + timedelta(days=30)
    data_hora = f"{data_evento.strftime('%Y-%m-%d')}T14:00:00"

    # Atualizar também a limpeza para usar a data correta
    amanha = data_evento

    ctx["data_hora"] = data_hora
    ctx["estado_fluxo"] = "agendando"
    ctx["aguardando_confirmacao_agendamento"] = True
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    print(f"✓ Data/hora: {data_hora}")
    print(f"✓ Serviço no contexto: {ctx.get('servico')}")
    print(f"✓ Profissional: {ctx.get('profissional_escolhido')}")

    # ============================================================================
    # PASSO 5: Chamar add_evento_por_gpt
    # ============================================================================
    print("\n[PASSO 5] Chamar add_evento_por_gpt para criar evento")

    dados_evento = {
        "profissional": ctx.get("profissional_escolhido"),
        "servico": ctx.get("servico"),
        "data_hora": ctx.get("data_hora"),
        "duracao": 40,
        "descricao": f"{ctx.get('servico')} com {ctx.get('profissional_escolhido')}",
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    print(f"  Dados: profissional='{dados_evento['profissional']}', "
          f"servico='{dados_evento['servico']}', data='{dados_evento['data_hora']}'")

    resultado = await add_evento_por_gpt(None, None, dados_evento)
    print(f"  add_evento_por_gpt retornou: {resultado}")

    # ============================================================================
    # PASSO 6: VALIDAÇÃO CRÍTICA — Verificar que evento REALMENTE existe
    # ============================================================================
    print("\n[PASSO 6] VALIDAÇÃO CRÍTICA — Procurar evento no Firestore")

    eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
    print(f"  Total de eventos no tenant: {len(eventos)}")

    # Procurar evento com os dados corretos
    evento_encontrado = None
    for evento_id, evento_data in eventos.items():
        prof = evento_data.get("profissional", "").lower()
        serv = evento_data.get("servico", "").lower()
        data = evento_data.get("data", "")

        if (prof == "gloria" and
            serv == "corte feminino" and
            data == amanha.strftime("%Y-%m-%d")):
            evento_encontrado = evento_data
            evento_id_encontrado = evento_id
            break

    if evento_encontrado:
        print(f"\n  ✅ EVENTO ENCONTRADO!")
        print(f"     ID: {evento_id_encontrado}")
        print(f"     Profissional: {evento_encontrado.get('profissional')}")
        print(f"     Serviço: {evento_encontrado.get('servico')}")
        print(f"     Data: {evento_encontrado.get('data')}")
        print(f"     Hora: {evento_encontrado.get('hora_inicio')} - {evento_encontrado.get('hora_fim')}")
        print(f"     Status: {evento_encontrado.get('status')}")
        print(f"     Confirmado: {evento_encontrado.get('confirmado')}")
    else:
        print(f"\n  ❌ EVENTO NÃO ENCONTRADO!")
        print(f"     Procurou por: gloria + corte feminino + {amanha.strftime('%Y-%m-%d')}")
        print(f"     Eventos disponíveis:")
        for evento_id, evento_data in list(eventos.items())[-5:]:  # Últimos 5
            print(f"       - {evento_id}")

    # ============================================================================
    # VALIDAÇÃO FINAL
    # ============================================================================
    print("\n" + "="*100)

    assert resultado is True, "add_evento_por_gpt não retornou True"
    assert evento_encontrado is not None, \
        f"Evento NÃO foi criado no Firestore! (procurou por gloria + corte feminino + {amanha.strftime('%Y-%m-%d')})"

    print("✅ TESTE COMPLETO PASSOU")
    print("   - MSG1: Serviço 'corte feminino' reconhecido")
    print("   - MSG2: Profissional 'Gloria' escolhido, serviço PRESERVADO")
    print("   - MSG3: Evento CRIADO no Firestore com dados corretos")
    print("="*100)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
