# PLANO IMPLEMENTAÇÃO — Arquitetura Trial+Billing+Conversão

**Data:** 2026-07-27  
**Baseado em:** AUDITORIA_IMPLEMENTACAO_CONTRATOS_2026_07_27.md  
**Escopo:** Implementar 26 componentes (5.8% hoje → 100% ao final)  
**Duração Estimada:** 17-24 dias  
**Risco:** Médio-alto (webhook é crítico)  

---

## 📋 RESUMO EXECUTIVO

Contratos comerciais (CATALOGO, TRIAL, BILLING, CONVERSAO, ARQUITETURA) especificam arquitetura completa que **não foi implementada** no código Python.

**Gap Identificado:**
- Código atual: Lead Status Management + Multi-tenant Isolation ✅
- Faltante: Trial State Machine, Billing Domain Service, Webhook Handler ❌

**Solução:** 6 fases sequenciais, iniciando com State Machines (sem dependências).

---

## 🎯 FASE 1: STATE MACHINES (Dias 1-4)

### Objetivo
Implementar 4 máquinas de estado independentes que validam transições e evitam estados inválidos.

### Componentes

#### 1.1 TrialStateMachine
**Arquivo:** `services/trial_state_machine.py`

**Classe:**
```python
class TrialStateMachine:
    STATES = ["PREPARADO", "ATIVO", "EXPIRADO", "CONVERTIDO", "DELETADO"]
    
    TRANSICOES_VALIDAS = {
        "PREPARADO": ["ATIVO"],
        "ATIVO": ["EXPIRADO"],
        "EXPIRADO": ["CONVERTIDO", "DELETADO"],
        "CONVERTIDO": [],
        "DELETADO": []
    }
    
    def __init__(self, estado_atual):
        self.estado_atual = estado_atual
    
    def pode_transicionar_para(self, novo_estado) -> bool
    def transicionar(self, novo_estado) -> dict  # retorna {sucesso, motivo}
```

**Testes (UNIT):**
```
☐ PREPARADO → ATIVO [válida]
☐ PREPARADO → EXPIRADO [inválida]
☐ ATIVO → EXPIRADO [válida]
☐ EXPIRADO → CONVERTIDO [válida]
☐ EXPIRADO → DELETADO [válida]
☐ CONVERTIDO → * [todas inválidas]
```

---

#### 1.2 MaquinaEstadoAssinatura
**Arquivo:** `services/billing_state_machines.py`

**Classe:**
```python
class MaquinaEstadoAssinatura:
    STATES = ["PENDENTE", "ATIVA", "CANCELAMENTO_AGENDADO", 
              "CANCELADA", "ENCERRADA"]
    
    TRANSICOES_VALIDAS = {
        "PENDENTE": ["ATIVA"],
        "ATIVA": ["CANCELAMENTO_AGENDADO", "SUSPENSA"],
        "CANCELAMENTO_AGENDADO": ["ATIVA", "CANCELADA"],
        "CANCELADA": ["ENCERRADA"],
        "SUSPENSA": ["ATIVA", "CANCELADA"],
        "ENCERRADA": []
    }
```

**Testes (UNIT):**
```
☐ PENDENTE → ATIVA [válida]
☐ ATIVA → CANCELAMENTO_AGENDADO [válida]
☐ CANCELAMENTO_AGENDADO → ATIVA [válida - descancel]
☐ CANCELADA → ENCERRADA [válida]
☐ ATIVA → ENCERRADA [inválida - precisa CANCELADA]
```

---

#### 1.3 MaquinaEstadoPagamento
**Arquivo:** `services/billing_state_machines.py` (mesma classe)

**Classe:**
```python
class MaquinaEstadoPagamento:
    STATES = ["PENDENTE", "APROVADO", "RECUSADO", "ATRASADO",
              "REEMBOLSADO", "CONTESTADO", "RESOLVIDO"]
    
    TRANSICOES_VALIDAS = {
        "PENDENTE": ["APROVADO", "RECUSADO", "ATRASADO"],
        "APROVADO": ["REEMBOLSADO", "RESOLVIDO"],
        "RECUSADO": ["RESOLVIDO"],
        "ATRASADO": ["APROVADO", "RECUSADO"],
        "REEMBOLSADO": ["RESOLVIDO"],
        "CONTESTADO": ["RESOLVIDO"],
        "RESOLVIDO": []
    }
```

