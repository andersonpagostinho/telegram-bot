#!/usr/bin/env python
import asyncio
import sys
from services.gpt_service import processar_com_gpt_com_acao
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA

async def test_consulta_pura():
    print("\n" + "="*70)
    print("🧪 TESTE: Consulta Pura - 'vocês fazem escova?'")
    print("="*70)

    texto = 'vocês fazem escova?'

    # Simular contexto com objetivo_conversacional de consulta pura
    contexto = {
        'objetivo_conversacional': 'consultar_disponibilidade_por_servico',
        'intencao_conversacional': 'consulta_disponibilidade_servico',
        'profissionais': [
            {
                'nome': 'Maria',
                'servicos': ['escova', 'corte', 'pintura']
            },
            {
                'nome': 'Ana',
                'servicos': ['escova', 'hidratação']
            }
        ]
    }

    print(f"\n📥 Entrada:")
    print(f"  Texto: '{texto}'")
    print(f"  objetivo_conversacional: {contexto['objetivo_conversacional']}")
    print(f"  intencao_conversacional: {contexto['intencao_conversacional']}")

    resultado = await processar_com_gpt_com_acao(
        texto_usuario=texto,
        contexto=contexto,
        instrucao=INSTRUCAO_SECRETARIA,
        user_id='teste_usuario_consulta_123'
    )

    print(f"\n📤 Resultado:")
    if resultado:
        print(f"  resposta: {str(resultado.get('resposta'))[:150]}...")
        print(f"  acao: {resultado.get('acao')}")
        print(f"  dados: {resultado.get('dados')}")
    else:
        print(f"  (None)")

    print("\n✅ Teste concluído\n")

if __name__ == "__main__":
    asyncio.run(test_consulta_pura())
