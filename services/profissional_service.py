# services/profissional_service.py

from services.firebase_service_async import buscar_subcolecao

async def buscar_profissionais_por_servico(servicos: list[str], user_id: str) -> dict:
    """
    Retorna um dicionário com os profissionais que oferecem TODOS os serviços listados.
    """
    profissionais = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais")

    profissionais_filtrados = {}

    for nome, dados in profissionais.items():
        prof_servicos = dados.get("servicos", [])
        if all(servico in prof_servicos for servico in servicos):
            profissionais_filtrados[nome] = dados

    return profissionais_filtrados
