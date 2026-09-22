# ARQUITETURA_WEBHOOK_DOMAINSERVICE — Regra de Ouro da Conversão

**Versão:** 1.0  
**Data:** 2026-07-27  
**Criticidade:** P0 Arquitetural  
**Status:** Obrigatória antes de CONTRATO_CONVERSAO_LEAD_TENANT.md  

---

## 🚨 REGRA INVIOLÁVEL

**Nenhuma mudança de estado comercial será disparada diretamente por webhook.**

Sempre passa por um **serviço de domínio** intermediário.

```
❌ PROIBIDO:
Webhook → Firestore (direto)

✅ OBRIGATÓRIO:
Webhook → Adapter → BillingDomainService → Máquinas de Estado → Firestore → Eventos Internos
```

---

## 🏗️ ARQUITETURA CORRETA

### Camada 1: Webhook (Entrada)

```python
# webhook_handler.py
@router.post("/webhooks/hotmart")
async def receber_webhook_hotmart(payload: dict):
    # Validar autenticação
    validar_assinatura(payload)
    
    # Passar para adapter, NÃO para Firestore direto
    adapter = HotmartWebhookAdapter(payload)
    await adapter.processar()
```

---

### Camada 2: Adapter (Transformação)

```python
# hotmart_adapter.py
class HotmartWebhookAdapter:
    def __init__(self, payload):
        self.evento = self._extrair_evento(payload)
        self.tenant_id = self._extrair_tenant(payload)
        self.user_id = self._extrair_usuario(payload)
    
    async def processar(self):
        # Passar para serviço de domínio
        domain_service = BillingDomainService(
            tenant_id=self.tenant_id,
            user_id=self.user_id
        )
        await domain_service.processar_evento(self.evento)
```

**Responsabilidade Adapter:**
- Extrair dados do payload Hotmart
- Converter para formato interno
- Validar estrutura básica
- Passar para domínio

**NÃO:**
- ❌ Salvar direto em Firestore
- ❌ Atualizar estado
- ❌ Chamar máquina de estados

---

### Camada 3: BillingDomainService (Lógica)

```python
# billing_domain_service.py
class BillingDomainService:
    def __init__(self, tenant_id, user_id):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.firestore = FirestoreClient()
    
    async def processar_evento(self, evento):
        """
        Processa evento Hotmart com todas as proteções.
        
        Fluxo:
        1. Validar evento
        2. Verificar idempotência
        3. Carregar estado atual
        4. Aplicar máquina de estados
        5. Persistir
        6. Registrar auditoria
        7. Publicar eventos internos
        """
        
        # 1. Validar evento
        self._validar_evento(evento)
        
        # 2. Verificar idempotência
        if await self._evento_processado(evento):
            return {"status": "already_processed"}
        
        # 3. Carregar estado atual
        estado_atual = await self._carregar_estado()
        
        # 4. Aplicar máquina de estados
        transicao = self._aplicar_transicao(estado_atual, evento)
        
        # 5. Persistir (com transação!)
        async with self.firestore.transaction() as txn:
            await txn.update_doc(
                path=f"tenants/{self.tenant_id}/assinaturas/{self.user_id}",
                data=transicao.novo_estado
            )
            
            # Registrar evento processado (idempotência)
            await txn.set_doc(
                path=f"tenants/{self.tenant_id}/webhooks/processados/{evento.id}",
                data={
                    "provider_event_id": evento.id,
                    "provider": "hotmart",
                    "processed_at": datetime.now(),
                    "result": "success"
                }
            )
        
        # 6. Registrar auditoria
        await self._registrar_auditoria(evento, transicao)
        
        # 7. Publicar eventos internos
        await self._publicar_eventos_internos(transicao)
        
        return {"status": "success", "transicao": transicao}
    
    def _validar_evento(self, evento):
        """Validar estrutura, campos obrigatórios, tipos."""
        if not evento.id:
            raise ValueError("Event ID é obrigatório")
        if evento.tipo not in self.TIPOS_VALIDOS:
            raise ValueError(f"Tipo de evento inválido: {evento.tipo}")
        # ... mais validações
    
    async def _evento_processado(self, evento):
        """Verificar se esse evento já foi processado (idempotência)."""
        doc = await self.firestore.get_doc(
            path=f"tenants/{self.tenant_id}/webhooks/processados/{evento.id}"
        )
        return doc is not None
    
    async def _carregar_estado(self):
        """Carregar estado atual da assinatura."""
        return await self.firestore.get_doc(
            path=f"tenants/{self.tenant_id}/assinaturas/{self.user_id}"
        )
    
    def _aplicar_transicao(self, estado_atual, evento):
        """Aplicar máquina de estados."""
        # Seria chamada a máquina de estados do Billing
        # Resultado: nova estado + validações
        maquina = MaquinaEstadoAssinatura(estado_atual)
        return maquina.processar(evento)
    
    async def _registrar_auditoria(self, evento, transicao):
        """Registrar mudança em auditoria."""
        await self.firestore.add_doc(
            path=f"tenants/{self.tenant_id}/auditoria",
            data={
                "tipo": "webhook_processado",
                "evento_hotmart_id": evento.id,
                "transicao_de": transicao.estado_anterior,
                "transicao_para": transicao.novo_estado,
                "timestamp": datetime.now(),
                "usuario": self.user_id
            }
        )
    
    async def _publicar_eventos_internos(self, transicao):
        """Publicar eventos internos para outros serviços."""
        # Exemplo: assinatura_ativada, assinatura_cancelada
        for evento_interno in transicao.eventos_internos:
            await self.event_bus.publish(evento_interno)
```

