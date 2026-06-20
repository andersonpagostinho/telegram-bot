# DIAGNÓSTICO P0 — 3 FALHAS ESTRUTURAIS

**Data:** 2026-06-19  
**Status:** 🔴 CRÍTICO — Falhas identificadas, nenhuma correção aplicada ainda  
**Escopo:** Teste p0_bateria_real_fluxo_completo_conflito_a_criacao.py (7 etapas)  

---

## RESUMO EXECUTIVO

Bateria P0 falhou em 3 etapas críticas com causa raiz em:
1. **FALHA 1** — Runner chama criar_evento_com_lock() com payload incompleto
2. **FALHA 2** — Sugestão consulta path errado (divergência tenant)
3. **FALHA 3** — Limpeza limpa path v2, leitura carrega path v1

**Todas as 3 são bugs de INTEGRAÇÃO (componentes não falam a mesma linguagem).**

---

# FALHA 1 — RUNNER CHAMA CREATE_EVENTO_COM_LOCK ERRADO

## 📍 Localização

**Arquivo:** `tests/p0_bateria_real_fluxo_completo_conflito_a_criacao.py`  
**Linhas:** 102-106, 128-132, 193-197, 447-449  
**Função afetada:** `BateriaP0FluxoCompleto.etapa_1_conflito_detectado()`

## 📝 Evidência de Erro

**Teste chamando:**
```python
resultado_pre = await criar_com_lock_real(
    dono_id=self.tenant_id,
    evento=evento_ocupado,
    event_id=f"evt_ocupado_{data_hoje}_1000"
)
```

**Resultado retornado:**
```
{
    'ok': False,
    'motivo': 'Dados incompletos (profissional, hora_inicio, hora_fim)',
    'tipo_erro': 'validacao'
}
```

## 🔍 Análise Técnica

### Assinatura Real

**Arquivo:** `services/agenda_lock_service.py:223-228`

```python
async def criar_evento_com_lock(
    dono_id: str,
    evento: dict,
    event_id: str,
    excluir_evento_id: Optional[str] = None
) -> Dict[str, Any]:
```

### Validações Internas

**Arquivo:** `services/agenda_lock_service.py:259-275`

```python
# Validação 1: evento.confirmado
if not evento.get("confirmado"):
    return {
        "ok": False,
        "motivo": "Evento não marcado como confirmado",
        "tipo_erro": "validacao"
    }

# Validação 2: profissional, hora_inicio, hora_fim
profissional = evento.get("profissional", "").strip()
hora_inicio = normalizar_hora(evento.get("hora_inicio", ""))
hora_fim = normalizar_hora(evento.get("hora_fim", ""))

if not profissional or not hora_inicio or not hora_fim:
    return {
        "ok": False,
        "motivo": "Dados incompletos (profissional, hora_inicio, hora_fim)",
        "tipo_erro": "validacao"
    }
```

### Payload Enviado

**Arquivo:** `tests/p0_bateria_real_fluxo_completo_conflito_a_criacao.py:87-99`

```python
evento_ocupado = {
    "descricao": "Corte com Bruna (ocupado)",
    "profissional": "Bruna",              # ✅ presente
    "servico": "Corte",
    "data": data_hoje,                    # yyyymmdd
    "hora_inicio": "10:00",               # ✅ presente
    "hora_fim": "10:20",                  # ✅ presente
    "duracao": 20,
    "confirmado": True,                   # ✅ presente
    "status": "confirmado",
    "cliente_id": "cliente_teste_001",
    "cliente_nome": "João Ocupado"
}
```

## ⚠️ Causa Provável

**HIPÓTESE 1 — Dados completos mas função falha:**

A função `normalizar_hora()` pode estar retornando valor falsy (None, "", False) em vez de validar a hora.

**Ponto de investigação:**
- Arquivo: `services/agenda_lock_service.py` ou imports
- Buscar: `def normalizar_hora()` ou `normalizar_hora = `
- Verificar: Que essa função retorna string não-vazia para "10:00"

**HIPÓTESE 2 — payload não é dict (é None ou transformado):**

Importação ou chamada pode estar transformando o evento antes de passar para criar_evento_com_lock.

**Ponto de investigação:**
- Linha 102: `resultado_pre = await criar_com_lock_real(...)`
- Verificar: Que evento_ocupado é de fato um dict com todos os campos

## 🔧 Patch Mínimo Recomendado

### Opção A: Debug Imediato (não produção)

Adicionar print no teste antes da chamada:

