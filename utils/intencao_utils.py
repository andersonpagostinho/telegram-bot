# utils/intencao_utils.py

def identificar_intencao(texto):
    texto = texto.lower()

    comandos = {
        "start": ["start", "iniciar", "começar", "ativar bot"],
        "help": ["ajuda", "help", "como usar", "comandos disponíveis"],
        "meusdados": ["meus dados", "ver meus dados", "meu perfil"],
        "meuestilo": ["meu estilo", "meu tipo de negócio", "tipo de empresa"],

        "adicionar_tarefa": ["nova tarefa", "adicionar tarefa", "criar tarefa"],
        "listar_tarefas": ["listar tarefas", "ver tarefas", "mostrar tarefas", "minhas tarefas"],
        "listar_prioridade": ["listar por prioridade", "tarefas por prioridade", "prioridade de tarefas"],
        "limpar_tarefas": ["limpar tarefas", "apagar tarefas", "remover tarefas"],

        "adicionar_evento": ["nova reunião", "marcar reunião", "agendar reunião", "novo evento", "criar evento"],
        "listar_eventos": ["listar eventos", "ver eventos", "mostrar agenda", "meus eventos"],
        "confirmar_reuniao": ["confirmar reunião", "confirmar evento", "confirmar agendamento"],
        "confirmar_presenca": ["confirmar presença", "vou participar", "presença confirmada"],
        "debug_eventos": ["testar eventos", "debug eventos", "evento de teste"],

        "conectar_email": ["conectar e-mail", "logar no email", "autenticar e-mail"],
        "authcallback": ["finalizar autenticação", "callback", "confirmar e-mail"],
        "ler_emails": ["ler emails", "ler e-mails", "ver emails", "quero ver os e-mails"],
        "emails_prioritarios": ["emails importantes", "e-mails prioritários", "ver prioridades do e-mail"],
        "enviar_email": ["enviar email", "enviar e-mail", "mandar mensagem", "mandar e-mail"],
        "meu_email": ["meu e-mail", "definir e-mail", "configurar email de envio"],

        "relatorio_diario": ["relatório diário", "status do dia", "me dá o resumo de hoje"],
        "relatorio_semanal": ["relatório semanal", "resumo da semana", "status semanal"],
        "enviar_relatorio_email": ["enviar relatório por e-mail", "mandar relatório", "relatório no e-mail"],

        "definir_tipo_negocio": ["definir tipo de negócio", "meu tipo de empresa", "negócio"],
        "definir_estilo": ["definir estilo", "estilo de comunicação", "meu estilo"],
        "definir_nome_negocio": ["nome do negócio", "nome da empresa", "nome do meu negócio"],

        "organizar_semana": [
            "planejar minha semana", "organizar minha semana", "como vai ser minha semana",
            "me ajuda com os compromissos da semana", "estrutura minha semana", "meu planejamento da semana"
        ],


        "criar_followup": [
            "fazer follow-up com", "registrar follow-up com",
            "marcar follow-up com", "agendar follow-up com",
            "adicionar follow-up com", "novo follow-up com",
            "follow-up com", "follow up com"
        ],

        "concluir_followup": [
            "já fiz o follow-up com", "pode apagar o follow-up de",
            "concluir o follow-up com", "já falei com",
            "já entrei em contato com", "remover o follow-up do",
            "apagar o follow-up de", "deletar o da loja",
            "concluir follow-up com", "já fiz o follow up com",
            "já falei com o", "falei com", "concluí o follow-up com"
        ],

        "meusfollowups": [
            "meus follow-ups", "ver follow-ups", "listar follow-ups",
            "mostrar meus follow-ups", "quais são meus follow-ups",
            "mostrar follow-up", "quero ver os follow-ups"
        ],

        "configurar_avisos": [
            "me avise às", "avisos às", "avisar nos horários",
            "quero lembretes em", "lembretes às", "configurar avisos",
            "horários de lembrete", "avisar em", "configurar lembretes para"
        ],
    }

    for intencao, padroes in comandos.items():
        for padrao in padroes:
            if padrao in texto:
                return intencao

    return None
