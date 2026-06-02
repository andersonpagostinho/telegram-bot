#!/bin/bash
# EXEMPLO DE USO DO ORQUESTRADOR

echo "======================================================================"
echo "EXEMPLOS DE USO DO ORQUESTRADOR"
echo "======================================================================"
echo ""

echo "1. INVESTIGAR BUG DE CONSULTA PURA:"
echo ""
echo "   python orquestrador.py \"investigue por que consulta pura vira agendamento\""
echo ""

echo "2. REVISAR BLOCO AUTO-PROFISSIONAL:"
echo ""
echo "   python orquestrador.py \"revise bloco auto-profissional pos-extracao\""
echo ""

echo "3. AUDITAR SLOTS:"
echo ""
echo "   python orquestrador.py \"audit slots e extrair_slots_e_mesclar\""
echo ""

echo "4. INVESTIGAR CONTEXTO:"
echo ""
echo "   python orquestrador.py \"investigue contexto_temporario e risco de RMW\""
echo ""

echo "5. REVISAR ROUTER:"
echo ""
echo "   python orquestrador.py \"revise router principal_router\""
echo ""

echo "======================================================================"
echo "PRIMEIRO USO - SETUP:"
echo "======================================================================"
echo ""

echo "1. Instalar dependencias:"
echo "   pip install -r requirements_orquestrador.txt"
echo ""

echo "2. Configurar .env:"
echo "   - Adicionar: ANTHROPIC_API_KEY=sk-ant-..."
echo "   - Obter em: https://console.anthropic.com/keys"
echo ""

echo "3. Executar exemplo:"
echo "   python orquestrador.py \"teste rápido\""
echo ""

echo "4. Ver resultado:"
echo "   cat logs/orquestrador_*.json | python -m json.tool"
echo ""

echo "======================================================================"
echo "DOCUMENTAÇÃO:"
echo "======================================================================"
echo ""
echo "   - ORQUESTRADOR_README.md   (completo)"
echo "   - ORQUESTRADOR_SETUP.md    (setup rápido)"
echo ""
