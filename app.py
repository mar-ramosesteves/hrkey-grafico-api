from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import pandas as pd
import matplotlib.pyplot as plt
import io
import json

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://gestor.thehrkey.tech"]}})


# Carrega a matriz de cálculo com a coluna CHAVE
matriz = pd.read_excel("TABELA_GERAL_ARQUETIPOS_COM_CHAVE.xlsx")

@app.route("/grafico", methods=["POST"])
def gerar_grafico():
    try:
        if request.is_json:
            dados = request.get_json()
        else:
            dados = request.form.to_dict()

        if "entries" in dados:
            try:
                dados = json.loads(dados["entries"])
            except json.JSONDecodeError:
                raise Exception("Formato de JSON em 'entries' inválido.")

        if not dados:
            raise Exception("Nenhum dado recebido.")
        print("📦 Dados recebidos (após unpack):", dados)

        perguntas = [f"Q{str(i).zfill(2)}" for i in range(1, 50)]
        arquetipos = ["Imperativo", "Consultivo", "Cuidativo", "Resoluto", "Prescritivo", "Formador"]
        linhas = []

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

            for arq in arquetipos:
                chave = f"{arq}{nota}{cod}"
                match = matriz[matriz["CHAVE"] == chave]
                if not match.empty:
                    pontos = match.iloc[0]["PONTOS_OBTIDOS"]
                    maximo = match.iloc[0]["PONTOS_MAXIMOS"]
                    linhas.append((arq, pontos, maximo))

        if not linhas:
            raise Exception("Nenhuma resposta válida encontrada para gerar o gráfico.")

        df_result = pd.DataFrame(linhas, columns=["ARQUETIPO", "PONTOS_OBTIDOS", "PONTOS_MAXIMOS"])
        resumo = df_result.groupby("ARQUETIPO").sum()
        resumo["PERCENTUAL"] = (resumo["PONTOS_OBTIDOS"] / resumo["PONTOS_MAXIMOS"]) * 100
        resumo = resumo.reindex(arquetipos)

        email_lider = dados.get("emailLider", "N/D")
        data_envio = dados.get("data", "N/D")

        # Gráfico atualizado
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(resumo.index, resumo["PERCENTUAL"], color='skyblue')

        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, height + 1, f'{height:.1f}%', ha='center', va='bottom')

        ax.axhline(50, color='gray', linestyle='--', linewidth=1, label='50% (Suporte)')
        ax.axhline(60, color='red', linestyle='--', linewidth=1, label='60% (Dominante)')

        ax.set_ylim(0, 100)
        ax.set_ylabel('Pontuação (%)')
        ax.set_title(f"AUTOAVALIAÇÃO - ARQUÉTIPOS DE LIDERANÇA\nRespondente: {email_lider} | Data: {data_envio}", fontsize=13)
        ax.legend()
        plt.xticks(rotation=0)

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



@app.route("/relatorio", methods=["POST"])
def relatorio_detalhado():
    try:
        dados = request.get_json()
        if not dados:
            raise Exception("Nenhum dado recebido.")

        # Carrega matriz com tendência (%)
        matriz = pd.read_excel("TABELA_GERAL_ARQUETIPOS_COM_CHAVE.xlsx")

        perguntas = [f"Q{str(i).zfill(2)}" for i in range(1, 50)]
        arquetipos = ["Imperativo", "Consultivo", "Cuidativo", "Resoluto", "Prescritivo", "Formador"]
        linhas = []

        for cod in perguntas:
            nota = int(dados.get(cod, 0))
            if nota < 1 or nota > 6:
                continue

            linha_q = matriz[matriz["COD_AFIRMACAO"] == cod]
            chaves = [
                f"{arq}{nota}{cod}" for arq in arquetipos
            ]
            matches = matriz[matriz["CHAVE"].isin(chaves)]
            if matches.empty:
                continue

            # Seleciona os dois arquétipos com maior % tendência
            top2 = matches.sort_values(by="% Tendência", ascending=False).head(2)
            arqs = top2["ARQUETIPO"].tolist()
            tendencia = top2["Tendência"].values[0]
            percentual = top2["% Tendência"].values[0]

            frase = linha_q["AFIRMACAO"].values[0] if not linha_q.empty else cod

            linhas.append({
                "codigo": cod,
                "frase": frase,
                "percentual": round(percentual, 1),
                "tendencia": tendencia,
                "arquetipos": arqs
            })

        return jsonify({"resultado": linhas})

    except Exception as e:
        print("❌ Erro no /relatorio:", str(e))
        return jsonify({"erro": str(e)}), 500