```python
print(f"[DEBUG] evento_ocupado completo: {evento_ocupado}")
print(f"[DEBUG] confirmado presente? {'confirmado' in evento_ocupado}")
print(f"[DEBUG] profissional: {evento_ocupado.get('profissional', 'AUSENTE')}")
print(f"[DEBUG] hora_inicio: {evento_ocupado.get('hora_inicio', 'AUSENTE')}")
print(f"[DEBUG] hora_fim: {evento_ocupado.get('hora_fim', 'AUSENTE')}")

resultado_pre = await criar_com_lock_real(...)
```

### Opção B: Se normalizar_hora() estiver quebrado

Procurar por `normalizar_hora` em agenda_lock_service.py e verificar se está importada corretamente.

---

# FALHA 2 — SUGESTÃO CONSULTA PATH ERRADO

## 📍 Localização

**Arquivo teste:** `tests/p0_bateria_real_fluxo_completo_conflito_a_criacao.py`  
**Linhas teste:** 245-252 (ETAPA 3)

**Arquivo função:** `services/event_service_async.py`  
**Linhas função:** 1000-1015  
**Função afetada:** `verificar_conflito_e_sugestoes_profissional()`

## 📝 Evidência de Erro

**Teste cria evento em:**
```
Path: Clientes/bateria_p0_dono_teste/Eventos/evt_ocupado_2026-06-19_1000
```

**Teste chama sugestão com:**
```python
conflito_info = await verificar_conflito_e_sugestoes_profissional(
    user_id=self.actor_id,  # = "bateria_p0_user_teste_001"
    data=data_hoje,
    hora_inicio="10:00",
    duracao_min=20,
    profissional=self.profissional,  # = "Bruna"
    servico=self.servico  # = "Corte"
)
```

**Resultado observado em log:**
```
📦 Eventos existentes: {}
```

**Esperado:**
```
📦 Eventos existentes:
{
    "evt_ocupado_2026-06-19_1000": {
        "profissional": "Bruna",
        "hora_inicio": "10:00",
        ...
    }
}
```

## 🔍 Análise Técnica

### Path Divergência

**Onde evento foi salvo:**
```
Clientes/{tenant_id}/Eventos/...
onde tenant_id = "bateria_p0_dono_teste" (passado explicitamente)
```

**Onde sugestão procura:**
```python
# Arquivo: services/event_service_async.py:1004-1007

user_id_efetivo = await obter_id_dono(user_id)
# onde user_id = "bateria_p0_user_teste_001" (passado pelo teste)

eventos = await buscar_subcolecao(f"Clientes/{user_id_efetivo}/Eventos")
```

### Função obter_id_dono

**Arquivo:** `services/firebase_service_async.py:279-281`

```python
async def obter_id_dono(user_id: str) -> str:
    cliente = await buscar_cliente(user_id)
    return cliente.get("id_negocio", user_id) if cliente else user_id
```

**Comportamento:**
1. Busca cliente com `user_id="bateria_p0_user_teste_001"`
2. Se cliente NÃO existe em Firestore → retorna user_id original
3. Se cliente existe mas sem `id_negocio` → retorna user_id original
4. Se cliente existe e tem `id_negocio` → retorna `id_negocio`

### Problema Real

No teste, o `actor_id="bateria_p0_user_teste_001"` provavelmente:
- Não está registrado em Firestore como cliente
- OU está, mas sem campo `id_negocio`

Resultado: `obter_id_dono("bateria_p0_user_teste_001")` retorna `"bateria_p0_user_teste_001"`

Path consultado: `Clientes/bateria_p0_user_teste_001/Eventos` ← ERRADO!
Path que deveria: `Clientes/bateria_p0_dono_teste/Eventos` ← CORRETO!

## 🔧 Patch Mínimo Recomendado

### Opção A: Runner registra actor como cliente

Antes do teste, criar documento de cliente:

```python
# No setup do teste
cliente_doc = {
    "nome": "Bateria Test Actor",
    "id_negocio": "bateria_p0_dono_teste",  # ← Resolver para tenant
    "email": "test@example.com"
}
await atualizar_dado_em_path(
    "Clientes/bateria_p0_user_teste_001",
    cliente_doc
)
```

### Opção B: Runner passa tenant_id para sugestão

Alterar chamada do teste para passar tenant explicitamente:

```python
# NÃO EXISTE PARÂMETRO ATUALMENTE
# Necessário adicionar ao verificar_conflito_e_sugestoes_profissional()

conflito_info = await verificar_conflito_e_sugestoes_profissional(
    user_id=self.actor_id,
    tenant_id=self.tenant_id,  # ← NOVO PARÂMETRO
    ...
)
```

