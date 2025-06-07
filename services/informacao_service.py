from unidecode import unidecode
from services.profissional_service import buscar_profissionais_por_servico
from services.firebase_service_async import buscar_subcolecao
import re
import string

async def responder_consulta_informativa(mensagem: str, user_id: str) -> str | None:
    mensagem_normalizada = unidecode(mensagem.lower().strip())

    # 📌 Listar todos os serviços disponíveis
    if "servi" in mensagem_normalizada and ("oferec" in mensagem_normalizada or "tem" in mensagem_normalizada):
        profissionais = (await buscar_subcolecao(f"Clientes/{user_id}/Profissionais")) or {}
        servicos_set = set()
        for p in profissionais.values():
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

    # 💰 Preço de determinado serviço ou tabela completa
    palavras_chave_preco = [
        "quanto custa", "qual o valor", "qual é o valor", "qual é o preço", "preço",
        "valor", "quanto", "cobra", "custa", "quero saber o valor de", "quero saber o valor da",
        "quero saber quanto custa", "valores", "todos os valores", "tabela de preços", 
        "preços dos serviços", "valores dos serviços", "me traga todos os valores"
    ]

    if any(p in mensagem_normalizada for p in palavras_chave_preco):
        profissionais = (await buscar_subcolecao(f"Clientes/{user_id}/Profissionais")) or {}
        profissionais = profissionais.values()

        # Verifica se o usuário pediu TODOS OS VALORES
        if "todos os valores" in mensagem_normalizada or "me traga todos os valores" in mensagem_normalizada \
            or "tabela de preços" in mensagem_normalizada or "valores dos serviços" in mensagem_normalizada \
            or "preços dos serviços" in mensagem_normalizada or (mensagem_normalizada.strip() == "valores"):
            
            respostas = []
            for p in profissionais:
                nome = p.get("nome", "Profissional")
                precos = p.get("precos", {})
                for servico, preco in precos.items():
                    respostas.append(f"• {servico.capitalize()} com {nome}: R$ {preco}")
            if respostas:
                return f"💰 Tabela completa de valores:\n\n" + "\n".join(respostas)
            else:
                return "❌ Não encontrei preços cadastrados para nenhum serviço."

        # Caso seja pergunta por serviço específico
        padrao = r"(?:quanto custa|qual o valor|qual é o valor|qual é o preço|preço|valor|quanto|cobra|custa|quero saber o valor de|quero saber o valor da|quero saber quanto custa)?\s*(?:o|a|uma|um)?\s*(.*)"
        match = re.search(padrao, mensagem_normalizada)
        termo = match.group(1).strip() if match else ""

        # Limpa pontuações
        termo = termo.translate(str.maketrans('', '', string.punctuation)).strip()

        # Remove artigos finais se ainda houver
        termo = re.sub(r"^(o|a|uma|um)\s+", "", termo).strip()

        # Tokenização do termo para comparação inteligente
        termo_tokens = set(unidecode(termo.lower()).split())

        respostas = []
        for p in profissionais:
            nome = p.get("nome", "Profissional")
            precos = p.get("precos", {})
            for servico, preco in precos.items():
                servico_tokens = set(unidecode(servico.lower()).split())
                if termo_tokens & servico_tokens:  # se houver interseção de palavras
                    respostas.append(f"• {servico.capitalize()} com {nome}: R$ {preco}")

        if respostas:
            return f"💰 Valores encontrados:\n\n" + "\n".join(respostas)
        return "❌ Não encontrei preços para esse serviço."

    return None  # Se não for uma intenção informativa
