#!/usr/bin/env python3
import asyncio
from services.multisservico_service import extrair_intervalo_horario, enriquecer_contexto_consulta
from services.duracao_service import obter_duracao_por_profissional_bridge

async def audit_cenario_original():
    print("="*80)
    print("[AUDITORIA E2E] Cenario Original - 14h-17h, Manicure + Pedicure, Bruna")
    print("="*80)
    
    # PASSO 1: Extracao intervalo
    msg = "Consigo chegar a partir das 14h, mas tenho um compromisso no final do dia e preciso terminar os dois servicos ate, no maximo, 17h."
    print(f"\n[1] Mensagem: {msg[:60]}...")
    inicio, fim = extrair_intervalo_horario(msg)
    print(f"    Intervalo extraido: ({inicio}, {fim})")
    assert inicio == 14, f"Esperado 14, obteve {inicio}"
    assert fim == 17, f"Esperado 17, obteve {fim}"
    print("    ✅ Parser OK")
    
    # PASSO 2: Enriquecimento contexto
    print(f"\n[2] Enriquecimento contexto:")
    contexto = {
        'profissional_mencionada': 'Bruna',
        'servicos_multiplos': ['manicure', 'pedicure']
    }
    contexto = enriquecer_contexto_consulta(contexto, msg)
    print(f"    intervalo_inicio: {contexto.get('intervalo_inicio')}")
    print(f"    intervalo_fim: {contexto.get('intervalo_fim')}")
    assert contexto.get('intervalo_inicio') == 14
    assert contexto.get('intervalo_fim') == 17
    print("    ✅ Contexto OK")
    
    # PASSO 3: Validacao intervalo
    print(f"\n[3] Validacao intervalo (varredura):")
    intervalo_inicio = contexto.get('intervalo_inicio')
    intervalo_fim = contexto.get('intervalo_fim')
    
    tipos_ok = isinstance(intervalo_inicio, int) and isinstance(intervalo_fim, int)
    print(f"    Tipos corretos? {tipos_ok}")
    
    range_ok = intervalo_fim > intervalo_inicio
    print(f"    Fim > Inicio? {intervalo_fim} > {intervalo_inicio} = {range_ok}")
    
    if tipos_ok and range_ok:
        horas = list(range(intervalo_inicio, intervalo_fim))
        print(f"    Range seguro: {horas}")
        print("    ✅ Validacao OK")
    
    print("\n✅ CENARIO ORIGINAL RASTREADO COM SUCESSO")
    print("="*80)

asyncio.run(audit_cenario_original())
