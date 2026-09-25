# C4.2.5 — DESENHO DO LOCK ATÔMICO

**Data:** 2026-09-25  
**Status:** PRÉ-IMPLEMENTAÇÃO (auditoria de design)  

---

## DESENHO DO LOCK

### Problema a Resolver

```
ANTES (inseguro):
  Dois processos geram timestamp idêntico
  Ambos escrevem com merge=true
  Ambos passam na revalidação
  Resultado: Duplicação

DEPOIS (seguro):
  Apenas um consegue criar lock determinístico
  Operação falha atomicamente se já existe
  Resultado: Exclusividade garantida
```

### Solução: Lock Document

```
Estrutura Firestore:

Clientes/{tenant_id}/
  NotificacoesAgendadas/
    {notif_id}/
      (documento principal da notificação)
      
      locks/
        {lock_id}  ← Documento de lock (CHAVE = notif_id, não processo_id!)
          {
            processo_id: "uuid-do-processo",
            claimed_at: "2026-09-25T16:08:45.234567-03:00",
            expires_at: "2026-09-25T16:09:45.234567-03:00",
            status: "ACTIVE"
          }
```

### Decisão Crítica: Lock ID

#### ❌ ERRADO:
```
locks/{processo_id}

Problema: Ambos conseguem criar (proc_A e proc_B são diferentes)
locks/proc_1_xxxx   ← A consegue criar
locks/proc_2_yyyy   ← B também consegue criar
Resultado: Não garante exclusividade
```

#### ✅ CORRETO:
```
locks/{notif_id}

Garantia: Apenas um lock por notificação
locks/t9_517cd4d5   ← Apenas A consegue criar
                    ← B tenta criar, recebe ALREADY_EXISTS

Resultado: Exclusividade garantida
```

### Operação Atômica Firestore

**Método:** `DocumentReference.create(data)`

```python
# Pseudocódigo:

lock_path = f"Clientes/{tenant_id}/NotificacoesAgendadas/{notif_id}/locks/{notif_id}"

lock_data = {
    "processo_id": processo_id,
    "claimed_at": agora.isoformat(),
    "expires_at": (agora + timedelta(minutes=1)).isoformat(),
    "status": "ACTIVE"
}

try:
    await ref.create(lock_data)  # Falha se já existe
    return (True, "Lock criado com sucesso")
except AlreadyExists:
    return (False, "Lock já existe")
except Exception as e:
    return (False, str(e))
```

**Semântica:**
- `create()` falha atomicamente se documento já existe
- Não há race condition entre a verificação e a criação
- Firestore garante exclusividade em nível de servidor

---

## DETECÇÃO DE COLISÃO

### Cenário de Concorrência (Agora Seguro)

```
TEMPO: 16:08:45.234567

Processo A:
  1. Lê notif_id (sucesso)
  2. Tenta criar lock
  3. Firestore: ✅ Criar locks/t9_xxxx
  4. Sucesso! Retorna True

Processo B (paralelo, mesmo microsegundo):
  1. Lê notif_id (sucesso)
  2. Tenta criar lock
  3. Firestore: ❌ ALREADY_EXISTS (A já criou)
  4. Falha! Retorna False

Resultado:
  ✅ Apenas A consegue o claim
  ✅ B é bloqueado automaticamente
  ✅ Nenhuma duplicação possível
```

### Operação Firestore Exata

**Firebase SDK async (python):**

```python
from google.cloud.firestore_v1.exceptions import AlreadyExists

ref = db.collection("Clientes").document(tenant_id)\
         .collection("NotificacoesAgendadas").document(notif_id)\
         .collection("locks").document(notif_id)

try:
    await ref.create(lock_data)
    # ✅ Lock criado com sucesso
except AlreadyExists:
    # ❌ Lock já existe
except Exception as e:
    # ❌ Erro inesperado
```

---

## RECUPERAÇÃO DE LOCK EXPIRADO

### Problema

```
Cenário: Processo A cria lock, travador durante envio, nunca confirma
        Timeout: 60 segundos expira
        Processo B tenta recuperar o lock expirado

Risco: Ambos conseguem criar novo lock?
```

### Solução Proposta

**Operação atômica condicional não-disponível facilmente na API async.**

Opções:

#### Opção A: Não implementar recovery (Simples, Seguro)
```
Se lock expirou:
  ❌ Não recuperar
  ✅ Apenas aguardar renovação manual
  
Downside: Notificação fica travada até expiração natural
Upside: 100% seguro, sem race condition
```

#### Opção B: Usar Firestore Transaction (Correto, Complexo)
```python
transaction = db.transaction()

@transaction.transactional
async def recuperar_lock_expirado(tx):
    lock = tx.get(lock_path)
    
    if lock.exists:
        expires_at = lock.get("expires_at")
        if datetime.fromisoformat(expires_at) > agora:
            return False  # Ainda válido, não recuperar
    
    # Atômica: criar novo lock dentro da transaction
    tx.set(lock_path, nova_lock_data)
    return True
```

Problema: Async Transaction não funciona bem com decorator pattern

#### Opção C: Usar Update Condicional (Se disponível)
```
Firestore não expõe precondição "update só se campo == valor" na API Python async
```

---

## RECOMENDAÇÃO FINAL

### Para C4.2.5

**Use Opção A: Sem Recovery**

Razão:
- Lock document (`create()`) é atomicamente seguro
- Recovery exigiria Transaction ou Precondição (indisponíveis facilmente)
- Timeout de 60 segundos é razoável para máq. travada
- Simplicidade > Otimização prematura

Fluxo simplificado:

```
tentar_claim():
  1. Tenta criar lock/{notif_id}
  2. Se sucesso: retorna True (claim obtido)
  3. Se ALREADY_EXISTS: retorna False (outro tem)
  4. Se expirado:
     - Não recuperar automaticamente
     - Deixar expirar (60s)
     - Próximo `tentar_claim()` vê documento "morto" e recria
```

---

## ARQUIVOS QUE SERÃO MODIFICADOS

### 1. services/notificacoes_idempotencia_service.py

```
Linhas a modificar:
  - 36-175: tentar_claim_notificacao()
  
Mudanças:
  - Remover operação merge
  - Adicionar criação de lock com create()
  - Detectar AlreadyExists
  - Simplificar (sem retry interno para recovery)
```

### 2. services/firebase_service_async.py

```
Possível adição:
  - Função auxiliar para criar documento atomicamente
  - Ou reutilizar ref.create() diretamente em notificacoes_idempotencia_service
```

### 3. tests/test_c423_regression_scheduler_integration.py

```
Atualizar T2:
  - Validar que lock document é criado
  - Validar exclusividade real
  - Múltiplas iterações para detectar flakiness
```

---

## CHECKLIST PRÉ-IMPLEMENTAÇÃO

- [ ] Firestore permite `create()`? SIM (verificado)
- [ ] `create()` falha com AlreadyExists? SIM (comportamento padrão)
- [ ] AlreadyExists é importável? SIM (google.cloud.firestore_v1.exceptions)
- [ ] Lock path é determinístico (não depende processo_id)? SIM
- [ ] Timeout de 60s é suficiente? SIM
- [ ] Recovery não é crítica para MVP? SIM

---

## PRÓXIMOS PASSOS

1. ✅ Auditoria pré-edição (este documento)
2. ⏳ Implementar tentar_claim_notificacao() com lock
3. ⏳ Rodar testes T1-T10
4. ⏳ Validar concorrência
5. ⏳ Novo regression gate C4.2.3
6. ⏳ Aprovação ou bloqueio

