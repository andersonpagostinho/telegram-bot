# Guia de Configuração Firebase para Ambiente Local

**Data:** 2026-06-21  
**Versão:** 1.0  
**Escopo:** Desenvolvimento local, testes, ambiente de homologação  

---

## 📋 4 Estratégias Suportadas

O `services/firestore_client.py` tenta as estratégias em ordem:

```
1. firebaseConfig.json (arquivo local na raiz)
2. FIREBASE_CREDENTIALS (variável ambiente com JSON completo)
3. GOOGLE_APPLICATION_CREDENTIALS (variável ambiente com caminho)
4. Application Default Credentials (GCP - fora de escopo local)
```

---

## ✅ Solução Recomendada: GOOGLE_APPLICATION_CREDENTIALS

**Por que:** Simples, confiável, suportado por Google Cloud SDK

### Windows PowerShell

```powershell
# 1. Obtém credenciais do Firebase (JSON)
# Faça download em: https://console.firebase.google.com/ → Projeto → Configurações → Contas de Serviço → Gerar Chave Privada

# 2. Configure a variável de ambiente (temporária, apenas sessão atual)
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\Users\ANDERSON\caminho\para\firebaseConfig.json"

# 3. Verifique se foi configurada
$env:GOOGLE_APPLICATION_CREDENTIALS

# 4. Rode os testes
python tests/validacao_firebase_auth.py

# RESULTADO ESPERADO:
# [OK] Firebase inicializado com GOOGLE_APPLICATION_CREDENTIALS
# [OK] Conseguiu listar coleções
```

### Windows PowerShell (Permanente)

Para manter a variável entre sessões:

```powershell
# 1. Abra PowerShell como Administrador

# 2. Configure a variável permanentemente
[Environment]::SetEnvironmentVariable("GOOGLE_APPLICATION_CREDENTIALS", "C:\Users\ANDERSON\caminho\para\firebaseConfig.json", "User")

# 3. Feche e reabra PowerShell

# 4. Verifique
$env:GOOGLE_APPLICATION_CREDENTIALS

# Agora permanece mesmo após reinicializar
```

### Git Bash (Windows)

```bash
# 1. Obtém credenciais do Firebase (JSON)

# 2. Configure a variável (temporária)
export GOOGLE_APPLICATION_CREDENTIALS="/c/Users/ANDERSON/caminho/para/firebaseConfig.json"

# 3. Verifique
echo $GOOGLE_APPLICATION_CREDENTIALS

# 4. Rode os testes
python tests/validacao_firebase_auth.py

# Para PERMANENTE, adicione ao ~/.bashrc
echo 'export GOOGLE_APPLICATION_CREDENTIALS="/c/Users/ANDERSON/caminho/para/firebaseConfig.json"' >> ~/.bashrc
source ~/.bashrc
```

---

## 🔄 Alternativa: firebaseConfig.json Local

Se preferir usar arquivo local:

```
NeoEve - Empresarial/
├── firebaseConfig.json ← aqui (raiz do projeto)
├── services/
├── tests/
├── docs/
└── ...
```

### Passos

1. Obtém credenciais do Firebase:
   - Firebase Console → Seu Projeto → ⚙️ Configurações
   - Guia "Contas de Serviço"
   - Botão "Gerar Nova Chave Privada"
   - Salve como `firebaseConfig.json` na raiz

2. Teste:
   ```bash
   python tests/validacao_firebase_auth.py
   
   # RESULTADO ESPERADO:
   # [OK] Firebase inicializado com credenciais locais: .../firebaseConfig.json
   ```

### ⚠️ Segurança

**NUNCA faça commit de `firebaseConfig.json` para Git!**

```bash
# Adicione ao .gitignore
echo "firebaseConfig.json" >> .gitignore
```

---

## 🧪 Validação

### Teste Simples

```bash
python tests/validacao_firebase_auth.py
```

### Resultado Esperado

```
[TESTE 1] Estratégias de autenticação disponíveis...
[TESTE 2] Verificar firebaseConfig.json...
[TESTE 3] Verificar FIREBASE_CREDENTIALS (env var)...
[TESTE 4] Verificar GOOGLE_APPLICATION_CREDENTIALS (env var)...
[TESTE 5] Tentar inicializar get_db()...
  [OK] get_db() retornou cliente Firestore
[TESTE 6] Teste mínimo: listar coleções...
  [OK] Conseguiu listar coleções (total: X)

[SUCESSO] Firebase autenticado e funcional!
```

