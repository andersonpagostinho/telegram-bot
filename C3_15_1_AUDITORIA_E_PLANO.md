# C3.15.1 — PREPARAÇÃO & SCHEMA

**Status:** Auditoria Pré-Execução + Plano Detalhado  
**Data:** 2026-09-26  
**Escopo:** Preparar infraestrutura SOMENTE (sem alterar comportamento)  
**Objetivo:** Path novo isolado por actor_id  

---

## PARTE 1: AUDITORIA DO ESTADO ATUAL

### 1.1 Código Existente — Onboarding

**Arquivos Atualmente Envolvidos:**

```
services/
  ├─ onboarding_dono_service.py      (11.2 KB, criado 30-jun-2024)
  └─ onboarding_service.py            (11.6 KB, criado 30-jun-2024)

router/
  └─ integracao_identidade_onboarding.py

tests/
  ├─ runner_p1_identidade_canal_onboarding.py
  ├─ test_c312_novo_dono_onboarding_firebase_real.py
  ├─ p1_e2e_onboarding_*.py
  └─ runner_onboarding_endereco_dono.py
```

### 1.2 Firestore Atual

**Path Existente (Legacy):**
```
Clientes/{tenant_id}/Configuracao/negocio
```

**Verificação:** ✅ Caminho novo "Donos/" NÃO existe no código  
**Verificação:** ✅ Nenhum conflito estrutural esperado

### 1.3 Comportamento Existente — DEVE PERMANECER INALTERADO

- ✅ onboarding_dono_service continua funcional
- ✅ Fluxo WhatsApp continua idêntico
- ✅ principal_router não alterado
- ✅ integracao_identidade_onboarding mantém comportamento
- ✅ onboarding_service continua processando mensagens
- ✅ Tenant 7394370553 permanece intacto

---

## PARTE 2: PLANO DE ARQUIVOS EM C3.15.1

### Arquivos a CRIAR

| Arquivo | Tipo | Responsabilidade | Linhas | Fundação |
|---------|------|-----------------|--------|----------|
| `services/onboarding_isolado_schema.py` | Service | Defini schema, helpers para novo path | ~150 | Firestore helpers |
| `tests/test_c315_1_schema_isolado.py` | Test | Validar novo path, isolamento, schema | ~200 | Firestore real |

### Arquivos a MANTER (ZERO ALTERAÇÃO)

| Arquivo | Razão |
|---------|-------|
| `services/onboarding_dono_service.py` | Será alterado em C3.15.2+ |
| `services/onboarding_service.py` | Será alterado em C3.15.4+ |
| `router/integracao_identidade_onboarding.py` | Será alterado em C3.15.5+ |
| `main.py` | Sem alteração |
| `router/principal_router.py` | Sem alteração |

### Arquivos a CONSULTAR (LEITURA APENAS)

| Arquivo | Propósito |
|---------|-----------|
| `services/firebase_service_async.py` | Entender padrão de leitura/escrita Firestore |
| `services/firestore_client.py` | Entender cliente Firestore |
| Todos callsites atuais | Confirmar que não há early adoption da nova path |

---

## PARTE 3: ESPECIFICAÇÃO DO NOVO SCHEMA

### Path Canônico

```
Clientes/{tenant_id}/Donos/{actor_id}/onboarding/ativo
```

**Estrutura:**
- `Clientes` = coleção de tenants
- `{tenant_id}` = document de tenant
- `Donos` = subcoleção (novo)
- `{actor_id}` = document de ator específico (novo)
- `onboarding` = subcoleção (novo)
- `ativo` = document único por ator (novo)

### Document Schema Mínimo

```python
{
    # Identidade
    "tenant_id": str,           # Redundante no path, mas necessário para query
    "actor_id": str,            # Redundante no path, mas necessário para validação
    
    # Estado de Onboarding
    "onboarding_status": str,   # "em_progresso" | "completo" | "parado"
    "onboarding_etapa_atual": str,  # "nome_negocio" | "segmento" | ...
    "onboarding_indice": int,   # 0-11, índice na sequência
    
    # Rastreabilidade
    "criado_em": str,           # ISO 8601 timestamp
    "criado_por": str,          # actor_id que criou
    "atualizado_em": str,       # ISO 8601 timestamp (updated every write)
    
    # Placeholder para campos de coleta
    "nome_negocio": str | None,
    "segmento": str | None,
    "endereco": str | None,
    "agenda_padrao": str | None,
    # ... etc (11 campos totais previstos)
}
```

### Validações do Schema

