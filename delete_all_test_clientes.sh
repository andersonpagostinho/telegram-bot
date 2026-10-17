#!/bin/bash
# Script para deletar clientes de teste via Firebase CLI
# Preserva: 5511991382080, 7371670478, 7394370553

PROJECT="projeto-agente-inteligente"

# Clientes a MANTER
KEEP=("5511991382080" "7371670478" "7394370553")

echo "========================================================================"
echo "DELETANDO CLIENTES DE TESTE VIA FIREBASE CLI"
echo "========================================================================"
echo ""
echo "Clientes a manter:"
for client in "${KEEP[@]}"; do
    echo "  ✓ $client"
done
echo ""

# Função para verificar se cliente deve ser mantido
should_keep() {
    local client=$1
    for keep in "${KEEP[@]}"; do
        if [[ "$client" == "$keep" ]]; then
            return 0
        fi
    done
    return 1
}

# Lista de clientes de teste (extraída do Firebase)
CLIENTES_TESTE=(
    "c423_test_e5681e90"
    "c423_test_f6c0d0a3"
    "c42_idempo_test"
    "c446_fase2b_tenant2_51db5e"
    "c446_fase2b_tenant2_b612eb"
    "c446_fase2b_tenant2_f24f9e"
    "c446_fase2b_tenant_026df1"
    "c446_fase2b_tenant_0c51af"
)

echo "Deletando ${#CLIENTES_TESTE[@]} clientes de teste..."
echo ""

deleted=0
failed=0

for cliente in "${CLIENTES_TESTE[@]}"; do
    if should_keep "$cliente"; then
        echo "  ⊘ $cliente (mantido)"
    else
        echo -n "  Deletando $cliente... "
        if firebase firestore:delete --project="$PROJECT" "Clientes/$cliente" --recursive --yes > /dev/null 2>&1; then
            echo "✓"
            ((deleted++))
        else
            echo "✗"
            ((failed++))
        fi
    fi
done

echo ""
echo "========================================================================"
echo "RESUMO"
echo "========================================================================"
echo "Deletados: $deleted"
echo "Falhados: $failed"
echo "========================================================================"
