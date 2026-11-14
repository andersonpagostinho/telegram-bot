"""
P0 FASE 6.3 — Varredura Determinística de Disponibilidade

Percorre janela temporal e valida horários com motor determinístico.
"""

from datetime import datetime, timedelta
from services.event_service_async import verificar_conflito_e_sugestoes_profissional
from services.duracao_service import obter_duracao_por_profissional_bridge
from services.firebase_service_async import buscar_subcolecao
from services.agenda_service import obter_janela_funcionamento
from unidecode import unidecode


async def varrer_disponibilidade_multisservico(
    tenant_id: str,
    actor_id: str,
    data: str,
    intervalo_inicio: int,
    intervalo_fim: int,
    profissional_mencionada: str,
    servicos_multiplos: list[str],
    duracao_total: int = 60,
    max_resultados: int = 3,
    passo_minutos: int = 20,
    dono_id: str | None = None
) -> dict:
    """
    Percorre janela temporal e encontra horários disponíveis.

    Args:
        tenant_id: ID do cliente/tenant
        actor_id: ID canônico do usuário
        data: Data em formato "YYYY-MM-DD"
        intervalo_inicio: Hora inicial (ex: 14)
        intervalo_fim: Hora final (ex: 17)
        profissional_mencionada: Nome do profissional preferido
        servicos_multiplos: Lista de serviços
        duracao_total: Duração em minutos
        max_resultados: Máximo de horários a retornar
        passo_minutos: Intervalo entre candidatos

    Returns:
        {
            "profissional": "Bruna",
            "horarios_disponiveis": [
                {"inicio": "14:00", "fim": "15:00"},
                {"inicio": "15:30", "fim": "16:30"},
            ],
            "alternativas": [...],
            "nenhuma_disponibilidade": False
        }
    """

    from datetime import date as dateclass

    print(f"\n[VARREDURA] Iniciando busca: {profissional_mencionada}, janela {intervalo_inicio}-{intervalo_fim}h", flush=True)

    # Validar que profissional executa ambos os serviços
    profissionais_db = await buscar_subcolecao(f"Clientes/{tenant_id}/Profissionais") or {}

    # Buscar case-insensitive
    prof_data = None
    for nome_db, dados in profissionais_db.items():
        if unidecode(nome_db.lower().strip()) == unidecode(profissional_mencionada.lower().strip()):
            prof_data = dados
            break

    if not prof_data:
        prof_data = {}

    servicos_prof = [unidecode(s.lower().strip()) for s in (prof_data.get("servicos") or [])]

    # Normalizar serviços para comparação
    servicos_norm = [unidecode(s.lower().strip()) for s in servicos_multiplos]

    faltam_servicos = [s for s in servicos_norm if s not in servicos_prof]
    if faltam_servicos:
        print(f"[VARREDURA] {profissional_mencionada} não executa: {faltam_servicos}", flush=True)
        return {
            "profissional": profissional_mencionada,
            "horarios_disponiveis": [],
            "alternativas": [],
            "nenhuma_disponibilidade": True,
            "motivo": f"Profissional não executa todos os serviços"
        }

    # Iterar horários dentro da janela
    horarios_disponiveis = []
    data_obj = datetime.fromisoformat(data).date()

    # FASE 1: Validar se a data está aberta e respeitar horário de funcionamento
    janela_funcionamento = await obter_janela_funcionamento(
        user_id=actor_id,
        data_str=data,
        profissional=profissional_mencionada,
        dono_id=dono_id or tenant_id
    )

    if not janela_funcionamento.get("aberto"):
        print(f"[VARREDURA] Data {data} está fechada (origem: {janela_funcionamento.get('origem')})", flush=True)
        return {
            "profissional": profissional_mencionada,
            "horarios_disponiveis": [],
            "alternativas": [],
            "nenhuma_disponibilidade": True,
            "motivo": f"Profissional fechado em {data}"
        }

    # Extrair limite de horário
    limite_inicio_str = janela_funcionamento.get("inicio")
    limite_fim_str = janela_funcionamento.get("fim")

    # Converter limites para hora/minuto para comparação
    limite_inicio_dt = None
    limite_fim_dt = None
    if limite_inicio_str:
        try:
            h_i, m_i = map(int, limite_inicio_str.split(":"))
            limite_inicio_dt = datetime.fromisoformat(f"{data}T{limite_inicio_str}")
        except:
            pass
    if limite_fim_str:
        try:
            h_f, m_f = map(int, limite_fim_str.split(":"))
            limite_fim_dt = datetime.fromisoformat(f"{data}T{limite_fim_str}")
        except:
            pass

    # VALIDAÇÃO: Intervalo deve ser válido antes de executar range()
    # Usar type() is int em vez de isinstance() para rejeitar bool (que é subclasse de int)
    if type(intervalo_inicio) is not int or type(intervalo_fim) is not int:
        print(f"[VARREDURA] Intervalo inválido: tipos {type(intervalo_inicio).__name__}, {type(intervalo_fim).__name__}", flush=True)
        return {
            "profissional": profissional_mencionada,
            "horarios_disponiveis": [],
            "alternativas": [],
            "nenhuma_disponibilidade": True,
            "motivo": f"Intervalo inválido: tipos incorretos"
        }

    # VALIDAÇÃO: Fim deve ser maior que início
    if intervalo_fim <= intervalo_inicio:
        print(f"[VARREDURA] Intervalo ilógico: inicio={intervalo_inicio}, fim={intervalo_fim}", flush=True)
        return {
            "profissional": profissional_mencionada,
            "horarios_disponiveis": [],
            "alternativas": [],
            "nenhuma_disponibilidade": True,
            "motivo": f"Intervalo inválido: fim ({intervalo_fim}) <= inicio ({intervalo_inicio})"
        }

    for hora in range(intervalo_inicio, intervalo_fim):
        for minuto in [0, 20, 40]:  # Passo de 20 minutos
            hora_candidata = f"{hora:02d}:{minuto:02d}"
            inicio_candidato = datetime.fromisoformat(f"{data}T{hora_candidata}")
            fim_candidato = inicio_candidato + timedelta(minutes=duracao_total)

            # Verificar se término não ultrapassa limite da janela solicitada
            if fim_candidato.hour > intervalo_fim or (fim_candidato.hour == intervalo_fim and fim_candidato.minute > 0):
                print(f"[VARREDURA] {hora_candidata} + {duracao_total}min = {fim_candidato.strftime('%H:%M')} > {intervalo_fim}:00 ❌", flush=True)
                continue

            # FASE 1: Validar contra horário de funcionamento real
            # Início deve estar dentro do expediente
            if limite_inicio_dt and inicio_candidato < limite_inicio_dt:
                print(f"[VARREDURA] {hora_candidata} é antes da abertura ({limite_inicio_str}) ❌", flush=True)
                continue

            # Fim deve estar dentro do expediente
            if limite_fim_dt and fim_candidato > limite_fim_dt:
                print(f"[VARREDURA] {hora_candidata} + {duracao_total}min = {fim_candidato.strftime('%H:%M')} ultrapassa fechamento ({limite_fim_str}) ❌", flush=True)
                continue

            print(f"[VARREDURA] Testando {hora_candidata}...", flush=True)

            # Chamar motor para validar este horário
            resultado_motor = await verificar_conflito_e_sugestoes_profissional(
                user_id=actor_id,
                data=data,
                hora_inicio=hora_candidata,
                duracao_min=duracao_total,
                profissional=profissional_mencionada,
                servico=None,
                tenant_id=tenant_id,
                servicos_bloco=servicos_multiplos
            )

            if not resultado_motor.get("conflito"):
                horario_info = {
                    "inicio": hora_candidata,
                    "fim": fim_candidato.strftime("%H:%M")
                }
                horarios_disponiveis.append(horario_info)
                print(f"[VARREDURA] ✅ {hora_candidata} disponível", flush=True)

                if len(horarios_disponiveis) >= max_resultados:
                    print(f"[VARREDURA] Máximo de resultados atingido", flush=True)
                    break

        if len(horarios_disponiveis) >= max_resultados:
            break

    # Se encontrou disponibilidade, retornar
    if horarios_disponiveis:
        return {
            "profissional": profissional_mencionada,
            "horarios_disponiveis": horarios_disponiveis,
            "alternativas": [],
            "nenhuma_disponibilidade": False
        }

    print(f"[VARREDURA] Nenhum horário disponível para {profissional_mencionada}", flush=True)

    # Se não encontrou, buscar alternativas compatíveis
    alternativas = await buscar_alternativas_multisservico(
        tenant_id=tenant_id,
        actor_id=actor_id,
        data=data,
        intervalo_inicio=intervalo_inicio,
        intervalo_fim=intervalo_fim,
        servicos_multiplos=servicos_multiplos,
        duracao_total=duracao_total,
        profissional_a_excluir=profissional_mencionada
    )

    return {
        "profissional": profissional_mencionada,
        "horarios_disponiveis": [],
        "alternativas": alternativas,
        "nenhuma_disponibilidade": True,
        "motivo": "Profissional indisponível na janela"
    }


