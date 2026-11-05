# P0.27.2 — AUDITORIA DA LIMPEZA DE LOCKS E ORIGEM DO FALSO CONFLITO

**Data**: 2026-11-05  
**Status**: ✅ **DIAGNÓSTICO COMPLETO (READ-ONLY)**  
**Severidade**: 🔴 **CRÍTICA** - Gap em limpeza de locks confirmados órfãos

---

## ETAPA 1 — RASTREAMENTO DO CONFLITO

### Fluxo Exato de Bruna 10:00 em 2026-11-06

```
1. Novo agendamento tenta 10:00
   ↓
2. P0.27-C gera event_id: "...bruna_2026-11-06_1000"
   ↓
3. criar_evento_com_lock() tenta adquirir 4 locks
   - bruna_20261106_100000
   - bruna_20261106_101000
   - bruna_20261106_102000
   - bruna_20261106_103000
   ↓
4. adquirir_locks_atomicamente() (linha 237):
   - Itera cada lock_key
   - transaction.get(lock_ref) no Firestore
   - Para bucket 100000: ENCONTRA documento
   - lock_doc.exists = True
   - RETORNA: {"ok": False, "motivo": "lock_já_existe"}
   ↓
5. criar_evento_com_lock() recebe ok=False (linha 610)
   ↓
6. Fallback idempotência (linha 619-620):
   - Busca evento: "...bruna_2026-11-06_1000"
   - Procura em Firestore
   - NÃO ENCONTRA (evento_id é "...10:00", não "..._1000")
   - evento_existente = None
   ↓
7. Evento não existe (linha 655):
   - RETORNA: "Slot ocupado" (lock_existente)
```

### Função Responsável

**[CONFIRMADO]** Linha 281-285:

```python
# Em adquirir_locks_atomicamente() → callback() → transaction
if hasattr(lock_doc, 'exists') and lock_doc.exists:
    return {
        "ok": False,
        "lock_key_conflito": lock_key,
        "motivo": f"lock_já_existe: {lock_key}"
    }
```

### Documento que Causa Bloqueio

**Firestore Document**: `Clientes/7394370553/AgendaLocks/bruna_20261106_100000`

```json
{
    "status": "confirmado",
    "evento_id": "whatsapp:5511991382080_bruna_2026-11-06_10:00",
    "timestamp_lock": "2026-10-20T22:00:00.119453",
    "expira_em": "2026-10-21T22:00:00.119453",
    "bucket": "100000",
    "profissional": "bruna"
}
```

**Análise**:
- Existe: ✓ YES
- Status: "confirmado" ✓ (não "reservado")
- Expirado: ✓ YES (21 out < 5 nov)
- Evento correspondente: ❌ NÃO EXISTE
- Classificação: **LOCK ÓRFÃO CONFIRMADO EXPIRADO**

---

## ETAPA 2 — AUDITORIA DE LIMPEZA

### Função: `limpar_locks_expirados()` (Linha 839)

**Implementação**:
```python
for lock_item in locks:
    lock_data = lock_item.get("data", lock_item)
    status = lock_data.get("status", "")
    
    # ❌ PROBLEMA: Só remove status em ["rejeitado", "erro_validacao", "erro_save"]
    if status not in ["rejeitado", "erro_validacao", "erro_save"]:
        continue  # ← PULA locks com status "confirmado"
    
    timestamp = datetime.fromisoformat(timestamp_str).timestamp()
    if timestamp < limite_tempo:
        # ❌ PROBLEMA: Delete está comentado
        # await deletar_dado_em_path(lock_path)
        removidos += 1
```

### Critério de Remoção

| Status | Removido | Motivo |
|--------|----------|--------|
| `reservado` | ❌ NÃO | Não está na lista permitida |
| `confirmado` | ❌ NÃO | **Não está na lista permitida** |
| `rejeitado` | ✓ SIM | Está na lista |
| `erro_validacao` | ✓ SIM | Está na lista |
| `erro_save` | ✓ SIM | Está na lista |

### Problema Crítico

**`limpar_locks_expirados()` NÃO remove locks confirmados!**

Locks de Bruna têm status="confirmado" → serão IGNORADOS.

Além disso: **delete está comentado na linha 878!**

---

## ETAPA 3 — VALIDAÇÃO DOS QUATRO LOCKS

### Bruna 10:00-10:40 em 2026-11-06

| Bucket | Documento | evento_id | Status | Expirado | Evento | Órfão? |
|--------|-----------|-----------|--------|----------|--------|--------|
| 100000 | EXISTS ✓ | `...10:00` | confirmado | SIM | ❌ | ✓ YES |
| 101000 | EXISTS ✓ | `...10:00` | confirmado | SIM | ❌ | ✓ YES |
| 102000 | EXISTS ✓ | `...10:00` | confirmado | SIM | ❌ | ✓ YES |
| 103000 | EXISTS ✓ | `...10:00` | confirmado | SIM | ❌ | ✓ YES |

**Conclusão**: Todos 4 são locks órfãos confirmados expirados.

---

## ETAPA 4 — REGRAS CONCEITUAIS

### Lock Lifecycle e Validade

| Cenário | Status | evento_id | Evento Existe | Expirado | Ação |
|---------|--------|-----------|---------------|----------|------|
| Novo agendamento | reservado | None | N/A | NÃO | Pode criar |
| Agendamento confirmado | confirmado | event_id | SIM | NÃO | Deve manter |
| Evento foi cancelado | confirmado | event_id | NÃO | N/A | **Deve liberar** |
| Erro em criação | rejeitado | None | N/A | SIM | Pode limpar |
| **BRUNA CASO** | confirmado | old_id | NÃO | SIM | **DEVE LIBERAR** |

