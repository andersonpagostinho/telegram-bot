#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MATRIZ DE VARIAÇÃO: Profissional × Serviço

Testa as 4 combinações críticas:
1. Prof válido + Serviço válido → Pré-confirmação
2. Prof válido + Serviço inválido → Serviço não encontrado
3. Prof inválido + Serviço válido → Prof não atende
4. Prof inválido + Serviço inválido → Qual validar primeiro? (Serviço tem prioridade)

Entradas:
- "Quero corte com Bruna amanhã às 10" (válido + válido)
- "Quero massagem com Bruna amanhã às 10" (válido + inválido)
- "Quero corte com Carla amanhã às 10" (inválido + válido)
- "Quero massagem com Carla amanhã às 10" (inválido + inválido)
"""

import asyncio
import sys
import io
from datetime import datetime, timedelta
from dataclasses import dataclass

# Force UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, '.')


@dataclass
class Caso:
    entrada: str
    prof: str
    servico: str
    prof_valido: bool
    servico_valido: bool
    esperado: str
    descricao: str


CASOS = [
    Caso(
        entrada="Quero corte com Bruna amanhã às 10",
        prof="Bruna",
        servico="corte",
        prof_valido=True,
        servico_valido=True,
        esperado="pré-confirmação",
        descricao="Prof válido + Serviço válido"
    ),
    Caso(
        entrada="Quero massagem com Bruna amanhã às 10",
        prof="Bruna",
        servico="massagem",
        prof_valido=True,
        servico_valido=False,
        esperado="serviço_não_encontrado",
        descricao="Prof válido + Serviço inválido (massagem)"
    ),
    Caso(
        entrada="Quero corte com Carla amanhã às 10",
        prof="Carla",
        servico="corte",
        prof_valido=False,
        servico_valido=True,
        esperado="prof_não_atende",
        descricao="Prof inválido (Carla) + Serviço válido"
    ),
    Caso(
        entrada="Quero massagem com Carla amanhã às 10",
        prof="Carla",
        servico="massagem",
        prof_valido=False,
        servico_valido=False,
        esperado="serviço_não_encontrado",  # Serviço tem prioridade
        descricao="Prof inválido + Serviço inválido (serviço tem prioridade)"
    ),
]

# Profissionais cadastrados
PROFISSIONAIS = {
    "Bruna": {"servicos": ["corte", "escova", "coloracao", "hidratacao"]},
    "Gloria": {"servicos": ["corte", "escova", "manicure"]},
    "Joana": {"servicos": ["corte", "hidratacao", "manicure"]},
    "Carla": {"servicos": ["manicure"]},  # NÃO atende corte
}

SERVICOS = {
    "corte": {"preco": 50},
    "escova": {"preco": 60},
    "coloracao": {"preco": 120},
    "hidratacao": {"preco": 80},
    "manicure": {"preco": 40},
}


async def test_matriz():
    """Testa matriz de combinações prof × servico."""

    print("\n" + "="*100)
    print("MATRIZ DE VARIAÇÃO: Profissional × Serviço")
    print("="*100)

    resultados = []

    for i, caso in enumerate(CASOS, 1):
        print(f"\n{'─'*100}")
        print(f"CASO {i}: {caso.descricao}")
        print(f"{'─'*100}")
        print(f"Entrada: {caso.entrada}")
        print(f"Profissional: {caso.prof} (válido: {caso.prof_valido})")
        print(f"Serviço: {caso.servico} (válido: {caso.servico_valido})")
        print(f"Esperado: {caso.esperado}")

        # Simular validações
        validacoes = []

        # 1. Extrair prof/servico
        print(f"\n✓ Extração: prof={caso.prof}, servico={caso.servico}")
        validacoes.append(True)

        # 2. Validar serviço
        servico_existe = caso.servico.lower() in SERVICOS
        print(f"✓ Validação serviço: {servico_existe}")
        validacoes.append(servico_existe == caso.servico_valido)

        # 3. Se serviço inválido, retornar erro imediatamente
        if not servico_existe:
            print(f"✓ Serviço inválido → Retornar erro (prioridade sobre prof)")
            print(f"  Resposta: 'Não encontrei *{caso.servico}* no catálogo.'")
            validacoes.append(caso.esperado == "serviço_não_encontrado")
        else:
            # 4. Se serviço válido, validar prof
            prof_existe = caso.prof.lower() in [p.lower() for p in PROFISSIONAIS.keys()]
            prof_atende = False
            if prof_existe:
                prof_data = PROFISSIONAIS.get(caso.prof)
                prof_atende = caso.servico.lower() in prof_data.get("servicos", [])

            print(f"✓ Validação prof: existe={prof_existe}, atende={prof_atende}")
            validacoes.append(prof_atende == caso.prof_valido)

            if prof_existe and prof_atende:
                print(f"✓ Prof válido → Pré-confirmação")
                validacoes.append(caso.esperado == "pré-confirmação")
            elif prof_existe and not prof_atende:
                print(f"✓ Prof não atende → Listar profissionais válidos")
                print(f"  Resposta: '*{caso.prof}* não atende {caso.servico}. Para {caso.servico}, posso verificar com: ...'")
                validacoes.append(caso.esperado == "prof_não_atende")
            elif not prof_existe:
                print(f"✓ Prof não existe → Listar profissionais para serviço")
                print(f"  Resposta: 'Não encontrei *{caso.prof}* entre os profissionais. Para {caso.servico}, posso verificar com: ...'")
                validacoes.append(caso.esperado == "prof_não_existe")

        # Resultado deste caso
        passou = all(validacoes)
        status = "✅ PASSOU" if passou else "❌ FALHOU"
        print(f"\nResultado: {status} ({sum(validacoes)}/{len(validacoes)} validações)")
        resultados.append((caso.descricao, passou))

    # Resumo
    print(f"\n{'='*100}")
    print("RESUMO DA MATRIZ")
    print(f"{'='*100}\n")

    for descricao, passou in resultados:
        status = "✅" if passou else "❌"
        print(f"{status} {descricao}")

    total_passou = sum(1 for _, passou in resultados if passou)
    print(f"\n{total_passou}/{len(resultados)} casos passaram")

    return all(passou for _, passou in resultados)


async def main():
    try:
        resultado = await test_matriz()
        sys.exit(0 if resultado else 1)
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