**Responsabilidade BillingDomainService:**
- ✅ Validar evento
- ✅ Verificar idempotência
- ✅ Carregar estado
- ✅ Aplicar máquina de estados
- ✅ Persistir com transação
- ✅ Registrar auditoria
- ✅ Publicar eventos internos

**NÃO:**
- ❌ Salvar diretamente
- ❌ Lógica de negócio sem máquina de estados
- ❌ Ignorar duplicações

---

### Camada 4: Máquinas de Estado (Validação)

```python
# billing_state_machines.py

class MaquinaEstadoAssinatura:
    """
    Estados: PENDENTE → ATIVA → CANCELAMENTO_AGENDADO → CANCELADA → ENCERRADA
    """
    
    TRANSICOES_VALIDAS = {
        "PENDENTE": ["ATIVA", "CANCELADA"],
        "ATIVA": ["CANCELAMENTO_AGENDADO", "SUSPENSA"],
        "CANCELAMENTO_AGENDADO": ["ATIVA", "CANCELADA"],
        "CANCELADA": ["ENCERRADA"],
        "SUSPENSA": ["ATIVA", "CANCELADA"],
        "ENCERRADA": []
    }
    
    def __init__(self, estado_atual):
        self.estado_atual = estado_atual
    
    def processar(self, evento):
        novo_estado = self._calcular_novo_estado(evento)
        
        # Validar transição
        if novo_estado not in self.TRANSICOES_VALIDAS.get(self.estado_atual, []):
            raise ValueError(
                f"Transição inválida: {self.estado_atual} → {novo_estado} "
                f"para evento {evento.tipo}"
            )
        
        return Transicao(
            estado_anterior=self.estado_atual,
            novo_estado=novo_estado,
            eventos_internos=self._gerar_eventos(evento),
            mudancas_firestore=self._gerar_mudancas(evento)
        )
    
    def _calcular_novo_estado(self, evento):
        # Lógica baseada em tipo de evento
        if evento.tipo == "payment_approved":
            return "ATIVA"
        elif evento.tipo == "subscription_canceled":
            return "CANCELADA"
        # ...
```

**Responsabilidade Máquina de Estados:**
- ✅ Validar transições
- ✅ Calcular novo estado
- ✅ Gerar eventos internos
- ✅ Gerar mudanças para Firestore

**NÃO:**
- ❌ Interagir com Firestore
- ❌ Validar webhook (responsabilidade do Adapter)

---

### Camada 5: Firestore (Persistência)

```python
# Feito DENTRO de BillingDomainService com transação
async with firestore.transaction() as txn:
    txn.update_doc(path, dados)
    txn.set_doc(idempotencia_path, dados)
```

**Responsabilidade Firestore:**
- ✅ Persistência atômica
- ✅ Transações multi-documento
- ✅ Índices para consulta

**NÃO:**
- ❌ Lógica de negócio
- ❌ Validação de estado

---

### Camada 6: Eventos Internos (Publicação)

```python
# event_bus.py
async def publicar(evento_interno):
    """
    Exemplo: assinatura_ativada
    {
        "tipo": "assinatura_ativada",
        "tenant_id": "...",
        "user_id": "...",
        "timestamp": "...",
        "origem": "webhook_payment_approved"
    }
    """
```

**Responsabilidade Eventos Internos:**
- ✅ Notificar outros serviços
- ✅ Manter auditoria de mudanças
- ✅ Possibilitar reprocessamento

---

## 🎯 BENEFÍCIOS DESSA ARQUITETURA

### 1. **Proteção contra duplicação**
```
Webhook chega 2x com mesmo event_id
    ↓
Adapter → BillingDomainService
    ↓
Verificar: evento_processado?
    ↓
Sim: retornar sem reprocessar
Não: processar e marcar como processado
```

