from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import pandas as pd
import matplotlib.pyplot as plt
import io
import json  # <-- importar json para carregar o string
 
app = Flask(__name__)
CORS(app)
 
# Carrega a matriz de cálculo com a coluna CHAVE
matriz = pd.read_excel("TABELA_GERAL_ARQUETIPOS_COM_CHAVE.xlsx")
 
 
@app.route("/grafico", methods=["POST"])
def gerar_grafico():
    try:
        # 1) Recebe o payload
        if request.is_json:
            dados = request.get_json()
        else:
            dados = request.form.to_dict()
 
        # 2) Se veio dentro de 'entries' como string JSON, converte para dict
        if "entries" in dados:
            try:
                dados = json.loads(dados["entries"])
            except json.JSONDecodeError:
                raise Exception("Formato de JSON em 'entries' inválido.")
 
        if not dados:
            raise Exception("Nenhum dado recebido.")
        print("📦 Dados recebidos (após unpack):", dados)
 
        # 3) Definições
        perguntas = [f"Q{str(i).zfill(2)}" for i in range(1, 50)]  # Q01 a Q49
        arquetipos = [
            "Imperativo",
            "Consultivo",
            "Cuidativo",
            "Resoluto",
            "Prescritivo",
            "Formador",
        ]
 
        linhas = []
 
        # 4) Para cada pergunta, busca tanto a chave maiúscula quanto minúscula
        for cod in perguntas:
            raw = dados.get(cod) or dados.get(cod.lower())
            if raw is None:
                continue
            try:
                nota = int(raw)
                if nota < 1 or nota > 6:
                    continue
            except ValueError:
                continue
 
            # 5) Monta a CHAVE e busca na matriz
            for arq in arquetipos:
                chave = f"{arq}{nota}{cod}"
                match = matriz[matriz["CHAVE"] == chave]
                if not match.empty:
                    pontos = match.iloc[0]["PONTOS_OBTIDOS"]
                    maximo = match.iloc[0]["PONTOS_MAXIMOS"]
                    linhas.append((arq, pontos, maximo))
 
        if not linhas:
            raise Exception("Nenhuma resposta válida encontrada para gerar o gráfico.")
 
        # 6) Agrupa e calcula percentual
        df_result = pd.DataFrame(
            linhas, columns=["ARQUETIPO", "PONTOS_OBTIDOS", "PONTOS_MAXIMOS"]
        )
        resumo = df_result.groupby("ARQUETIPO").sum()
        resumo["PERCENTUAL"] = (
            resumo["PONTOS_OBTIDOS"] / resumo["PONTOS_MAXIMOS"]
        ) * 100
 
        # 7) Gera o gráfico
        fig, ax = plt.subplots(figsize=(10, 6))
        resumo = resumo.sort_index()
        ax.bar(resumo.index, resumo["PERCENTUAL"])
        ax.set_ylim(0, 120)
        ax.set_title("Avaliação de Arquétipos")
        ax.set_ylabel("Pontuação (%)")
        plt.xticks(rotation=45)
        plt.grid(axis="y")
 
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png")
        buf.seek(0)
        plt.close()
 
        return send_file(buf, mimetype="image/png")
 
    except Exception as e:
        print("❌ Erro:", str(e))
        return jsonify({"erro": str(e)}), 500
 
 
@app.route("/")
def home():
    return "🎯 API de Gráficos de Arquétipos está ativa!"