### Resultado com Erro

```
[ERRO] Falha ao inicializar Firebase: Your default credentials were not found

[FALHA] Firebase não autenticado

Solução:
1. Verifique firebaseConfig.json ou GOOGLE_APPLICATION_CREDENTIALS
2. Windows PowerShell: $env:GOOGLE_APPLICATION_CREDENTIALS='C:\caminho\firebaseConfig.json'
```

---

## 🔀 Hierarquia de Precedência

Se múltiplas estratégias forem encontradas, o `firestore_client.py` usa a primeira que funcionar:

```
firebaseConfig.json (estratégia 1)
    ↓ (se falhar)
FIREBASE_CREDENTIALS (estratégia 2)
    ↓ (se falhar)
GOOGLE_APPLICATION_CREDENTIALS (estratégia 3)
    ↓ (se falhar)
Application Default Credentials (estratégia 4)
```

**Recomendação:** Use apenas uma estratégia por ambiente para evitar confusão.

---

## 🚨 Troubleshooting

### Erro: "Your default credentials were not found"

**Causa:** Nenhuma estratégia funcionou

**Solução:**
1. Verifique se `firebaseConfig.json` existe na raiz
2. OU configure `GOOGLE_APPLICATION_CREDENTIALS`
3. Reexecute `validacao_firebase_auth.py`

### Erro: "FIREBASE_CREDENTIALS JSON inválido"

**Causa:** Variável de ambiente truncada ou malformada

**Solução:**
1. Verifique tamanho: `$env:GOOGLE_APPLICATION_CREDENTIALS.Length` (deve ser >500 chars)
2. Se muito curto, use `GOOGLE_APPLICATION_CREDENTIALS` ao invés
3. Ou limpe e reconfigure:
   ```powershell
   Remove-Item Env:\FIREBASE_CREDENTIALS
   ```

### Erro: "JSON válido mas falta campo 'type'"

**Causa:** Arquivo de credenciais inválido

**Solução:**
1. Baixe novas credenciais do Firebase Console
2. Certifique-se que é do tipo "Conta de Serviço" (service account), não outro tipo

### Erro: "Arquivo não existe"

**Causa:** `GOOGLE_APPLICATION_CREDENTIALS` aponta para arquivo inexistente

**Solução:**
1. Verifique o caminho: `Test-Path "C:\caminho\para\arquivo"`
2. Use caminho absoluto completo, não relativo
3. Escape barras invertidas: `C:\\Users\\ANDERSON\\arquivo.json`

---

## 🎯 Fluxo Recomendado para Novo Developer

1. **Obter credenciais:**
   - Firebase Console → Seu Projeto → ⚙️ Configurações → Contas de Serviço → Gerar Chave
   - Salve em local seguro (ex: `~/Firebase/firebaseConfig-dev.json`)

2. **Configurar uma única estratégia:**
   - **Recomendado:** GOOGLE_APPLICATION_CREDENTIALS
   - Alternativa: firebaseConfig.json na raiz (com `.gitignore`)

3. **Teste:**
   ```bash
   python tests/validacao_firebase_auth.py
   ```

4. **Se passar:**
   ```bash
   python -m pytest tests/runner_p1_identidade_canal_onboarding.py -v
   # Esperado: 9/9 PASS
   
   python -m pytest tests/runner_p0_regressao_completa.py -v
   # Esperado: 174/174 PASS
   ```

---

## 📚 Referências

- Firebase Admin SDK Python: https://firebase.google.com/docs/database/admin/start?hl=pt
- Google Cloud Authentication: https://cloud.google.com/docs/authentication/application-default-credentials
- firestore_client.py: `services/firestore_client.py`
- Teste de validação: `tests/validacao_firebase_auth.py`

---

## ✅ Checklist

- [ ] Credenciais obtidas do Firebase Console
- [ ] GOOGLE_APPLICATION_CREDENTIALS configurada OU firebaseConfig.json na raiz
- [ ] `validacao_firebase_auth.py` passou com sucesso
- [ ] `runner_p1_identidade_canal_onboarding.py` (9/9 esperado)
- [ ] `runner_p0_regressao_completa.py` (174/174 esperado)

---

**Última atualização:** 2026-06-21  
**Autor:** Claude Code  
**Status:** Publicado