---

#### 1.4 MaquinaEstadoAcesso
**Arquivo:** `services/billing_state_machines.py` (mesma classe)

**Classe:**
```python
class MaquinaEstadoAcesso:
    STATES = ["LIBERADO", "RESTRITO", "SUSPENSO", "ENCERRADO"]
    
    TRANSICOES_VALIDAS = {
        "LIBERADO": ["RESTRITO", "SUSPENSO"],
        "RESTRITO": ["LIBERADO", "SUSPENSO"],
        "SUSPENSO": ["LIBERADO", "ENCERRADO"],
        "ENCERRADO": []
    }
```

---

#### 1.5 MaquinaEstadoRetencaoDados
**Arquivo:** `services/billing_state_machines.py` (mesma classe)

**Classe:**
```python
class MaquinaEstadoRetencaoDados:
    STATES = ["ATIVO", "EM_RETENCAO", "ELEGIVEL_EXCLUSAO", "EXCLUIDO"]
    
    TRANSICOES_VALIDAS = {
        "ATIVO": ["EM_RETENCAO"],
        "EM_RETENCAO": ["ELEGIVEL_EXCLUSAO"],
        "ELEGIVEL_EXCLUSAO": ["EXCLUIDO"],
        "EXCLUIDO": []
    }
```

---

### Checklist Fase 1

```
☐ services/trial_state_machine.py criado com TrialStateMachine
☐ services/billing_state_machines.py criado com 4 máquinas
☐ Testes unitários (mínimo 20 cases)
☐ Code review passou
☐ Todos os testes PASS
☐ Documentação de transições válidas
```

**Entrega:** Máquinas de estado validadas, prontas para usar em domínio.

---

## 🎯 FASE 2: TRIAL SERVICES (Dias 5-7)

### Objetivo
Implementar acompanhamento inteligente do trial com segmentação de perfis e relatório final.

### 2.1 TrialAcompanhamentoService

**Arquivo:** `services/trial_acompanhamento_service.py`

**Classe:**
```python
class TrialAcompanhamentoService:
    PERFIS = [
        "ONBOARDING_INCOMPLETO",
        "CONFIGURADO_SEM_MOVIMENTO",
        "MOVIMENTO_BLOQUEADO",
        "USO_SAUDAVEL",
        "USO_INTENSO"
    ]
    
    async def classificar_lead(tenant_id, user_id):
        # Analisar telemetria (mensagens, agendamentos, atividade)
        # Retornar: perfil + dados de suporte para ação
        pass
    
    async def acompanhamento_inteligente(tenant_id, user_id):
        # Publish trial_acompanhamento event
        # Determinar ação: check-in, open_door_message, aguardar
        pass
```

---

### 2.2 TrialReportService

**Arquivo:** `services/trial_report_service.py`

**Classe:**
```python
class TrialReportService:
    DIMENSOES = [
        "mensagensProcessadas",
        "agendamentosRealizados",
        "padrãoAtividade"
    ]
    
    async def gerar_relatorio_final(tenant_id, user_id):
        # Coletar métricas
        # Estruturar relatório com 3 dimensões
        # Retornar: {mensagens: X, agendamentos: Y, padrao: Z}
        pass
    
    async def obter_metricas_trial(tenant_id, user_id, data_inicio, data_fim):
        # Calcular: cliente_unicos, horarios_maior_volume, conversas_fora_horario
        pass
```

---

### 2.3 Eventos de Trial

**Publicar:**
```python
# trial_iniciado
event_bus.publish("trial_iniciado", {
    "tenant_id": tenant_id,
    "user_id": user_id,
    "data_inicio": now(),
    "data_expiracao": now() + duracao
})

# trial_expirado
event_bus.publish("trial_expirado", {
    "tenant_id": tenant_id,
    "user_id": user_id,
    "relatorio": {...}
})

# trial_convertido
event_bus.publish("trial_convertido", {
    "tenant_id": tenant_id,
    "user_id": user_id,
    "plano": plano_escolhido
})
```

---

### Checklist Fase 2

```
☐ TrialAcompanhamentoService implementado (5 perfis)
☐ TrialReportService implementado (3 dimensões)
☐ Eventos publicados (trial_iniciado, trial_expirado, trial_convertido)
☐ Testes de segmentação (UNIT)
☐ Testes de relatório (INTEGRATION)
☐ Code review passou
```

