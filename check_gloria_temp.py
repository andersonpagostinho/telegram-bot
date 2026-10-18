import asyncio
import os
import sys

# Carregar ambiente
os.environ.setdefault('GOOGLE_APPLICATION_CREDENTIALS', './firebase-key.json')

async def main():
    from utils.firestore_utils import buscar_dado_em_path
    
    tenant_id = '7394370553'
    data_target = '2026-10-19'
    
    print('[FIREBASE VERIFICATION]')
    print(f'Checking Glory events on {data_target} 09:00-10:00')
    print()
    
    # Get all events
    eventos = await buscar_dado_em_path(f'Clientes/{tenant_id}/Eventos') or {}
    
    print(f'Total eventos: {len(eventos)}')
    
    gloria_eventos = []
    for event_id, evento in eventos.items():
        prof = (evento.get('profissional') or '').strip().lower()
        data = evento.get('data', '')
        
        if prof == 'gloria' and data == data_target:
            gloria_eventos.append({
                'event_id': event_id,
                'hora_inicio': evento.get('hora_inicio'),
                'hora_fim': evento.get('hora_fim'),
                'servico': evento.get('descricao'),
                'cliente_id': evento.get('cliente_id'),
                'status': evento.get('status'),
                'confirmado': evento.get('confirmado')
            })
    
    print()
    if gloria_eventos:
        print(f'[CONFLICT FOUND] Glory HAS {len(gloria_eventos)} event(s):')
        for ev in gloria_eventos:
            print(f"  {ev['hora_inicio']}-{ev['hora_fim']}: {ev['servico']}")
            print(f"    Status: {ev['status']}, Confirmado: {ev['confirmado']}")
        
        # Check overlap
        for ev in gloria_eventos:
            if ev['hora_inicio'] < '10:00' and ev['hora_fim'] > '09:00':
                print(f"\n[CONCLUSION] Glory WAS OCCUPIED at 09:00-10:00")
                print(f"  Conflicting event: {ev['hora_inicio']}-{ev['hora_fim']}")
                return
        
        print(f"\n[CONCLUSION] Glory was FREE at 09:00-10:00 (no overlapping events)")
    else:
        print(f'[AVAILABLE] Glory has NO events on {data_target}')
        print('[CONCLUSION] Glory WAS AVAILABLE at 09:00-10:00')

asyncio.run(main())