### Opção C: Função valida tenant explicitamente

Se tenant_id for adicionado, usar em vez de obter_id_dono():

```python
# Em event_service_async.py

async def verificar_conflito_e_sugestoes_profissional(
    user_id: str,
    data: str,
    hora_inicio: str,
    duracao_min: int,
    profissional: str,
    servico: str,
    tenant_id: str = None  # ← NOVO
):
    # Se tenant_id fornecido, use direto
    if tenant_id:
        user_id_efetivo = tenant_id
    else:
        user_id_efetivo = await obter_id_dono(user_id)
    
    eventos = await buscar_subcolecao(f"Clientes/{user_id_efetivo}/Eventos")
```

---

# FALHA 3 — LIMPEZA E LEITURA CONSULTAM PATHS DIFERENTES

## 📍 Localização

**Arquivo teste:** `tests/p0_bateria_real_fluxo_completo_conflito_a_criacao.py`  
**Linhas limpeza:** 496-499 (ETAPA 7)  
**Linhas leitura:** 504-507 (ETAPA 7, validação)

**Arquivo funções:** `utils/contexto_temporario.py` + `handlers/context_manager.py`

## 📝 Evidência de Erro

**ETAPA 7 executa:**

1. **Limpeza:**
```python
from utils.contexto_temporario import limpar_contexto_agendamento_v2

resultado_limpeza = await limpar_contexto_agendamento_v2(
    dono_id=self.tenant_id,              # = "bateria_p0_dono_teste"
    cliente_id=self.actor_id             # = "bateria_p0_user_teste_001"
)
```

2. **Validação (leitura):**
```python
contexto_final = await carregar_contexto_temporario(
    self.actor_id,                       # = "bateria_p0_user_teste_001"
    tenant_id=self.tenant_id             # = "bateria_p0_dono_teste"
)
```

3. **Resultado:**
   - Limpeza fez seu trabalho (sem erro)
   - Mas leitura não encontra os dados removidos
   - Ou encontra dados vazios/incorretos

## 🔍 Análise Técnica

### Path de Limpeza

**Arquivo:** `utils/contexto_temporario.py:133-148`

```python
async def limpar_contexto_agendamento_v2(dono_id: str, cliente_id: str):
    """Path: Clientes/{dono_id}/Sessoes/{cliente_id}"""
    
    path = f"Clientes/{dono_id}/Sessoes/{cliente_id}"
    # Path = "Clientes/bateria_p0_dono_teste/Sessoes/bateria_p0_user_teste_001"
    
    payload = {
        # ... DELETE_FIELD para campos transitórios
        "draft_agendamento": firestore.DELETE_FIELD,
        "dados_confirmacao_agendamento": firestore.DELETE_FIELD,
        ...
    }
    
    return await atualizar_dado_em_path(path, payload)
```

### Path de Leitura

**Arquivo:** `handlers/context_manager.py:25-34`

```python
async def carregar_contexto_temporario(user_id: str, tenant_id: str = None):
    """Carrega contexto com guard rail se tenant_id fornecido."""
    
    if tenant_id:
        # V1 COM GUARD RAIL — path: Clientes/{tenant_id}/Sessoes/{user_id}
        return await carregar_v1_com_guard(user_id, tenant_id=tenant_id)
    
    # FALLBACK (sem tenant_id) — path: Clientes/{user_id}/MemoriaTemporaria/contexto
    path = CONTEXT_PATH_TEMPLATE.format(user_id=user_id)
    return await buscar_dado_em_path(path)
```

Onde `carregar_v1_com_guard` está em `utils/contexto_temporario.py:64-80`:

```python
async def carregar_sessao_temporaria(actor_id: str, tenant_id: str):
    """Path: Clientes/{tenant_id}/Sessoes/{actor_id}"""
    
    path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"
    # Path = "Clientes/bateria_p0_dono_teste/Sessoes/bateria_p0_user_teste_001"
    # ... lógica de migração
```

### Path Comparação

| Operação | Path | Esperado |
|----------|------|----------|
| **Limpeza** | `Clientes/{dono_id}/Sessoes/{cliente_id}` | `Clientes/bateria_p0_dono_teste/Sessoes/bateria_p0_user_teste_001` |
| **Leitura** | `Clientes/{tenant_id}/Sessoes/{user_id}` | `Clientes/bateria_p0_dono_teste/Sessoes/bateria_p0_user_teste_001` |

✅ **Os paths SÃO iguais!** Problema está em outro lugar.