**Entrega:** Trial pode ser monitorado e acompanhado com dados reais.

---

## 🎯 FASE 3: BILLING DOMAIN SERVICE (Dias 8-11)

### Objetivo
Implementar serviço de domínio que orquestra processamento de webhooks com máquinas de estado.

### 3.1 BillingDomainService

**Arquivo:** `services/billing_domain_service.py`

**Classe:**
```python
class BillingDomainService:
    def __init__(self, tenant_id, user_id):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.firestore = get_db()
    
    async def processar_evento(self, evento):
        """
        1. Validar evento
        2. Verificar idempotência
        3. Carregar estado atual
        4. Aplicar máquina de estados
        5. Persistir com transação
        6. Registrar auditoria
        7. Publicar eventos internos
        """
        # 1. Validar
        self._validar_evento(evento)
        
        # 2. Verificar idempotência
        if await self._evento_processado(evento):
            return {"status": "already_processed"}
        
        # 3. Carregar estado
        estado_atual = await self._carregar_estado()
        
        # 4. Aplicar transição
        transicao = self._aplicar_transicao(estado_atual, evento)
        
        # 5. Persistir com transação
        async with self.firestore.transaction() as txn:
            txn.update_doc(assinatura_path, transicao.novo_estado)
            txn.set_doc(idempotencia_path, {...})
        
        # 6. Auditoria
        await self._registrar_auditoria(evento, transicao)
        
        # 7. Eventos internos
        await self._publicar_eventos_internos(transicao)
        
        return {"status": "success"}
    
    def _validar_evento(self, evento) -> bool
    async def _evento_processado(self, evento) -> bool
    async def _carregar_estado(self) -> dict
    def _aplicar_transicao(self, estado, evento) -> Transicao
    async def _registrar_auditoria(self, evento, transicao)
    async def _publicar_eventos_internos(self, transicao)
```

---

### 3.2 Estrutura de Transição

```python
@dataclass
class Transicao:
    estado_anterior: dict
    novo_estado: dict
    eventos_internos: list
    mudancas_firestore: dict
```

---

### Checklist Fase 3

```
☐ BillingDomainService implementado
☐ Método processar_evento() com 7 passos
☐ Métodos auxiliares (_validar, _evento_processado, etc)
☐ Testes unitários de cada método
☐ Testes de integração (com máquinas de estado)
☐ Transações Firestore garantidas
☐ Code review passou
```

**Entrega:** Webhook pode ser processado com garantias de consistência.

---

## 🎯 FASE 4: WEBHOOK HANDLER (Dias 12-15)

### Objetivo
Implementar recepção de webhooks Hotmart e adaptação para domínio.

### 4.1 HotmartWebhookAdapter

**Arquivo:** `adapters/hotmart_adapter.py`

**Classe:**
```python
class HotmartWebhookAdapter:
    def __init__(self, payload: dict):
        self.payload = payload
        self.evento = self._extrair_evento()
        self.tenant_id = self._extrair_tenant()
        self.user_id = self._extrair_usuario()
    
    def _extrair_evento(self) -> dict:
        # Extrair evento de payload Hotmart
        # Mapear: payment_approved → estrutura interna
        pass
    
    def _extrair_tenant(self) -> str:
        # Extrair tenant_id de payload
        pass
    
    def _extrair_usuario(self) -> str:
        # Extrair user_id de payload
        pass
    
    async def processar(self):
        domain_service = BillingDomainService(self.tenant_id, self.user_id)
        return await domain_service.processar_evento(self.evento)
```

---

### 4.2 WebhookHandler

**Arquivo:** `handlers/webhook_handler.py`

**Função:**
```python
@router.post("/webhooks/hotmart")
async def receber_webhook_hotmart(payload: dict, request: Request):
    # 1. Validar autenticação
    validar_assinatura_hotmart(payload, request.headers)
    
    # 2. Converter para adapter
    adapter = HotmartWebhookAdapter(payload)
    
    # 3. Processar
    resultado = await adapter.processar()
    
    # 4. Retornar 200 OK (acknowledgment)
    return {"status": "accepted"}
```

---

### Checklist Fase 4

```
☐ HotmartWebhookAdapter implementado
☐ WebhookHandler endpoint criado
☐ Validação de assinatura Hotmart
☐ Testes de transformação de payload (UNIT)
☐ Testes E2E webhook (INTEGRATION)
☐ Logging e monitoramento
☐ Code review passou
```

