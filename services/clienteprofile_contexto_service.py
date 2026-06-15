# -*- coding: utf-8 -*-
# services/clienteprofile_contexto_service.py
"""
P1.2B: Extração de Contexto Neutro do ClienteProfile
======================================================

Objetivo: Motor determinístico lê ClienteProfile para ENTENDER contexto.
Constraint: Zero influência em decisões, apenas contexto interno.

Campos extraídos (NEUTROS):
- total_eventos (métrica de volume)
- profissional_mais_frequente (padrão observado, não sugestão)
- servico_mais_frequente (padrão observado, não sugestão)
- ultima_contato (timestamp para calcular inatividade)
- cliente_novo (flag: total_eventos < 5)
- cliente_veterano (flag: total_eventos > 20)
- cliente_inativo (flag: última_contato > 30 dias)
- fonte: "clienteprofile" (metadata)
- modo: "contexto_apenas" (metadata)

Proibido em P1.2B:
- profissional_sugestao (é P1.3)
- servico_sugestao (é P1.3)
- reengajement_elegivel (é P1.3+)
- premium_offer_elegivel (é P1.3+)
- pode_pular_prof (é P1.3)
- pode_pular_serv (é P1.3)

Referência:
- SPEC_P1_2B_MOTOR_CONSULTA_CLIENTEPROFILE.md
- SPEC_SEGURANCA_CLIENTEPROFILE_NAO_DECIDE.md
"""

from datetime import datetime


def extrair_contexto_motor(profile: dict | None) -> dict | None:
    """
    Extrai contexto neutro do ClienteProfile para o motor.

    Args:
        profile: dict com estrutura ClienteProfile ou None

    Returns:
        dict com contexto neutro ou None

    Estrutura de saída (APENAS campos neutros):
    {
        "total_eventos": int,
        "profissional_mais_frequente": str | None,
        "servico_mais_frequente": str | None,
        "ultima_contato": str | None,
        "cliente_novo": bool,
        "cliente_veterano": bool,
        "cliente_inativo": bool,
        "fonte": "clienteprofile",
        "modo": "contexto_apenas"
    }
    """

    if not profile:
        return None

    try:
        # ========================================================
        # Extrair métricas (neutro)
        # ========================================================
        historico = profile.get("historico") or {}
        tendencias = profile.get("tendencias") or {}

        total_eventos = historico.get("total_eventos", 0)
        profissional_mais_frequente = tendencias.get("profissional_mais_frequente")
        servico_mais_frequente = tendencias.get("servico_mais_frequente")
        ultima_contato = historico.get("ultima_contato")

        # ========================================================
        # Calcular flags de categorização (neutro)
        # ========================================================
        cliente_novo = total_eventos < 5
        cliente_veterano = total_eventos > 20

        # Flag de inatividade
        cliente_inativo = False
        if ultima_contato:
            try:
                ultima_dt = datetime.fromisoformat(ultima_contato)
                dias_inativo = (datetime.now() - ultima_dt).days
                cliente_inativo = dias_inativo > 30
            except (ValueError, TypeError):
                pass

        # ========================================================
        # Montar estrutura neutra (APENAS contexto, sem ação)
        # ========================================================
        contexto_motor = {
            # Métricas (neutro)
            "total_eventos": total_eventos,
            "profissional_mais_frequente": profissional_mais_frequente,
            "servico_mais_frequente": servico_mais_frequente,
            "ultima_contato": ultima_contato,

            # Flags (neutro)
            "cliente_novo": cliente_novo,
            "cliente_veterano": cliente_veterano,
            "cliente_inativo": cliente_inativo,

            # Metadados (neutro)
            "fonte": "clienteprofile",
            "modo": "contexto_apenas",
        }

        return contexto_motor

    except Exception as e:
        print(f"[P1.2B] Erro ao extrair contexto: {e}", flush=True)
        return None
