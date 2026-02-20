from telegram import Update
from telegram.ext import ContextTypes
import os
import pandas as pd
from services.firebase_service_async import salvar_dado_em_path
from utils.permissao_utils import verificar_dono

# 🔍 Detecta colunas por alternativas possíveis
def detectar_coluna(colunas, alternativas):
    for alt in alternativas:
        for col in colunas:
            if alt.lower() in col.lower():
                return col
    return None

# 📊 Lê a planilha e salva os profissionais no Firebase
async def importar_profissionais_de_planilha(file_path, user_id):
    try:
        df = pd.read_excel(file_path) if file_path.endswith(".xlsx") else pd.read_csv(file_path)
        colunas = df.columns

        col_nome = detectar_coluna(colunas, ["nome", "profissional", "nome profissional", "nome do profissional"])
        col_servicos = detectar_coluna(colunas, ["serviços", "servicos", "funções", "atividades", "especialidades"])
        col_precos = detectar_coluna(colunas, ["preços", "valores", "preco", "preço", "valor"])

        if not col_nome or not col_servicos:
            print("❌ Cabeçalhos obrigatórios não encontrados.")
            return False

        for _, row in df.iterrows():
            nome = str(row[col_nome]).strip()
            if not nome: continue

            servicos = [s.strip() for s in str(row[col_servicos]).split(",")]
            dados = {
                "nome": nome,
                "servicos": servicos
            }

            if col_precos and str(row[col_precos]).strip().lower() != "nan":
                try:
                    precos = [float(p.strip()) for p in str(row[col_precos]).split(",")]
                    dados["precos"] = dict(zip(servicos, precos))
                except Exception:
                    pass  # Ignora erros de preço

            path = f"Clientes/{user_id}/Profissionais/{nome}"
            await salvar_dado_em_path(path, dados)

        return True
    except Exception as e:
        print(f"❌ Erro ao importar planilha: {e}")
        return False

# 🚀 Handler para receber e processar a planilha
async def importar_profissionais_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    if not context.user_data.get("esperando_planilha"):
        await update.message.reply_text("❌ Nenhuma importação foi solicitada. Peça primeiro para importar profissionais.")
        return

    context.user_data["esperando_planilha"] = False

    if not await verificar_dono(user_id):
        await update.message.reply_text("🚫 Apenas o dono pode importar arquivos.")
        return

    if not update.message.document:
        await update.message.reply_text("📂 Envie um arquivo Excel (.xlsx) ou CSV com os profissionais.")
        return

    file = await update.message.document.get_file()
    file_path = f"/tmp/{update.message.document.file_name}"
    await file.download_to_drive(file_path)

    await update.message.reply_text(f"📅 Arquivo recebido! Processando...")

    sucesso = await importar_profissionais_de_planilha(file_path, user_id)

    if sucesso:
        context.user_data["ultima_importacao_profissionais"] = "sucesso"
        await update.message.reply_text("✅ Profissionais importados com sucesso!")
    else:
        context.user_data["ultima_importacao_profissionais"] = "erro"
        await update.message.reply_text("❌ Erro ao importar profissionais.")

    os.remove(file_path)
