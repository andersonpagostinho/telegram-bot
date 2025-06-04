from unidecode import unidecode
from services.profissional_service import buscar_profissionais_por_servico
from services.firebase_service_async import buscar_subcolecao

async def responder_consulta_informativa(mensagem: str, user_id: str) -> str | None:
    mensagem_normalizada = unidecode(mensagem.lower().strip())

    # 📌 Listar todos os serviços disponíveis
    if "servi" in mensagem_normalizada and ("oferec" in mensagem_normalizada or "tem" in mensagem_normalizada):
        profissionais = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais")
        servicos_set = set()
        for p in profissionais:
            for serv in p.get("servicos", []):
                servicos_set.add(serv.lower().strip())
        if servicos_set:
            lista = "\n".join([f"• {s.capitalize()}" for s in sorted(servicos_set)])
            return f"✨ Serviços oferecidos atualmente:\n\n{lista}"
        return "❌ Nenhum serviço foi encontrado no sistema."

    # 👥 Quem faz determinado serviço
    if "quem faz" in mensagem_normalizada or "qual profissional" in mensagem_normalizada:
        palavras = mensagem_normalizada.split()
        termo_busca = palavras[-1] if palavras else ""
        profissionais = await buscar_profissionais_por_servico([termo_busca], user_id)
        if profissionais:
            nomes = "\n".join([f"• {p}" for p in profissionais])
            return f"👥 Profissionais que fazem *{termo_busca}*:\n\n{nomes}"
        return f"❌ Nenhum profissional encontrado para o serviço *{termo_busca}*."

    # 💰 Preço de determinado serviço
    if "quanto custa" in mensagem_normalizada or "preço" in mensagem_normalizada or "valor" in mensagem_normalizada:
        profissionais = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais")
        termo = (
            mensagem_normalizada
            .replace("quanto custa", "")
            .replace("qual o valor", "")
            .replace("preço", "")
            .replace("valor", "")
            .strip()
        )
        respostas = []
        for p in profissionais:
            nome = p.get("nome", "Profissional")
            precos = p.get("precos", {})
            for servico, preco in precos.items():
                if termo in unidecode(servico.lower()):
                    respostas.append(f"• {servico.capitalize()} com {nome}: R$ {preco}")
        if respostas:
            return f"💰 Valores encontrados:\n\n" + "\n".join(respostas)
        return "❌ Não encontrei preços para esse serviço."

    return None  # Se não for uma intenção informativa
