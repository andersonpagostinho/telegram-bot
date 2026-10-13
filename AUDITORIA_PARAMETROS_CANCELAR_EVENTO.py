#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUDITORIA: Parâmetros passados para cancelar_evento()

Objetivo: Registrar EXATAMENTE qual é cada parâmetro:
- user_id (valor recebido em principal_router linha 3714-3723)
- event_id (valor obtido de cancelamento_pendente)
- tenant_id (dono_id passado)

E comparar com o que cancelar_evento() usa para procurar.
"""

print("\n" + "=" * 80)
print("AUDITORIA: Parâmetros para cancelar_evento()")
print("=" * 80)

print("""
CÓDIGO-FONTE EM principal_router.py (linha 3714-3723):

    evento_id = cancelamento_pendente.get("evento_id")

    if evento_id:
        ok = await cancelar_evento(
            user_id=user_id,                                    # PARÂMETRO 1
            event_id=evento_id,                                 # PARÂMETRO 2
            cancelado_por_tipo="cliente",
            tenant_id=dono_id,                                  # PARÂMETRO 3
        )

VALORES ESPERADOS (com base na auditoria de Firestore):
    Firestore caminho do evento: Clientes/7394370553/Eventos/whatsapp:5511991382080_bruna_2026-10-12_10:00
    evento_id na sessão: whatsapp:5511991382080_bruna_2026-10-12_10:00
    dono_id (tenant): 7394370553
    user_id (actor): provavelmente whatsapp:5511991382080 ou 5511991382080
""")

print("\n" + "-" * 80)
print("ANÁLISE: Fluxo em cancelar_evento()")
print("-" * 80)

print("""
Em cancelar_evento(url/services/event_service_async.py linha 276-292):

    if tenant_id:
        user_id_efetivo = tenant_id                            # <-- Usa dono_id
        tipo_usuario = "cliente"
        path = f"Clientes/{user_id_efetivo}/Eventos/{event_id}"

    path RESULTANTE = f"Clientes/{tenant_id}/Eventos/{event_id}"
    path RESULTANTE = f"Clientes/7394370553/Eventos/{event_id}"

DEPOIS em linha 295:
    ev = await buscar_dado_em_path(path) or {}

VALIDAÇÃO em linha 302-310:
    cliente_id_evento = ev.get("cliente_id")           # Do Firestore: "whatsapp:5511991382080"

    if tipo_usuario == "cliente":
        if cliente_id_evento != user_id:                # AQUI: Comparação
            return False

    Comparison: cliente_id_evento (whatsapp:5511991382080) != user_id (?)
""")

print("\n" + "-" * 80)
print("DIVERGÊNCIA PROVÁVEL")
print("-" * 80)

print("""
CENÁRIO 1: Se user_id = "5511991382080" (SEM prefixo whatsapp:)
    - Firestore cliente_id: "whatsapp:5511991382080"
    - user_id recebido: "5511991382080"
    - Comparação: "whatsapp:5511991382080" != "5511991382080"
    - RESULTADO: False (bloqueado)

CENÁRIO 2: Se user_id = "whatsapp:5511991382080" (COM prefixo)
    - Firestore cliente_id: "whatsapp:5511991382080"
    - user_id recebido: "whatsapp:5511991382080"
    - Comparação: "whatsapp:5511991382080" == "whatsapp:5511991382080"
    - RESULTADO: True (permitido)
""")

print("\n" + "=" * 80)
print("DIAGNÓSTICO PROVÁVEL")
print("=" * 80)

print("""
PONTO DE FALHA:

Linha 306 em services/event_service_async.py:

    if cliente_id_evento != user_id:
        logger.warning(f"[CANCELAMENTO_BLOQUEADO] usuario={user_id} nao eh cliente_id={cliente_id_evento}")
        return False

VALOR DE cliente_id_evento (do Firestore):
    "whatsapp:5511991382080"

POSSÍVEL VALOR DE user_id (recebido em principal_router):
    "5511991382080" (SEM prefixo whatsapp:)

RESULTADO:
    "whatsapp:5511991382080" != "5511991382080" → BLOQUEADO

CAUSA-RAIZ:

Em principal_router.py, quando cancelamento é acionado, o parâmetro `user_id`
pode estar sendo passado como "5511991382080" (sem prefixo whatsapp:),
mas o Firestore tem "whatsapp:5511991382080" (com prefixo).

A validação de ownership falha porque compara values com formatos DIFERENTES.
""")

print("\n" + "=" * 80)
print("SOLUÇÃO PROPOSTA (SEM APLICAR)")
print("=" * 80)

print("""
Há 2 opções:

OPÇÃO A: Normalizar user_id ANTES de passar para cancelar_evento()
   Arquivo: router/principal_router.py linha 3718-3723
   Mudança: Garantir que user_id tenha prefixo "whatsapp:" se for WhatsApp

   user_id_normalizado = user_id if user_id.startswith("whatsapp:") else f"whatsapp:{user_id}"
   ok = await cancelar_evento(
       user_id=user_id_normalizado,
       ...
   )

OPÇÃO B: Normalizar DENTRO de cancelar_evento() antes de validação
   Arquivo: services/event_service_async.py linha 306
   Mudança: Comparar removendo prefixos para validação

   cliente_id_sem_prefixo = cliente_id_evento.split(":")[-1]
   user_id_sem_prefixo = user_id.split(":")[-1]

   if cliente_id_sem_prefixo != user_id_sem_prefixo:
       return False

OPÇÃO C: Adicionar guard com ambos os formatos
   Arquivo: services/event_service_async.py linha 306
   Mudança: Aceitar ambos formatos

   cliente_id_evento == user_id or cliente_id_evento.endswith(user_id)
""")

print("\n" + "=" * 80)
print("FIM DA AUDITORIA")
print("=" * 80 + "\n")