### 2. **Proteção contra out-of-order**
```
Webhook 1: payment_approved (chega em 2º)
Webhook 2: subscription_created (chega em 1º)

Máquina de estados detecta:
"Não posso ir de PENDENTE para ATIVA"
"Esperando CRIADA primeiro"
```

### 3. **Facilita mudança de provedor**
```
Se mudar de Hotmart para Stripe:
- Criar novo Adapter (StripeWebhookAdapter)
- BillingDomainService permanece igual
- Máquinas de estado permanecem igual
- Só muda ponto de entrada
```

### 4. **Facilita testes**
```
Testar BillingDomainService:
- Não precisa Hotmart de verdade
- Passar evento mock
- Validar estado resultante

Testar Adapter:
- Apenas transformação
- Sem lógica de negócio
```

### 5. **Auditoria completa**
```
Cada mudança fica registrada:
- Evento que disparou (qual Hotmart event_id?)
- Estado antes
- Estado depois
- Timestamp exato
- Usuário/tenant
```

### 6. **Recuperação de falhas**
```
Se BillingDomainService falhar no meio:
- Webhook não foi marcado como processado
- Hotmart reentrega
- Ser reconsumido do ponto onde falhou
```

---

## 🚫 O QUE NUNCA FAZER

### ❌ Anti-padrão 1: Webhook direto em Firestore
```python
@router.post("/webhooks/hotmart")
async def webhook(payload):
    # NÃO FAZER ISSO:
    await firestore.update_doc(
        path="tenants/.../assinaturas/...",
        data=payload  # ❌ direto
    )
```

**Por quê?**
- Sem validação
- Sem idempotência
- Sem lógica de máquina de estados
- Impossível testar

### ❌ Anti-padrão 2: Múltiplos handlers webhook
```python
# webhook_handler.py
async def webhook_hotmart(payload):
    if payload.tipo == "payment_approved":
        # Handler 1
        await ativar_assinatura()
    elif payload.tipo == "subscription_canceled":
        # Handler 2
        await cancelar_assinatura()

# Depois alguém cria:
# webhook_handler2.py com handlers diferentes
# webhook_handler_v2.py com outra lógica
# webhook_novo.py com outra

# Resultado: confusão total
```

**Por quê?**
- Lógica dispersa
- Impossível saber qual é a verdadeira
- Manutenção impossível

### ❌ Anti-padrão 3: Salvamento sem transação
```python
# NÃO FAZER:
await firestore.update(assinatura_path, novo_estado)
await firestore.set(idempotencia_path, evento_id)  # ❌ separado

# Se falhar entre as duas linhas: inconsistência
```

**Correto:**
```python
async with firestore.transaction() as txn:
    txn.update(assinatura_path, novo_estado)
    txn.set(idempotencia_path, evento_id)
    # Ambos salvos atomicamente ou nenhum
```

---

## 📋 CHECKLIST — Antes de Processar Qualquer Webhook

```
☐ Evento tem provider_event_id único?
☐ Adapter valida estrutura básica?
☐ BillingDomainService verifica idempotência?
☐ Máquina de estados valida transição?
☐ Firestore salva com transação?
☐ Auditoria registra mudança?
☐ Eventos internos são publicados?
☐ Resposta HTTP 200 apenas após sucesso?

Se qualquer ☐ não marcado: ❌ REJEITAR WEBHOOK
```

---

## 🔗 RELAÇÃO COM OUTROS DOCUMENTOS

- [[CONTRATO_BILLING_NEOEVE.md]] — Define máquinas de estado
- [[CONTRATO_CONVERSAO_LEAD_TENANT.md]] — Usa essa arquitetura
- [[VALIDACAO_HOTMART.md]] — Testa essa implementação

---

## 📅 Timeline de Implementação

1. **Antes de Sandbox:** Implementar BillingDomainService + Máquinas de Estado
2. **Sandbox:** Testar com VALIDACAO_HOTMART.md (Teste 9-18)
3. **Produção:** Validar com dados reais

---

## ✅ RESULTADO ESPERADO

```
Webhook Hotmart
    ↓
HTTP 200 (acknowledgment rápido)
    ↓
Adapter processa
    ↓
BillingDomainService:
  ├─ Valida
  ├─ Verifica idempotência
  ├─ Carrega estado
  ├─ Aplica máquina
  ├─ Persiste com transação
  ├─ Registra auditoria
  └─ Publica eventos internos

Resultado: Estado consistente, recuperável, auditável, testável.
```

---

**ARQUITETURA_WEBHOOK_DOMAINSERVICE.md** — Padrão obrigatório  
**Status:** Estabelecido como requisito pré-conversão  
**Próximo passo:** Criar CONTRATO_CONVERSAO_LEAD_TENANT.md referenciando essa arquitetura

