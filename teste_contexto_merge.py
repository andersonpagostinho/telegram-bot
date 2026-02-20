import asyncio
from services.firebase_service_async import deletar_dado_em_path
from utils.contexto_temporario import salvar_contexto_temporario, carregar_contexto_temporario

USER_ID = "teste_merge_001"  # pode deixar assim


async def main():
    print("\n=== 1) Limpando e criando contexto inicial ===")
    path = f"Clientes/{USER_ID}/MemoriaTemporaria/contexto"
    await deletar_dado_em_path(path)

    await salvar_contexto_temporario(USER_ID, {
        "servico": "escova",
        "data_hora": "2026-02-20 16:00",
        "profissional_escolhido": "Bruna",
        "historico": [{"role": "user", "content": "quero agendar"}],
    })

    ctx1 = await carregar_contexto_temporario(USER_ID)
    print("Contexto após inicial:", ctx1)

    print("\n=== 2) Salvando APENAS um campo novo (simulando update parcial) ===")
    await salvar_contexto_temporario(USER_ID, {
        "evento_criado": True
    })

    ctx2 = await carregar_contexto_temporario(USER_ID)
    print("Contexto após update parcial:", ctx2)

    print("\n=== 3) Checagem objetiva ===")
    faltando = []
    for campo in ["servico", "data_hora", "profissional_escolhido", "historico", "evento_criado"]:
        if campo not in (ctx2 or {}):
            faltando.append(campo)

    if faltando:
        print("❌ FALHOU: campos sumiram:", faltando)
    else:
        print("✅ OK: merge funcionando (nenhum campo sumiu).")


if __name__ == "__main__":
    asyncio.run(main())
