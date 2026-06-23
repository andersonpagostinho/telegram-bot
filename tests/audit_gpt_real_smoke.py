#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPT-TEST-01: Smoke Test GPT Real

Objetivo:
- Validar se OPENAI_API_KEY está configurada
- Testar conexão com OpenAI API
- Fazer chamada mínima e barata
- Registrar sucesso/falha
- Não consumir muitos tokens

Execução:
python tests/audit_gpt_real_smoke.py

Saída esperada:
- JSON com status de conectividade
- Informações de modelo usado
- Sem exposição de segredos
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

def validar_env_var():
    """Validar OPENAI_API_KEY sem expor segredo"""

    api_key = os.getenv("OPENAI_API_KEY")

    resultado = {
        "presente": api_key is not None and len(api_key) > 0,
        "tamanho_chars": len(api_key) if api_key else 0,
        "prefixo": None,
        "origem_provavel": None
    }

    if resultado["presente"]:
        # Extrair prefixo seguro (primeiros 10 chars + "...")
        if len(api_key) > 10:
            resultado["prefixo"] = api_key[:10] + "..."
        else:
            resultado["prefixo"] = "sk-[presente]"

        # Tentar descobrir origem
        if api_key.startswith("sk-proj-"):
            resultado["origem_provavel"] = "API Key v2 (sk-proj-...)"
        elif api_key.startswith("sk-"):
            resultado["origem_provavel"] = "API Key v1 (sk-...)"
        else:
            resultado["origem_provavel"] = "desconhecida"

    return resultado

async def testar_conexao_gpt():
    """Fazer chamada mínima e barata ao GPT"""

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Chamada mínima e barata (modelo barato, mensagem curta)
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",  # Modelo mais barato
            messages=[
                {
                    "role": "user",
                    "content": "respond with just: ok"
                }
            ],
            max_tokens=10,  # Mínimo possível
            temperature=0
        )

        return {
            "sucesso": True,
            "modelo": response.model,
            "resposta": response.choices[0].message.content if response.choices else None,
            "tokens_usados": {
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
                "total": response.usage.total_tokens
            },
            "custo_estimado_usd": round(
                (response.usage.prompt_tokens * 0.0005 + response.usage.completion_tokens * 0.0015) / 1000,
                6
            )
        }

    except Exception as e:
        return {
            "sucesso": False,
            "erro": str(e),
            "tipo_erro": type(e).__name__
        }

async def main():
    """Executar smoke test"""

    print("\n" + "="*80)
    print("GPT-TEST-01: SMOKE TEST GPT REAL")
    print("="*80 + "\n")

    resultado = {
        "timestamp": datetime.now().isoformat(),
        "teste": "smoke_gpt_real",
        "ambiente": "local",
        "etapas": {}
    }

    # ETAPA 1: Validar env var
    print("[1/2] VALIDANDO OPENAI_API_KEY...")
    env_status = validar_env_var()
    resultado["etapas"]["env_var"] = env_status

    if env_status["presente"]:
        print(f"  [OK] OPENAI_API_KEY presente")
        print(f"  - Prefixo: {env_status['prefixo']}")
        print(f"  - Tamanho: {env_status['tamanho_chars']} chars")
        print(f"  - Origem: {env_status['origem_provavel']}\n")
    else:
        print(f"  [ERRO] OPENAI_API_KEY NAO CONFIGURADA")
        print(f"  - Bloqueio: Não é possível continuar\n")

        resultado["status"] = "BLOQUEADO"
        resultado["motivo"] = "OPENAI_API_KEY não está configurada"

        # Salvar resultado
        output_file = "resultado_audit_gpt_real_smoke.json"
        with open(output_file, 'w') as f:
            json.dump(resultado, f, indent=2)

        print(f"Resultado salvo em: {output_file}\n")
        return False

    # ETAPA 2: Testar conexão
    print("[2/2] TESTANDO CONEXÃO COM OPENAI...")
    gpt_status = await testar_conexao_gpt()
    resultado["etapas"]["conexao_gpt"] = gpt_status

    if gpt_status["sucesso"]:
        print(f"  [OK] CONEXAO ESTABELECIDA")
        print(f"  - Modelo: {gpt_status['modelo']}")
        print(f"  - Resposta: {gpt_status['resposta']}")
        print(f"  - Tokens usados: {gpt_status['tokens_usados']['total']}")
        print(f"  - Custo estimado: ${gpt_status['custo_estimado_usd']}\n")

        resultado["status"] = "SUCESSO"
        resultado["motivo"] = "Conexao com OpenAI estabelecida com sucesso"
    else:
        print(f"  [ERRO] CONEXAO FALHOU")
        print(f"  - Erro: {gpt_status['erro']}")
        print(f"  - Tipo: {gpt_status['tipo_erro']}\n")

        resultado["status"] = "FALHA"
        resultado["motivo"] = f"Erro ao conectar: {gpt_status['tipo_erro']}"

    # SALVAR RESULTADO
    print("="*80)
    print("SALVANDO RESULTADO")
    print("="*80)

    output_file = "resultado_audit_gpt_real_smoke.json"
    with open(output_file, 'w') as f:
        json.dump(resultado, f, indent=2)

    print(f"[OK] Resultado salvo em: {output_file}\n")

    # PRÓXIMAS ETAPAS
    if resultado["status"] == "SUCESSO":
        print("="*80)
        print("PRÓXIMAS ETAPAS")
        print("="*80)
        print("\nGPT real está operacional. Pode executar auditorias:")
        print("  python tests/audit_cenario_05_gpt_real.py\n")
        return True
    else:
        print("Smoke test falhou. Não é possível continuar com auditorias GPT real.\n")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
