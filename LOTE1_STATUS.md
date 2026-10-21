# LOTE 1 — STATUS DE MIGRAÇÃO

**Data Início:** 2026-10-21  
**Status Atual:** ⏸️ BLOQUEADO — Ajustes necessários

## Testes Criados (5/5)

✅ Arquivos criados:
1. `test_p0_lote1_1_classificacao_e2e_firebase.py` — 3 testes de classificação
2. `test_p0_lote1_2_cancelar_evento_e2e_firebase.py` — 2 testes de cancelamento
3. `test_p0_lote1_3_confirmacao_cancelamento_e2e_firebase.py` — 2 testes de confirmação
4. `test_p0_lote1_4_data_sem_hora_e2e_firebase.py` — 2 testes de extração data/hora
5. `test_p0_lote1_5_extracao_termo_cancelamento_e2e_firebase.py` — 2 testes de termos

**Total de testes:** 11 testes E2E criados

## Motivo da Falha

Erro: `phone_number_id é obrigatório para WhatsApp`

Os testes precisam passar parâmetros WhatsApp reais ao `roteador_principal()`:
- `phone_number_id` (ID do WhatsApp endpoint)
- `wa_id` ou contexto WhatsApp apropriado
- Possível: Update na forma como chamar roteador_principal

## Próximo Passo

**OPÇÃO 1:** Analisar teste E2E existente (PASS) para ver assinatura correta
**OPÇÃO 2:** Ajustar todos os 11 testes com os parâmetros WhatsApp corretos
**OPÇÃO 3:** Contactar para receber assinatura correta de roteador_principal

## Referência de Erro

```
[P0.1] Erro ao criar IdentidadeContexto: phone_number_id é obrigatório para WhatsApp
[ACTOR_CANONICO] WhatsApp 5511993682094 não tem ator em 7394370553
```

Indica que é necessário simular envio WhatsApp completo, não apenas user_id + tenant_id.

## Ação Recomendada

1. Ler um teste E2E PASS existente
2. Verificar como chama roteador_principal com WhatsApp completo
3. Atualizar os 11 testes com a assinatura correta
4. Re-rodar pytest

