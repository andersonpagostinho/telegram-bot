#!/bin/bash
# Script para deletar clientes de teste preservando os 3 reais

PROJECT="projeto-agente-inteligente"

# Clientes a MANTER
KEEP=("7371670478" "7394370553" "5511991382080" "fernanda" "whatsapp:55119999006" "default")

# Padrões de DELETAR
DELETE_PATTERNS=(
    "dono_tenant_lote3_"
    "user_tenant_lote3_"
    "usuario_"
    "bateria_p0_user_teste_"
    "cliente_"
    "diagnostico_"
    "t1_"
    "t2_"
    "t3_"
    "t17_"
)

echo "Deletando clientes de teste..."
echo "Preservando: ${KEEP[@]}"
echo ""

# Para cada padrão, deletar todos que correspondem
for pattern in "${DELETE_PATTERNS[@]}"; do
    echo "Padrão: $pattern*"
    # Aqui seria necessário listar e deletar cada um
    # Mas Firebase CLI não suporta wildcards diretos
done

echo ""
echo "Nota: Firebase CLI não suporta wildcards em paths."
echo "Use o script Python ou delete manualmente."
