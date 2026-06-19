# PATCH AC-01 — Proteção Contra Race Condition em Agenda

**Data Descoberta**: 2026-06-17  
**Severidade**: 🔴 **P0 CRÍTICO**  
**Teste que expôs**: AC-01 (Conflito simples bloqueia criacao)  
**Resultado do Teste**: Ambos eventos foram criados (BUG)

---

## 🐛 Bug Identificado

### Problema

Quando dois usuários tentam agendar o **mesmo profissional** no **mesmo horário** **quase simultaneamente**, Firestore permite que **ambos os eventos sejam criados**, resultando em **double-booking**.

### Evidência Firestore

```
Path 1: Clientes/dono_a/Eventos/ac01_ev1_TIMESTAMP
  → {profissional: "Bruna", hora_inicio: "17:30", hora_fim: "18:00", status: "confirmado"}

Path 2: Clientes/dono_a/Eventos/ac01_ev2_TIMESTAMP
  → {profissional: "Bruna", hora_inicio: "17:30", hora_fim: "18:00", status: "confirmado"}

Resultado: 2 eventos no mesmo slot (INVÁLIDO)
```

### Causa Raiz

Função de criação de evento **NÃO valida conflitos** e **NÃO usa transação Firestore**.

```python
# VULNERÁVEL (código atual):
await atualizar_dado_em_path(path, evento)

# Sem verificação de:
# - Eventos já confirmados no slot
# - Lock exclusivo
# - Idempotência
```

---

## ✅ Solução Recomendada

### Opção A: Transação Firestore (RECOMENDADO)

```python
async def criar_evento_protegido(dono_id: str, evento: dict) -> bool:
    """Criar evento com proteção atômica contra conflito."""
    
    # 1. Validar profissional existe e faz o serviço
    if not validar_profissional_servico(evento["profissional"], evento["servico"]):
        return False
    
    # 2. Validar horário dentro do expediente
    if not validar_expediente(evento["hora_inicio"]):
        return False
    
    # 3. Validar bloqueios
    if tem_bloqueio(dono_id, evento["profissional"], evento["hora_inicio"]):
        return False
    
    # 4. TRANSACAO FIRESTORE
    @firestore.transactional
    async def criar_com_validacao(transaction):
        # 4a. Buscar eventos confirmados sobrepostos
        query = f"Clientes/{dono_id}/Eventos"
        eventos_conflitantes = await buscar_eventos_conflito(
            dono_id,
            evento["profissional"],
            evento["hora_inicio"],
            evento["hora_fim"]
        )
        
        # 4b. Se houver conflito, abortar
        if eventos_conflitantes:
            raise ConflictException("Profissional ocupado nesse horário")
        
        # 4c. Se não houver, criar evento
        path = f"{query}/{evento['id']}"
        await atualizar_dado_em_path(path, evento)
        
        return True
    
    # Executar dentro da transação
    try:
        return await criar_com_validacao()
    except ConflictException:
        return False
```

**Vantagens**:
- ✅ Atômico
- ✅ Garante que validação e criação acontecem juntas
- ✅ Sem race condition

**Desvantagens**:
- Requer refatoração de buscas para usar Firestore transaction

---

### Opção B: Lock por Slot (Alternativa)

```python
async def criar_evento_com_lock(dono_id: str, evento: dict) -> bool:
    """Criar evento com lock exclusivo no slot."""
    
    lock_id = f"{evento['profissional']}_{evento['hora_inicio']}"
    lock_path = f"Clientes/{dono_id}/AgendaLocks/{lock_id}"
    
    try:
        # 1. Tentar criar lock (fails se já existe)
        await criar_documento_unico(lock_path, {"timestamp": datetime.now()})
        
        # 2. Lock adquirido, agora criar evento
        evento_path = f"Clientes/{dono_id}/Eventos/{evento['id']}"
        await atualizar_dado_em_path(evento_path, evento)
        
        # 3. Liberar lock
        await deletar_documento(lock_path)
        
        return True
    except DocumentExistsException:
        # Lock já existe, profissional ocupado
        return False
```

**Vantagens**:
- ✅ Simples de implementar
- ✅ Não requer refatoração de transações

**Desvantagens**:
- ⚠️ Requer cleanup de locks (TTL recomendado)
- ⚠️ Ligeiramente mais overhead