### Regra de Ouro

```
Lock é VÁLIDO se:
  - status != "confirmado" → precisa validação de expiração
  - status == "confirmado" E evento_id exists(evento_id) → MANTÉM
  - status == "confirmado" E evento_id NOT exists(evento_id) → LIBERA (órfão)
  - timestamp < agora - 24h → LIBERA (expirado)
```

---

## ETAPA 5 — RELATÓRIO FINAL

### 1. Função Responsável pelo Bloqueio

**[CONFIRMADO]**
- **Arquivo**: `services/agenda_lock_service.py`
- **Função**: `adquirir_locks_atomicamente()`
- **Linhas**: 237-300 (callback linha 281-285)
- **Comportamento**: Verifica se lock já existe em Firestore; se existe, retorna erro imediatamente

### 2. Evidência de Bloqueio

Os 4 locks de Bruna 10:00-10:40 em 2026-11-06 causam bloqueio porque:
1. Existem em Firestore (documento criado)
2. Têm status = "confirmado"
3. Não correspondem a evento válido (evento_id malformado)
4. Não são removidos por nenhuma função de limpeza existente
5. Fazem `adquirir_locks_atomicamente()` falhar

### 3. Segurança de Limpeza

**[RISCO CRÍTICO]** `limpar_locks_expirados()` NÃO é seguro para locks confirmados:

- ❌ Ignora locks com status="confirmado"
- ❌ Delete está comentado (linha 878)
- ❌ Não valida se evento ainda existe
- ✓ Apenas remove locks com erro

### 4. Funções de Limpeza Existentes

| Função | Remove Quando | Status Alvo | Para Bruna? |
|--------|---------------|------------|------------|
| `limpar_locks_orfaos()` | evento_id vazio E expirado | sem evento_id | ❌ NÃO (tem evento_id) |
| `limpar_locks_com_erro()` | status em erro E expirado | rejeitado/erro | ❌ NÃO (status confirmado) |
| `liberar_locks_por_evento_id()` | evento cancelado | confirmado | ❌ NÃO (evento não existe) |

**GAP IDENTIFICADO**: Não existe função que libera locks confirmados órfãos expirados.

### 5. Correção Mínima Recomendada

**Opção A** (Segura - Recomendada):
Criar nova função `liberar_locks_orfaos_expirados()`:
```python
async def liberar_locks_orfaos_expirados(dono_id: str, horas_expiracao: int = 24):
    """Remove locks confirmados expirados sem evento correspondente."""
    locks = await buscar_subcolecao(f"Clientes/{dono_id}/AgendaLocks")
    removidos = 0
    
    for lock_item in locks:
        lock_data = lock_item.get("data", lock_item)
        
        # Verificar: confirmado + expirado + evento não existe
        if lock_data.get("status") == "confirmado":
            evento_id = lock_data.get("evento_id")
            if evento_id:  # Tem referência
                evento = await buscar_dado_em_path(
                    f"Clientes/{dono_id}/Eventos/{evento_id}"
                )
                if not evento:  # Mas evento não existe
                    # Verificar expiração
                    timestamp_str = lock_data.get("timestamp_lock")
                    timestamp = datetime.fromisoformat(timestamp_str).timestamp()
                    if timestamp < datetime.now().timestamp() - (horas_expiracao * 3600):
                        await deletar_dado_em_path(lock_path)
                        removidos += 1
```

**Opção B** (Quick Fix):
- Descomentar linha 878 em `limpar_locks_com_erro()`
- Expandir critério de status para incluir "confirmado"

### 6. Testes Necessários

Antes de qualquer alteração:

1. ✓ Verify locks de Bruna 10:00 estão no Firestore
2. ✓ Testar que função proposta identifica-os corretamente
3. ✓ Testar que função proposta NÃO remove locks confirmados COM evento existente
4. ✓ Testar que função NÃO remove locks que ainda não expiraram
5. ✓ Testar novo agendamento 10:00 funciona após limpeza
6. ✓ Testar idempotência (retry não duplica)
7. ✓ Testar isolamento tenant (não afeta outros tenants)

---

## IMPACTO DE P0.27-C

**Efeito colateral de P0.27-C**:
- Novo event_id include hora (P0.27-C fix)
- Locks antigos têm evento_id com formato antigo
- Novo sistema procura por novo formato
- Idempotência falha → falso conflito

**Não é um problema de P0.27-C**, é um problema de **gap em limpeza de locks**.

---

## CONCLUSÃO

### Causa Raiz Definitiva

**Locks confirmados órfãos expirados não são removidos.**

Função `limpar_locks_expirados()`:
- ❌ Ignora status="confirmado"
- ❌ Delete comentado
- ❌ Não valida se evento existe

### Ação Recomendada

1. **Curto prazo**: Descomentar delete em `limpar_locks_com_erro()` (risco baixo, apenas afeta erro)
2. **Médio prazo**: Criar `liberar_locks_orfaos_expirados()` (seguro, específico)
3. **Executar**: Para tenant 7394370553 para resolver Bruna 10:00

### Segurança de Execução

✓ Seguro remover lock confirmado se:
- Status = "confirmado"
- evento_id aponta para evento inexistente
- timestamp < 24h atrás
- Feito em lote sem deletar evento

⚠️ Não seguro remover sem validar evento:
- Pode deletar lock de evento legítimo ainda criando
- Pode causar duplicação em race condition

---

**P0.27.2**: Auditoria completa  
**Status**: ✅ Causa raiz identificada + solução proposta  
**Recomendação**: Implementar `liberar_locks_orfaos_expirados()` antes de produção

