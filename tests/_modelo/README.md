# 🧪 Testes Modelo — Referência Obrigatória

## ⚠️ REGRA DE OURO

**TODOS os testes E2E devem ser criados EXATAMENTE como o modelo abaixo.**

Testes que não seguem este padrão **NÃO VALEM** e serão recusados.

---

## 📋 Características Obrigatórias do Modelo

### ✅ O que é OBRIGATÓRIO:

1. **Firebase REAL** — não mockar Firestore
2. **Webhook REAL** — usar Flask `/webhook/whatsapp` endpoint
3. **Cliente REAL** — usar cliente com histórico em Firestore (exemplo: `5511991382080`)
4. **Contexto Anterior INTACTO** — não limpar context, deixar como está
5. **Patch HMAC** — `with patch("main.validate_whatsapp_signature", return_value=True)`
6. **Fluxo Completo** — 3 mensagens (ou as necessárias) via webhook até o erro/resultado final
7. **Validação Documentada** — print dos passos esperados
8. **Async/Await Correto** — usar `asyncio` adequadamente dentro de pytest asyncio

---

## 📖 Arquivo Modelo

**`test_e2e_webhook_modelo.py`**

Este arquivo é o **ÚNICO** padrão aceitável para testes E2E.

Qualquer novo teste E2E deve:
- Copiar esse arquivo
- Adaptar mensagens/cliente conforme necessário
- **MANTER a estrutura idêntica**
- **MANTER o Firebase REAL**
- **MANTER o webhook REAL**

---

## ❌ O que NÃO é Permitido:

- ❌ Mock do Firestore
- ❌ Mock do webhook
- ❌ Limpar contexto anterior
- ❌ Chamar handler diretamente (sem passar por Flask)
- ❌ Usar testes unitários para validar fluxo completo
- ❌ Usar `unittest.mock` para simular comportamento real
- ❌ Tests que não vão até o final do fluxo

---

## 🔄 Como Usar o Modelo

### Para criar novo teste E2E:

```bash
# 1. Copie o modelo
cp tests/_modelo/test_e2e_webhook_modelo.py tests/test_seu_novo_teste.py

# 2. Edite APENAS:
#    - Nome da função
#    - Mensagens a testar
#    - Cliente (se necessário)
#    - Validações finais

# 3. Mantenha INTACTO:
#    - Firebase REAL
#    - Webhook REAL
#    - Patch HMAC
#    - Estrutura async/await
```

---

## 📊 Checklist de Validação

Antes de considerar um teste "PRONTO":

- [ ] Usa Firebase REAL (não mocka Firestore)
- [ ] Usa `/webhook/whatsapp` endpoint (Flask)
- [ ] Cliente tem histórico em Firestore
- [ ] Não limpa contexto anterior
- [ ] Patch HMAC está presente
- [ ] Fluxo vai até o fim (erro/resultado)
- [ ] Validações estão documentadas com print
- [ ] Async/await está correto
- [ ] Teste passa/falha conforme esperado
- [ ] Segue estrutura do modelo exatamente

---

## 💡 Por que este padrão?

O padrão modelo garante que:

1. **Erros REAIS são reproduzidos** — não mascaram problemas com mock
2. **Contexto REAL é carregado** — reproduz fluxo do usuário fielmente
3. **Firebase REAL é validado** — vê dados tal como estão
4. **Webhook REAL é testado** — passa por todas as camadas Flask
5. **Integração E2E é completa** — do webhook até Firestore

Qualquer desvio deste padrão = **teste inválido**.

---

**Criado:** 2026-10-19
**Status:** OBRIGATÓRIO
**Versão:** 1.0
