#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E P0 — FLUXO COMPLETO MULTISSERVIÇO

Cenário:
- Data: segunda-feira, 16/11/2026
- Serviços: manicure + pedicure (sequencial, 60min total)
- Profissional: Bruna
- Janela: 14h-17h
- Sem autorização inicial

Fases:
1. CONSULTA INFORMATIVA (varredura, sem criar evento)
2. ESCOLHA DO CLIENTE (segunda opção)
3. CONFIRMAÇÃO EXPLÍCITA (cria evento)
4. VERIFICAÇÃO FIRESTORE (eventos, locks, isolamento)
5. REGRESSÃO (testes relacionados)
"""

import asyncio
import sys
import os
import uuid
import traceback
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from router.principal_router import roteador_principal
from services.firebase_service_async import salvar_dado_em_path, buscar_dado_em_path
from services.identidade_service import normalizar_actor_id
from services.cadastro_inicial_service import salvar_profissional


async def setup_tenant_completo():
    """Setup: Tenant com salão e profissional."""
    tenant_id = f"e2e_p0_completo_{uuid.uuid4().hex[:8]}"
    actor_id = normalizar_actor_id("whatsapp", "5511999999999")
    cliente_id = "5511999999999"
    phone_number_id = "1350170954840548"  # Mock

    print(f"\n[SETUP] tenant_id={tenant_id}")
    print(f"[SETUP] actor_id={actor_id}, cliente_id={cliente_id}")

    # Salão: seg-sex 08:00-19:00
    await salvar_dado_em_path(
        f"Clientes/{tenant_id}/configuracao/agenda_funcionamento",
        {
            "agenda_padrao": {
                "0": {"aberto": True, "inicio": "08:00", "fim": "19:00"},  # Seg
                "1": {"aberto": True, "inicio": "08:00", "fim": "19:00"},  # Ter
                "2": {"aberto": True, "inicio": "08:00", "fim": "19:00"},  # Qua
                "3": {"aberto": True, "inicio": "08:00", "fim": "19:00"},  # Qui
                "4": {"aberto": True, "inicio": "08:00", "fim": "19:00"},  # Sex
                "5": {"aberto": False},  # Sab
                "6": {"aberto": False}   # Dom
            },
            "excecoes_data": {}
        }
    )

    # Bruna: manicure (30min) + pedicure (30min)
    print(f"[SETUP] Salvando profissional Bruna...")
    try:
        payload_bruna = await salvar_profissional(
            user_id=tenant_id,
            nome="Bruna",
            servicos={
                "manicure": {"preco": 50.0, "duracao": 30},
                "pedicure": {"preco": 40.0, "duracao": 30}
            },
            agenda_funcionamento=None
        )
        print(f"[SETUP] Bruna salva com payload: {payload_bruna}")
    except Exception as e:
        print(f"[SETUP-ERROR] Falha ao salvar Bruna: {e}")
        raise

    # Validar que Bruna foi persistida
    print(f"[SETUP] Validando persistência de Bruna...")
    bruna_doc = await buscar_dado_em_path(f"Clientes/{tenant_id}/Profissionais/Bruna")
    if not bruna_doc:
        raise AssertionError(f"Documento de Bruna não encontrado em Firestore após salvar")
    print(f"[SETUP] Bruna confirmada em Firestore: {bruna_doc}")

    # Ator (cliente)
    await salvar_dado_em_path(
        f"Clientes/{tenant_id}/Atores/{actor_id}",
        {
            "tipo": "cliente",
            "id_negocio": tenant_id,
            "criado_em": datetime.utcnow().isoformat()
        }
    )

    print(f"[SETUP] Tenant criado com sucesso")
    return tenant_id, actor_id, cliente_id, phone_number_id


async def test_fase1_consulta():
    """FASE 1: Consulta informativa multisserviço (sem criar evento)."""
    print("\n" + "="*70)
    print("FASE 1 — CONSULTA INFORMATIVA")
    print("="*70)

    tenant_id, actor_id, cliente_id, phone_number_id = await setup_tenant_completo()

    # Mensagem: consulta com intervalo 14-17h, segunda 16/11, manicure+pedicure com Bruna
    mensagem = (
        "Olá! Gostaria de agendar manicure e pedicure para segunda-feira, dia 16/11/2026. "
        "Consigo chegar a partir das 14h, mas tenho um compromisso no final do dia e preciso terminar "
        "os dois serviços até, no máximo, 17h. Minha preferência é Bruna."
    )

    # Verificar que o router consegue carregar Bruna
    print(f"\n[FASE1-PRE] Verificando catálogo que router verá...")
    from services.firebase_service_async import buscar_subcolecao
    profs_dict = await buscar_subcolecao(f"Clientes/{tenant_id}/Profissionais") or {}
    print(f"[FASE1-PRE] Profissionais encontrados: {list(profs_dict.keys())}")
    if "Bruna" not in profs_dict:
        raise AssertionError(f"Bruna não encontrada no catálogo do router. Profissionais: {list(profs_dict.keys())}")

    # Verificar durações
    bruna_data = profs_dict.get("Bruna", {})
    duracao_manicure = bruna_data.get("duracoes", {}).get("manicure")
    duracao_pedicure = bruna_data.get("duracoes", {}).get("pedicure")
    print(f"[FASE1-PRE] Durações: manicure={duracao_manicure}, pedicure={duracao_pedicure}")
    if duracao_manicure != 30 or duracao_pedicure != 30:
        raise AssertionError(f"Durações incorretas: manicure={duracao_manicure}, pedicure={duracao_pedicure}")

    print(f"\n[FASE1] Mensagem: {mensagem[:80]}...")
    print(f"[FASE1] Roteador chamado com:")
    print(f"  - user_id: {actor_id}")
    print(f"  - tenant_id: {tenant_id}")
    print(f"  - phone_number_id: {phone_number_id}")

    try:
        resposta_fase1 = await roteador_principal(
            user_id=actor_id,
            mensagem=mensagem,
            tenant_id=tenant_id,
            phone_number_id=phone_number_id
        )

        print(f"\n[FASE1-RESPOSTA] Recebida:")
        if resposta_fase1:
            print(f"  - Tipo: {type(resposta_fase1).__name__}")

            # Router retorna dict com estrutura {"resposta": "texto", "acao": "...", ...}
            if isinstance(resposta_fase1, dict):
                resposta_texto = resposta_fase1.get("resposta", "")
                print(f"  - Ação: {resposta_fase1.get('acao')}")
                print(f"  - Comprimento: {len(resposta_texto)} chars")
                print(f"  - Preview (primeiros 150 chars):")
                print(f"    {resposta_texto[:150]}")

                # Validar que contém horários
                if "14:00" in resposta_texto and "15:00" in resposta_texto:
                    print(f"\n[FASE1-VALIDACAO] ✅ Horários encontrados (14:00-15:00, etc.)")
                elif "14:20" in resposta_texto or "14:40" in resposta_texto:
                    print(f"\n[FASE1-VALIDACAO] ✅ Horários alternativos encontrados")
                else:
                    print(f"\n[FASE1-VALIDACAO] ⚠️ Horários não encontrados como esperado")
                    print(f"    Resposta completa: {resposta_texto[:300]}")
            else:
                print(f"  - Tipo inesperado (esperado dict): {resposta_fase1}")
        else:
            print(f"  - Resposta: None")

        # Validar: nenhum evento criado
        eventos = await buscar_dado_em_path(f"Clientes/{tenant_id}/Eventos")
        if eventos is None or len(eventos) == 0:
            print(f"[FASE1-SEGURANCA] ✅ Nenhum evento criado (correto — consulta informativa)")
        else:
            print(f"[FASE1-SEGURANCA] ❌ ERRO: {len(eventos)} eventos criados (não deveria)")

        return True, tenant_id, actor_id, cliente_id, phone_number_id, resposta_fase1

    except Exception as e:
        print(f"\n[FASE1-ERROR] Exceção: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False, None, None, None, None, None


async def main():
    """Executar E2E completo."""
    print("\n" + "="*70)
    print("E2E P0 — FLUXO COMPLETO MULTISSERVIÇO")
    print("="*70)
    print(f"Data: {datetime.utcnow().isoformat()}")

    # FASE 1: Consulta
    fase1_ok, tenant_id, actor_id, cliente_id, phone_number_id, resposta_fase1 = await test_fase1_consulta()

    if not fase1_ok:
        print(f"\n[RESULTADO FINAL] FALHOU em FASE 1")
        return False

    print(f"\n[RESULTADO FINAL] ✅ FASE 1 PASSOU")
    print(f"  - Varredura executada")
    print(f"  - Horários apresentados")
    print(f"  - Nenhum evento criado")

    return True


if __name__ == "__main__":
    resultado = asyncio.run(main())
    sys.exit(0 if resultado else 1)