1. ✅ `tenant_id` ≠ vazio
2. ✅ `actor_id` ≠ vazio e normalizado (phone)
3. ✅ `onboarding_status` ∈ ["em_progresso", "completo", "parado"]
4. ✅ `onboarding_etapa_atual` ∈ ETAPAS_ONBOARDING
5. ✅ `onboarding_indice` ≥ 0 and ≤ 11
6. ✅ `criado_em` é timestamp válido ISO 8601
7. ✅ `atualizado_em` ≥ `criado_em`

---

## PARTE 4: HELPERS E UTILITÁRIOS (A CRIAR)

### Arquivo: services/onboarding_isolado_schema.py

**Responsabilidades:**
1. Constructores de document
2. Validadores de schema
3. Query builders (para C3.15+, mas definir interface)
4. Converter de legacy para novo (para C3.15.6)

**Funções Principais:**

```python
# 1. Constructor
def criar_documento_onboarding_novo(
    tenant_id: str,
    actor_id: str,
    dono_nome: str,
    dono_email: str,
    etapa_inicial: str = "nome_negocio"
) -> dict:
    """Cria novo documento para path Donos/{actor_id}/onboarding/ativo"""
    
    return {
        "tenant_id": tenant_id,
        "actor_id": actor_id,
        "onboarding_status": "em_progresso",
        "onboarding_etapa_atual": etapa_inicial,
        "onboarding_indice": 0,
        "criado_em": datetime.now(pytz.UTC).isoformat(),
        "criado_por": actor_id,
        "atualizado_em": datetime.now(pytz.UTC).isoformat(),
        "dono_nome": dono_nome,
        "dono_email": dono_email,
        "nome_negocio": None,
        "segmento": None,
        "endereco": None,
        "agenda_padrao": None,
        "primeiro_profissional": None,
        "canal_primeiro_profissional": None,
        "primeiro_servico": None,
        "duracao_primeiro_servico": None,
    }

# 2. Validator
def validar_documento_onboarding(doc: dict) -> tuple[bool, str]:
    """
    Valida documento contra schema.
    Retorna (valido: bool, motivo: str)
    """
    
    campos_obrigatorios = [
        "tenant_id", "actor_id", "onboarding_status",
        "onboarding_etapa_atual", "onboarding_indice",
        "criado_em", "criado_por", "atualizado_em"
    ]
    
    for campo in campos_obrigatorios:
        if campo not in doc:
            return False, f"Campo obrigatório faltando: {campo}"
    
    # Validar tipos
    if not isinstance(doc["tenant_id"], str) or not doc["tenant_id"]:
        return False, "tenant_id deve ser string não-vazia"
    
    if not isinstance(doc["actor_id"], str) or not doc["actor_id"]:
        return False, "actor_id deve ser string não-vazia"
    
    if doc["onboarding_status"] not in ["em_progresso", "completo", "parado"]:
        return False, f"onboarding_status inválido: {doc['onboarding_status']}"
    
    if not isinstance(doc["onboarding_indice"], int):
        return False, "onboarding_indice deve ser inteiro"
    
    if not (0 <= doc["onboarding_indice"] <= 11):
        return False, f"onboarding_indice fora do intervalo: {doc['onboarding_indice']}"
    
    # Validar timestamps
    try:
        datetime.fromisoformat(doc["criado_em"].replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return False, "criado_em não é timestamp ISO 8601 válido"
    
    return True, "OK"

# 3. Path builder (referência apenas, não usar em C3.15.1)
def obter_ref_onboarding_novo(
    db,  # Firestore client
    tenant_id: str,
    actor_id: str
):
    """Retorna referência do documento novo"""
    return (
        db.collection("Clientes").document(tenant_id)
        .collection("Donos").document(actor_id)
        .collection("onboarding").document("ativo")
    )

# 4. Converter (para C3.15.6, mas interface definida agora)
def converter_legacy_para_isolado(
    legacy_doc: dict,
    tenant_id: str,
    actor_id: str
) -> dict:
    """Converte documento legacy para novo formato"""
    
    # Verificar ownership
    if legacy_doc.get("dono_actor_id") != actor_id:
        raise ValueError("Legacy não pertence a este ator")
    
    # Copiar campos relevantes
    novo_doc = criar_documento_onboarding_novo(
        tenant_id=tenant_id,
        actor_id=actor_id,
        dono_nome=legacy_doc.get("dono_nome", ""),
        dono_email=legacy_doc.get("dono_email", ""),
        etapa_inicial=legacy_doc.get("onboarding_etapa_atual", "nome_negocio")
    )
    
    # Sobrescrever com dados do legacy
    novo_doc.update({
        "onboarding_status": legacy_doc.get("onboarding_status", "em_progresso"),
        "onboarding_indice": legacy_doc.get("onboarding_indice", 0),
        "criado_em": legacy_doc.get("criado_em", novo_doc["criado_em"]),
        "criado_por": legacy_doc.get("criado_por", actor_id),
        "atualizado_em": legacy_doc.get("atualizado_em", novo_doc["atualizado_em"]),
        "nome_negocio": legacy_doc.get("nome_negocio"),
        "segmento": legacy_doc.get("segmento"),
        "endereco": legacy_doc.get("endereco"),
        "agenda_padrao": legacy_doc.get("agenda_padrao"),
        "primeiro_profissional": legacy_doc.get("primeiro_profissional"),
        "canal_primeiro_profissional": legacy_doc.get("canal_primeiro_profissional"),
        "primeiro_servico": legacy_doc.get("primeiro_servico"),
        "duracao_primeiro_servico": legacy_doc.get("duracao_primeiro_servico"),
        "migrado_de_legacy": True,
        "migrado_em": datetime.now(pytz.UTC).isoformat()
    })
    
    return novo_doc
```