## ⚠️ Causa Provável

### HIPÓTESE 1 — Limpeza não usou DELETE_FIELD corretamente

`atualizar_dado_em_path()` pode não estar processando `firestore.DELETE_FIELD` corretamente.

**Ponto de investigação:**
- Arquivo: `services/firebase_service_async.py`
- Buscar: `async def atualizar_dado_em_path()`
- Verificar: Que usa `merge=False` ao atualizar

**Por que:** Firestore DELETE_FIELD só funciona com:
```python
db.collection("path").document("id").update({
    "field": firestore.DELETE_FIELD  # ← Requer update(), não set()
})
```

Se usar `set(..., merge=True)`, DELETE_FIELD é ignorado!

### HIPÓTESE 2 — Leitura carrega versão anterior em cache

Cache em memória pode estar retornando contexto antigo.

**Ponto de investigação:**
- Arquivo: `utils/contexto_temporario.py`
- Buscar: Inicialização de cache, variáveis globais
- Verificar: Que `carregar_sessao_temporaria()` sempre busca Firestore, não cache

### HIPÓTESE 3 — Contexto foi criado em path diferente durante fluxo

Versões anteriores (v1 legada) podem ter salvo em path diferente.

**Ponto de investigação:**
- Arquivo: `utils/contexto_temporario.py:67-74`
- Buscar: Seção "Read-through com migração"
- Verificar: Migração está movendo dados corretamente?

## 🔧 Patch Mínimo Recomendado

### Opção A: Validar DELETE_FIELD em atualizar_dado_em_path()

Verificar se função está usando `.update()` e não `.set(merge=True)`:

```python
# Em services/firebase_service_async.py

async def atualizar_dado_em_path(path, dados):
    # CORRETO: usa .update() para DELETE_FIELD
    if any(v == firestore.DELETE_FIELD for v in dados.values()):
        # Usar update, não set
        await db.document(path).update(dados)
    else:
        # Pode usar set com merge
        await db.document(path).set(dados, merge=True)
```

### Opção B: Debug limpeza vs leitura

Adicionar logs no teste:

```python
# Antes de limpar
print(f"[DEBUG ETAPA 7a] Contexto antes de limpar:")
contexto_pre = await carregar_contexto_temporario(
    self.actor_id,
    tenant_id=self.tenant_id
)
print(f"[DEBUG] {contexto_pre}")

# Limpar
resultado_limpeza = await limpar_contexto_agendamento_v2(
    dono_id=self.tenant_id,
    cliente_id=self.actor_id
)
print(f"[DEBUG ETAPA 7b] Resultado limpeza: {resultado_limpeza}")

# Depois de limpar
print(f"[DEBUG ETAPA 7c] Contexto depois de limpar:")
contexto_final = await carregar_contexto_temporario(
    self.actor_id,
    tenant_id=self.tenant_id
)
print(f"[DEBUG] {contexto_final}")
```

### Opção C: Validar path em ambas as funções

Adicionar guard rails que imprimem path usada:

```python
# Em utils/contexto_temporario.py

async def limpar_contexto_agendamento_v2(dono_id: str, cliente_id: str):
    path = f"Clientes/{dono_id}/Sessoes/{cliente_id}"
    print(f"🧹 [LIMPAR] Path: {path}", flush=True)  # ← ADD LOG
    
async def carregar_sessao_temporaria(actor_id: str, tenant_id: str):
    path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"
    print(f"📖 [CARREGAR] Path: {path}", flush=True)  # ← ADD LOG
```

---

## RESUMO DE PRÓXIMOS PASSOS

### Imediatamente (ordem de criticidade)

1. **FALHA 1** — Verificar normalizar_hora() em agenda_lock_service.py
   - Se houver erro em normalizar_hora → evento_ocupado será rejeitado
   - Fix: Procurar import/def e validar retorno

2. **FALHA 2** — Adicionar tenant_id ao teste ou registrar actor como cliente
   - Causa: obter_id_dono não resolve tenant corretamente
   - Fix: Opção A ou B recomendada

3. **FALHA 3** — Validar DELETE_FIELD em atualizar_dado_em_path()
   - Causa: Provável que UPDATE não funcione com DELETE_FIELD
   - Fix: Opção A recomendada

### Não corrigir ainda

✅ Diagnóstico completo (este documento)  
❌ Implementar patches  

Aguardar confirmação de causa raiz em cada falha.

---

**Status:** 🔴 DIAGNÓSTICO CONCLUÍDO, AGUARDANDO CONFIRMAÇÃO ANTES DE PATCHES

