"""
P0 FASE 6.4 — Auditoria de Integridade
"""

import asyncio
from services.firebase_service_async import buscar_subcolecao

async def auditar_profissionais():
    """Auditoria 1: Elegibilidade de profissionais."""
    tenant_id = "7394370553"
    profs = await buscar_subcolecao(f"Clientes/{tenant_id}/Profissionais") or {}

    print("\n" + "="*80)
    print("AUDITORIA 1: ELEGIBILIDADE PROFISSIONAIS")
    print("="*80 + "\n")

    for nome_id, dados in profs.items():
        nome = dados.get("nome", "N/A")
        servicos = dados.get("servicos", [])
        servicos_str = ", ".join(servicos) if servicos else "NENHUM"

        tem_manicure = any(s.lower() == "manicure" for s in servicos)
        tem_pedicure = any(s.lower() == "pedicure" for s in servicos)
        compativel = tem_manicure and tem_pedicure

        status = "✅ COMPATÍVEL (manicure + pedicure)" if compativel else "❌ INCOMPATÍVEL"

        print(f"ID DB: {nome_id:20}")
        print(f"  Nome: {nome}")
        print(f"  Serviços: {servicos_str}")
        print(f"  Status: {status}\n")


async def auditar_mensagens():
    """Auditoria 2: Mensagens de consulta (linguistic audit)."""
    print("\n" + "="*80)
    print("AUDITORIA 2: MENSAGENS — VERIFICAÇÃO LINGUÍSTICA")
    print("="*80 + "\n")

    # Simular resposta
    resposta_exemplo = """✅ Ótimo! Consegui agendar manicure, pedicure com Bruna.

📅 13/11/2026
⏱️ Duração: 60 minutos

Horários disponíveis:
• 14:00 às 15:00
• 14:20 às 15:20
• 14:40 às 15:40

Qual você prefere?"""

    print("RESPOSTA GERADA:")
    print(resposta_exemplo)
    print("\nVERIFICAÇÃO:")

    problemas_linguisticos = [
        ("Consegui agendar", "❌ ERRADO para read-only — implica criação"),
        ("Agendamento confirmado", "❌ ERRADO para read-only"),
        ("Seu horário está reservado", "❌ ERRADO para read-only"),
    ]

    tem_problema = False
    for frase, desc in problemas_linguisticos:
        if frase in resposta_exemplo:
            print(f"{desc}")
            tem_problema = True

    if tem_problema:
        print("\n⚠️  PROBLEMA DETECTADO: Linguagem imprópria para consulta read-only")
    else:
        print("✅ Linguagem apropriada para consulta read-only")


async def auditar_datas_proximas():
    """Auditoria 3: Busca de datas próximas."""
    print("\n" + "="*80)
    print("AUDITORIA 3: DATAS PRÓXIMAS")
    print("="*80 + "\n")

    import inspect
    from services.varredura_disponibilidade import varrer_disponibilidade_multisservico

    # Verificar se há lógica de datas próximas
    codigo = inspect.getsource(varrer_disponibilidade_multisservico)

    tem_datas_proximas = any(palavra in codigo for palavra in [
        "proxima",
        "próxima",
        "data_seguinte",
        "data_anterior",
        "timedelta",
        "add days",
        "add_day"
    ])

    if tem_datas_proximas:
        print("✅ Lógica de datas próximas PARECE estar implementada")
    else:
        print("❌ Lógica de datas próximas NÃO está implementada")
        print("\nCódigo atual busca apenas:")
        print("  - Uma única data (recebida como parâmetro)")
        print("  - Não há iteração para datas próximas")
        print("  - Necessário implementar se requerido")


async def main():
    await auditar_profissionais()
    await auditar_mensagens()
    await auditar_datas_proximas()

if __name__ == "__main__":
    asyncio.run(main())
