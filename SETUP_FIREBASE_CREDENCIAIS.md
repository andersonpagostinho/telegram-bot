# Setup: Credenciais Firebase

**Status:** Aguardando credenciais do Firebase Console

---

## 📋 O que fazer

### Passo 1: Gerar Chave Privada no Firebase Console

1. Abra: https://console.firebase.google.com/
2. Selecione seu projeto NeoEve
3. Clique em ⚙️ **Configurações do Projeto** (canto superior direito)
4. Guia **"Contas de Serviço"**
5. Botão **"Gerar Nova Chave Privada"** (azul)
6. Confirme clicando novamente em **"Gerar Chave"**
7. Um arquivo `[nome]-firebase-adminsdk-[hash].json` será baixado automaticamente

### Passo 2: Obter o Conteúdo do JSON

1. Abra o arquivo baixado em um editor de texto (VS Code, Notepad++, etc)
2. Selecione TODO o conteúdo (Ctrl+A)
3. Copie (Ctrl+C)
4. Este é o JSON que você precisa

---

## 🔑 Template para Fornecer as Credenciais

**Copie e cole TODO o conteúdo do arquivo JSON aqui:**

```json
{
  "type": "service_account",
  "project_id": "seu-projeto-id",
  "private_key_id": "chave-privada-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-xxxxx@seu-projeto.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
```

---

## ✅ Como Fornecer

**Opção 1: Direto no Chat**
- Cole o JSON completo aqui no chat
- Eu vou salvar como `firebaseConfig.json` na raiz do projeto
- Atualizarei variáveis de ambiente se necessário

**Opção 2: Via Arquivo**
- Salve o arquivo na pasta: `C:\Users\ANDERSON\iCloudDrive\Projeto Mercado Digital\Agente Bot\NeoEve - Empresarial\`
- Nomeie como: `firebaseConfig.json`
- Execute: `python tests/validacao_firebase_auth.py`

---

## ⚠️ Segurança

**Este arquivo contém credenciais sensíveis:**
- ❌ Nunca commitar para Git (já está em .gitignore)
- ❌ Nunca compartilhar publicamente
- ❌ Nunca incluir em logs
- ✅ Manter apenas localmente
- ✅ Se comprometido, regenerar no Firebase Console

---

## 📍 Próximas Etapas (Após Fornecer Credenciais)

1. ✅ Salvar `firebaseConfig.json` na raiz
2. ✅ Validar: `python tests/validacao_firebase_auth.py`
3. ✅ Se PASS → Rodar: `python -m pytest tests/runner_p1_identidade_canal_onboarding.py -v`
4. ✅ Se 9/9 PASS → Rodar: `python -m pytest tests/runner_p0_regressao_completa.py -v`
5. ✅ Se 174/174 PASS → Integrar em `principal_router.py`

---

**Aguardando suas credenciais...**