**Entrega:** Webhooks Hotmart podem ser recebidos e processados.

---

## 🎯 FASE 5: IDEMPOTÊNCIA WEBHOOK (Dias 16-17)

### Objetivo
Garantir que webhook duplicado seja processado apenas 1x.

### 5.1 WebhookIdempotenciaService

**Arquivo:** `services/webhook_idempotencia_service.py`

**Classe:**
```python
class WebhookIdempotenciaService:
    async def marcar_processado(provider_event_id, payload_hash):
        path = f"processed_webhook_events/{provider_event_id}"
        await firestore.set(path, {
            "provider_event_id": provider_event_id,
            "provider": "hotmart",
            "processed_at": now(),
            "payload_hash": payload_hash,
            "status": "success"
        })
    
    async def foi_processado(provider_event_id) -> bool:
        doc = await firestore.get(f"processed_webhook_events/{provider_event_id}")
        return doc is not None
```

---

### 5.2 Schema Firestore

```
processed_webhook_events/
├─ {provider_event_id}/
│  ├─ provider: "hotmart"
│  ├─ provider_event_id: "..."
│  ├─ provider_transaction_id: "..."
│  ├─ provider_subscription_id: "..."
│  ├─ payload_hash: "sha256(...)"
│  ├─ processed_at: timestamp
│  └─ status: "success" | "failed"
```

---

### Checklist Fase 5

```
☐ WebhookIdempotenciaService implementado
☐ Coleção processed_webhook_events criada
☐ provider_event_id como chave primária
☐ payload_hash para detecção de duplicação
☐ Testes de duplicação (UNIT)
☐ Código review passou
```

**Entrega:** Webhook duplicado = processado 1x (garantido).

---

## 🎯 FASE 6: VALIDAÇÃO SANDBOX (Dias 18-24)

### Objetivo
Executar VALIDACAO_HOTMART.md em Sandbox para validar todas as implementações.

### 6.1 Testes Críticos

```
TESTE 2: Criar Assinatura Teste (Lead→Trial→Compra)
TESTE 3: Webhook payment_approved (BillingDomainService)
TESTE 10: Duplicar webhook (Idempotência)
TESTE 14: Reconciliação Manual (Auditoria)
TESTE 15: Renovação Automática (Ciclo contínuo)
```

### 6.2 Checklist

```
☐ Todos 18 testes de VALIDACAO_HOTMART.md executados
☐ 17/18 passando em Sandbox
☐ Documentação de cada teste atualizada
☐ Problemas reportados e corrigidos
☐ Produção: subset crítico validado
```

**Entrega:** Sistema pronto para produção.

---

## 📊 TIMELINE VISUAL

```
SEMANA 1
├─ Dia 1-4: Phase 1 (State Machines)
├─ Dia 5-7: Phase 2 (Trial Services)
└─ (4 dias slack para code review)

SEMANA 2
├─ Dia 8-11: Phase 3 (BillingDomainService)
├─ Dia 12-15: Phase 4 (Webhook Handler)
└─ (1 dia slack)

SEMANA 3
├─ Dia 16-17: Phase 5 (Idempotência)
├─ Dia 18-21: Phase 6 (Sandbox Testing)
├─ Dia 22-24: Correções + Produção
└─ (buffer)

TOTAL: 17-24 dias (3-4 semanas)
```

---

## 🎯 CRITÉRIOS DE SUCESSO

```
Fase 1: 100% testes unitários PASS
Fase 2: 5 perfis classificando corretamente + relatório completo
Fase 3: BillingDomainService processando eventos + auditoria
Fase 4: Webhook recebido e transformado corretamente
Fase 5: Webhook duplicado detectado e rejeitado
Fase 6: 17/18 testes VALIDACAO_HOTMART PASS em Sandbox
```

---

## 🚀 PRÓXIMOS PASSOS

1. ✅ Auditoria completa (HOJE)
2. ⏳ Aprovação de plano (amanhã)
3. ⏳ Sprint planning (Fase 1)
4. ⏳ Implementação (17-24 dias)
5. ⏳ Sandbox testing (VALIDACAO_HOTMART.md)
6. ⏳ Produção

---

**PLANO_IMPLEMENTACAO_CONTRATOS_2026_07_27.md** — Roteiro detalhado  
**Status:** Pronto para execução  
**Próximo:** Aprovação e início Fase 1