---

## PARTE 5: TESTES C3.15.1

### Arquivo: tests/test_c315_1_schema_isolado.py

**Testes a Implementar:**

```python
# T1: Construção Correta do Path
def test_path_construction():
    """Verifica que path novo é construído corretamente"""
    tenant_id = "7394370553"
    actor_id = "5521987654321"
    # Não escrever, apenas construir referência
    doc_ref = obter_ref_onboarding_novo(db, tenant_id, actor_id)
    # Verificar path
    assert "Clientes/7394370553/Donos/5521987654321/onboarding/ativo" in str(doc_ref.path)

# T2: Isolamento de Actor A/B
def test_actor_isolation():
    """Verifica que actor A não acessa documento de actor B"""
    tenant_id = "test_tenant_001"
    actor_a = "5521111111111"
    actor_b = "5522222222222"
    
    doc_a = criar_documento_onboarding_novo(tenant_id, actor_a, "Dono A", "a@...")
    doc_b = criar_documento_onboarding_novo(tenant_id, actor_b, "Dono B", "b@...")
    
    # Verificar que não são o mesmo documento
    assert doc_a.get("actor_id") != doc_b.get("actor_id")
    assert doc_a != doc_b

# T3: Isolamento Tenant
def test_tenant_isolation():
    """Verifica que mesmo actor em tenants diferentes = documentos diferentes"""
    actor_id = "5521987654321"
    tenant_1 = "tenant_1"
    tenant_2 = "tenant_2"
    
    doc_1 = criar_documento_onboarding_novo(tenant_1, actor_id, "Dono", "d@...")
    doc_2 = criar_documento_onboarding_novo(tenant_2, actor_id, "Dono", "d@...")
    
    assert doc_1.get("tenant_id") != doc_2.get("tenant_id")
    # Paths são diferentes
    ref_1 = obter_ref_onboarding_novo(db, tenant_1, actor_id)
    ref_2 = obter_ref_onboarding_novo(db, tenant_2, actor_id)
    assert str(ref_1.path) != str(ref_2.path)

# T4: Schema Mínimo
def test_schema_minimo():
    """Verifica que documento tem todos os campos mínimos"""
    tenant_id = "test_tenant"
    actor_id = "test_actor"
    
    doc = criar_documento_onboarding_novo(tenant_id, actor_id, "Nome", "email@...")
    
    campos_obrigatorios = [
        "tenant_id", "actor_id",
        "onboarding_status", "onboarding_etapa_atual", "onboarding_indice",
        "criado_em", "criado_por", "atualizado_em"
    ]
    
    for campo in campos_obrigatorios:
        assert campo in doc, f"Campo faltando: {campo}"
        assert doc[campo] is not None, f"Campo vazio: {campo}"

# T5: Validação de Schema
def test_validacao_schema():
    """Verifica que validador rejeita documentos inválidos"""
    
    # Documento válido
    doc_valido = criar_documento_onboarding_novo("t1", "a1", "N", "e@...")
    valido, motivo = validar_documento_onboarding(doc_valido)
    assert valido, f"Documento válido foi rejeitado: {motivo}"
    
    # Documento inválido (falta tenant_id)
    doc_invalido = doc_valido.copy()
    del doc_invalido["tenant_id"]
    valido, motivo = validar_documento_onboarding(doc_invalido)
    assert not valido, "Documento sem tenant_id deveria ser rejeitado"

# T6: Conversão Legacy → Novo
def test_converter_legacy_para_isolado():
    """Verifica conversão de documento legacy"""
    
    legacy_doc = {
        "dono_actor_id": "5521987654321",
        "dono_nome": "Maria",
        "dono_email": "maria@...",
        "onboarding_status": "em_progresso",
        "onboarding_etapa_atual": "segmento",
        "onboarding_indice": 1,
        "criado_em": "2026-09-26T10:00:00Z",
        "criado_por": "5521987654321",
        "atualizado_em": "2026-09-26T11:00:00Z",
        "nome_negocio": None,
        "segmento": "Salão"
    }
    
    novo_doc = converter_legacy_para_isolado(legacy_doc, "tenant_1", "5521987654321")
    
    # Verificar que dados foram copiados
    assert novo_doc.get("dono_nome") == "Maria"
    assert novo_doc.get("segmento") == "Salão"
    assert novo_doc.get("onboarding_etapa_atual") == "segmento"
    assert novo_doc.get("migrado_de_legacy") == True

# T7: Firestore Real — Escrita/Leitura (sem afetar prod)
@pytest.mark.firestore_real
def test_firestore_write_read_isolado():
    """Testa escrita e leitura no caminho novo usando Firestore REAL"""
    
    # Usar tenant de teste (não prod)
    tenant_id = "test_c315_1_" + str(int(time.time()))
    actor_id = "test_actor_" + str(int(time.time()))
    
    doc = criar_documento_onboarding_novo(tenant_id, actor_id, "Teste", "test@...")
    
    # Escrever
    ref = obter_ref_onboarding_novo(db, tenant_id, actor_id)
    ref.set(doc)
    
    # Ler
    lido = ref.get()
    assert lido.exists, "Documento não foi escrito"
    
    # Validar
    dados_lidos = lido.to_dict()
    assert dados_lidos.get("actor_id") == actor_id
    assert dados_lidos.get("tenant_id") == tenant_id
    
    # Cleanup (deletar documento de teste)
    ref.delete()
    
    # Verificar que foi deletado
    assert not ref.get().exists, "Cleanup falhou"
```