---

## 🎯 Patch Mínimo Recomendado

### Usar **Opção A (Transação)** porque:
1. É a solução "correta" em Firestore
2. Não deixa locks órfãos
3. Garante atomicidade real

### Implementação

**Arquivo**: `services/agenda_service.py` (novo ou existente)

```python
from google.cloud.firestore import transactional

async def criar_agendamento_protegido(
    dono_id: str,
    cliente_id: str,
    profissional: str,
    servico: str,
    data: str,
    hora_inicio: str,
    hora_fim: str,
    idempotency_key: str = None
) -> Dict[str, Any]:
    """
    Criar agendamento com proteção contra race condition.
    
    Retorna:
    {
        "sucesso": bool,
        "evento_id": str (se sucesso),
        "erro": str (se falha),
        "motivo": "conflito" | "profissional_invalido" | etc
    }
    """
    
    # 1. Validações pré-transação
    if not await profissional_faz_servico(dono_id, profissional, servico):
        return {"sucesso": False, "motivo": "profissional_incompativel"}
    
    if not esta_no_expediente(hora_inicio):
        return {"sucesso": False, "motivo": "fora_expediente"}
    
    if tem_bloqueio_profissional(dono_id, profissional, hora_inicio):
        return {"sucesso": False, "motivo": "profissional_bloqueado"}
    
    # 2. Idempotência (se houver idempotency_key)
    if idempotency_key:
        existente = await buscar_por_idempotency(dono_id, idempotency_key)
        if existente:
            return {
                "sucesso": True,
                "evento_id": existente["id"],
                "duplicado": True
            }
    
    # 3. TRANSACAO: Validar conflito + criar evento
    @transactional
    async def criar_atomico(transaction):
        # 3a. Buscar eventos sobrepostos (DENTRO da transação)
        sobrepostos = await buscar_eventos_sobrepostos_tx(
            transaction,
            dono_id,
            profissional,
            hora_inicio,
            hora_fim
        )
        
        if sobrepostos:
            # Abortar transação
            raise FirebaseException("Conflito: profissional ocupado")
        
        # 3b. Criar evento (DENTRO da transação)
        evento_id = f"evt_{uuid.uuid4().hex[:8]}"
        evento = {
            "id": evento_id,
            "dono_id": dono_id,
            "cliente_id": cliente_id,
            "profissional": profissional,
            "servico": servico,
            "data": data,
            "hora_inicio": hora_inicio,
            "hora_fim": hora_fim,
            "status": "confirmado",
            "criado_em": datetime.now(),
            "idempotency_key": idempotency_key
        }
        
        path = f"Clientes/{dono_id}/Eventos/{evento_id}"
        await atualizar_dado_em_path(path, evento)
        
        return evento_id
    
    # 4. Executar transação
    try:
        evento_id = await criar_atomico()
        return {"sucesso": True, "evento_id": evento_id}
    except FirebaseException as e:
        if "Conflito" in str(e):
            return {"sucesso": False, "motivo": "conflito"}
        raise
```

---

## 📋 Plano de Implementação

### Fase 1: Implementar patch
- [ ] Criar `agenda_service.py` com `criar_agendamento_protegido()`
- [ ] Implementar transação Firestore
- [ ] Implementar validações pré-transação
- [ ] Implementar idempotência

### Fase 2: Migrar chamadas
- [ ] Localizar todas as criações de evento
- [ ] Migrar para `criar_agendamento_protegido()`
- [ ] Remover chamadas diretas a `atualizar_dado_em_path()` para eventos

### Fase 3: Testar
- [ ] Re-executar AC-01 (deve passar)
- [ ] Re-executar FASE 2 completa (13/13)
- [ ] Testar com AC-12 (concorrência real)
- [ ] 3 execuções consecutivas

---

## ⏱️ Estimativa

- Implementação: 2-3 horas
- Testes: 1 hora
- **Total**: 3-4 horas

---

## 🔒 Status Pré-Patch

**FASE 2**: BLOQUEADO por BUG P0 em AC-01/AC-02/AC-12

Não é possível declarar FASE 2 aprovada sem proteção contra race condition.

---

**Referência**: `docs/auditorias/MATRIZ_P0_AGENDA_CRITICA_REAL.md`

