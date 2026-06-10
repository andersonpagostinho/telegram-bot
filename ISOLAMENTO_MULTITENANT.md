# Isolamento Multi-Tenant em scheduler/notificacoes_scheduler.py

## Visão Geral

Patch implementado para garantir que `processar_notificacoes_agendadas()` processa notificações apenas de **tenants raiz (donos)**, não de clientes finais ou profissionais.

---

## Problema Identificado

Antes do patch, a função iterava sobre todos os documentos em `Clientes/`:

```python
clientes = await buscar_subcolecao("Clientes") or {}
for user_id in clientes.keys():
    notificacoes = await buscar_notificacoes_pendentes(user_id)
    # processa sem validar tipo_usuario
```

**Risco:** Um documento de cliente final (tipo_usuario="cliente") seria tratado como tenant, com acesso a `Clientes/{cliente_id}/NotificacoesAgendadas`.

---

## Solução Implementada

### **Código Adicionado (linhas 104-115)**

```python
for user_id in clientes.keys():
    # 🔐 VALIDAÇÃO DE TENANT: processar apenas donos
    try:
        doc_cli = await buscar_dado_em_path(f"Clientes/{user_id}") or {}
        tipo_usuario = (doc_cli.get("tipo_usuario") or "").strip().lower()

        if tipo_usuario != "dono":
            logger.info(f"[NOTIF] pulando user_id não-dono: {user_id} tipo_usuario={tipo_usuario}")
            continue
    except Exception as e:
        logger.warning(f"[NOTIF] erro ao validar tenant {user_id}: {e}")
        continue

    path = f"Clientes/{user_id}/NotificacoesAgendadas"
    notificacoes = await buscar_notificacoes_pendentes(user_id)
```

### **Lógica**

1. Para cada `user_id` em `Clientes/`
2. Carregar documento: `Clientes/{user_id}`
3. Verificar campo `tipo_usuario`
4. **Se `tipo_usuario != "dono"`:**
   - Log: `[NOTIF] pulando user_id não-dono: {user_id} tipo_usuario={tipo}`
   - Pular para próximo
5. **Se `tipo_usuario == "dono"`:**
   - Processar notificações normalmente

---

## Casos Cobertos

| Tipo Usuario | Acao | Log |
|--------------|------|-----|
| `"dono"` | Processa | (nenhum) |
| `"cliente"` | Pula | `[NOTIF] pulando user_id não-dono: {id} tipo_usuario=cliente` |
| `"profissional"` | Pula | `[NOTIF] pulando user_id não-dono: {id} tipo_usuario=profissional` |
| (vazio/ausente) | Pula | `[NOTIF] pulando user_id não-dono: {id} tipo_usuario=` |
| outro valor | Pula | `[NOTIF] pulando user_id não-dono: {id} tipo_usuario={valor}` |

---

## Impacto

### **Segurança**
- ✅ Isolamento de tenant garantido
- ✅ Clientes não processam notificações umas das outras
- ✅ Profissionais não acessam notificações de clientes

### **Performance**
- ✅ Sem degradação (1 busca adicional por tenant, já otimizado em `buscar_notificacoes_pendentes`)
- ✅ Logging estratégico para debug

### **Código**
- ✅ Não altera fluxo existente
- ✅ Não quebra follow-up, agenda, criação de evento
- ✅ Tratamento de erro robusto (try/except)

---

## Testes

### **Teste 1: Processar apenas DONO**
```
Entrada: user_id com tipo_usuario="dono"
Esperado: Chamar buscar_notificacoes_pendentes(user_id)
Resultado: ✅ PASSOU
```

### **Teste 2: PULAR cliente**
```
Entrada: user_id com tipo_usuario="cliente"
Esperado: Log "[NOTIF] pulando..." + NÃO chamar buscar_notificacoes_pendentes
Resultado: ✅ PASSOU
```

### **Teste 3: PULAR sem tipo_usuario**
```
Entrada: user_id sem campo tipo_usuario
Esperado: Log skip + NÃO processar
Resultado: ✅ PASSOU
```

### **Teste 4: PULAR profissional**
```
Entrada: user_id com tipo_usuario="profissional"
Esperado: Log skip + NÃO processar
Resultado: ✅ PASSOU
```

---

## Regressão

Todos os testes anteriores continuam passando:

- ✅ test_notificacoes_expirado.py (3/3 PASSOU)
- ✅ test_notificacao_profissional.py (3/3 PASSOU)
- ✅ test_integracao_simples.py (4/4 PASSOU)

---

## Validações

```bash
✅ python -m py_compile scheduler/notificacoes_scheduler.py
✅ python test_isolamento_multitenant.py (4/4 testes)
✅ python test_notificacoes_expirado.py (3/3 testes)
✅ python test_notificacao_profissional.py (3/3 testes)
```

---

## Logs Esperados

### **Execução Normal (com 2 donos)**
```
⏰ processar_notificacoes_agendadas() iniciado...
✅ Notificação cliente criada: {uuid}
✅ Notificação profissional criada: {uuid}
```

### **Execução com Cliente na lista**
```
⏰ processar_notificacoes_agendadas() iniciado...
[NOTIF] pulando user_id não-dono: usuario_cliente tipo_usuario=cliente
✅ Notificação cliente criada: {uuid}
```

### **Execução com Erro de Validação**
```
⏰ processar_notificacoes_agendadas() iniciado...
[NOTIF] erro ao validar tenant usuario_123: ConnectionError
```

---

## Próximas Melhorias (Opcional)

- [ ] Cache de `tipo_usuario` para evitar busca redundante
- [ ] Métrica de usuarios pulados por tipo
- [ ] Dashboard de isolamento de tenant
- [ ] Auditoria de acesso por tipo_usuario

---

## Checklist de Implementacao

- ✅ Adicionar validacao tipo_usuario
- ✅ Pular se nao for dono
- ✅ Logar skip apropriadamente
- ✅ Nao alterar follow-up
- ✅ Nao alterar agenda
- ✅ Nao alterar criacao evento
- ✅ Nao alterar helper notificacao
- ✅ Teste 1: dono processa
- ✅ Teste 2: cliente pula
- ✅ Teste 3: sem tipo pula
- ✅ Teste 4: profissional pula
- ✅ Validar sintaxe
- ✅ Regressao: expiração
- ✅ Regressao: notificação profissional