---

## PARTE 6: VALIDAÇÕES DE SEGURANÇA

### ✅ Tenant 7394370553 — Confirmação

**Verificação Pré-Execução:**
```
Tenant 7394370553:
  - Documentos atuais não serão tocados
  - Novo path Donos/ será criado vazio
  - Nenhuma cópia de dados
  - Nenhuma alteração em Configuracao/negocio
```

---

## PARTE 7: EXECUÇÃO E CHECKLIST

### Checklist Pré-Execução

- [ ] Auditar código atual (feito)
- [ ] Confirmar sem conflitos de path (feito)
- [ ] Planejar arquivos a criar (feito)
- [ ] Especificar schema (feito)
- [ ] Definir helpers (feito)
- [ ] Definir testes (feito)
- [ ] Aprovação para criar arquivos

### Checklist Pós-Execução

- [ ] Arquivo `services/onboarding_isolado_schema.py` criado
- [ ] Arquivo `tests/test_c315_1_schema_isolado.py` criado
- [ ] Todos os 7 testes passam
- [ ] Firestore de produção intacto
- [ ] Tenant 7394370553 intacto
- [ ] Nenhum arquivo antigo modificado
- [ ] Diff review
- [ ] Nenhum commit feito

---

## PARTE 8: RISCOS E MITIGAÇÃO

| Risco | Mitigação |
|-------|-----------|
| Schema inconsistente com C3.15 | Seguir exatamente spec do C3.15 |
| Path já existe em Firestore | Verificação inicial confirmou não existe |
| Teste apaga dados produção | Testes usam tenant de teste, cleanup automático |
| Arquivo criado com responsabilidade ampla | Single responsibility: helpers de schema |

---

## RESULTADO ESPERADO

Ao final de C3.15.1:

✅ 2 arquivos novos criados  
✅ 7 testes Firestore real passando  
✅ Schema validado  
✅ Helpers funcionando  
✅ Conversão de legacy planejada (interface definida)  
✅ Zero alterações ao comportamento atual  
✅ Zero alterações ao Firestore produção  
✅ Pronto para C3.15.2 (Leitura)

---

**Próximo Passo:** Executar C3.15.1 conforme plano acima.