async def buscar_alternativas_multisservico(
    tenant_id: str,
    actor_id: str,
    data: str,
    intervalo_inicio: int,
    intervalo_fim: int,
    servicos_multiplos: list[str],
    duracao_total: int = 60,
    profissional_a_excluir: str = None,
    max_alternativas: int = 3
) -> list[dict]:
    """
    Busca profissionais alternativos que executam TODOS os serviços.
    """

    from datetime import date as dateclass

    print(f"\n[ALTERNATIVAS] Buscando profissionais compatíveis com {servicos_multiplos}", flush=True)

    profissionais_db = await buscar_subcolecao(f"Clientes/{tenant_id}/Profissionais") or {}
    servicos_norm = [unidecode(s.lower().strip()) for s in servicos_multiplos]

    alternativas = []

    for prof_nome, prof_data in profissionais_db.items():
        # Comparação case-insensitive
        if unidecode(prof_nome.lower().strip()) == unidecode((profissional_a_excluir or "").lower().strip()):
            continue

        # Verificar se executa todos os serviços
        servicos_prof = [unidecode(s.lower().strip()) for s in (prof_data.get("servicos") or [])]

        if not all(s in servicos_prof for s in servicos_norm):
            print(f"[ALTERNATIVAS] {prof_nome} não executa todos os serviços", flush=True)
            continue

        print(f"[ALTERNATIVAS] {prof_nome} é compatível, buscando horários...", flush=True)

        # Buscar primeiro horário disponível para esta alternativa
        resultado = await varrer_disponibilidade_multisservico(
            tenant_id=tenant_id,
            actor_id=actor_id,
            data=data,
            intervalo_inicio=intervalo_inicio,
            intervalo_fim=intervalo_fim,
            profissional_mencionada=prof_nome,
            servicos_multiplos=servicos_multiplos,
            duracao_total=duracao_total,
            max_resultados=1,  # Apenas primeiro horário
            dono_id=tenant_id
        )

        if resultado.get("horarios_disponiveis"):
            primeiro_horario = resultado["horarios_disponiveis"][0]
            alternativas.append({
                "profissional": prof_nome,
                "horarios": [primeiro_horario]
            })

            if len(alternativas) >= max_alternativas:
                break

    print(f"[ALTERNATIVAS] Total encontrado: {len(alternativas)}", flush=True)
    return alternativas
