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
        resumo["PERCENTUAL"] = resumo["PERCENTUAL"].round(4)

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

        matriz = pd.read_excel("TABELA_GERAL_ARQUETIPOS_COM_CHAVE.xlsx")
        frases_auto = pd.read_excel("QUESTOES_AUTO_AVALIACAO.xlsx")
        frases_dict = dict(zip(frases_auto["COD_AFIRMACAO"], frases_auto["AFIRMACAO"]))

        perguntas = [f"Q{str(i).zfill(2)}" for i in range(1, 50)]
        arquetipos = ["Imperativo", "Consultivo", "Cuidativo", "Resoluto", "Prescritivo", "Formador"]
        linhas = []

        for cod in perguntas:
            nota = int(dados.get(cod, 0))
            if nota < 1 or nota > 6:
                continue

            linha_q = matriz[matriz["COD_AFIRMACAO"] == cod]
            chaves = [f"{arq}{nota}{cod}" for arq in arquetipos]
            matches = matriz[matriz["CHAVE"].isin(chaves)]
            if matches.empty:
                continue

            top2 = matches.sort_values(by="% Tendência", ascending=False).head(2)
            arqs = top2["ARQUETIPO"].tolist()
            tendencia = top2["Tendência"].values[0]
            percentual = top2["% Tendência"].values[0]
            frase = frases_dict.get(cod, cod)

            linhas.append({
                "codigo": cod,
                "frase": frase,
                "percentual": round(percentual, 3),
                "tendencia": tendencia,
                "arquetipos": arqs
            })

        return jsonify({"resultado": linhas})

    except Exception as e:
        print("❌ Erro no /relatorio:", str(e))
        return jsonify({"erro": str(e)}), 500

@app.route('/relatorio-equipe', methods=['POST'])
def relatorio_equipe():
    try:
        dados = request.get_json()
        if not dados:
            raise Exception("Nenhum dado recebido.")

        email = dados.get('emailLider')
        data = dados.get('data')

        if not email or not data:
            raise Exception("Faltam email ou data.")

        # Carrega a planilha com as chaves e tendências
        matriz = pd.read_excel("TABELA_GERAL_ARQUETIPOS_COM_CHAVE.xlsx")

        perguntas = [f"Q{str(i).zfill(2)}" for i in range(1, 50)]
        arquetipos = ["Imperativo", "Consultivo", "Cuidativo", "Resoluto", "Prescritivo", "Formador"]
        linhas = []

        for cod in perguntas:
            nota = int(dados.get(cod, 0))
            if nota < 1 or nota > 6:
                continue

            # Gerar todas as chaves possíveis para essa nota
            chaves = [f"{arq}{nota}{cod}" for arq in arquetipos]
            subconjunto = matriz[matriz["CHAVE"].isin(chaves)]

            if subconjunto.empty:
                continue

            top2 = subconjunto.sort_values(by="% Tendência", ascending=False).head(2)

            arqs = top2["ARQUETIPO"].tolist() if "ARQUETIPO" in top2.columns else [chave[:-len(cod)] for chave in top2["CHAVE"]]
            tendencia = top2["Tendência"].values[0]
            percentual = top2["% Tendência"].values[0]
            frase = top2["AFIRMACAO"].values[0]

            linhas.append({
                "codigo": cod,
                "frase": frase,
                "percentual": round(percentual, 3),
                "tendencia": tendencia,
                "arquetipos": arqs
            })

        return jsonify({"resultado": linhas})

    except Exception as e:
        print("❌ Erro no /relatorio-equipe:", str(e))
        return jsonify({"erro": str(e)}), 500

@app.route('/grafico-equipe', methods=['POST'])
def grafico_equipe():
    try:
        dados = request.get_json()
        if not dados:
            raise Exception("Nenhum dado recebido.")

        perguntas = [f"Q{str(i).zfill(2)}" for i in range(1, 50)]
        arquetipos = ["Imperativo", "Consultivo", "Cuidativo", "Resoluto", "Prescritivo", "Formador"]
        linhas = []

        for cod in perguntas:
            nota = int(dados.get(cod, 0))
            if nota < 1 or nota > 6:
                continue

            for arq in arquetipos:
                chave = f"{arq}{nota}{cod}"
                match = matriz[matriz["CHAVE"] == chave]
                if not match.empty:
                    pontos = match.iloc[0]["PONTOS_OBTIDOS"]
                    maximo = match.iloc[0]["PONTOS_MAXIMOS"]
                    linhas.append((arq, pontos, maximo))

        if not linhas:
            raise Exception("Nenhuma resposta válida encontrada.")

        df_result = pd.DataFrame(linhas, columns=["ARQUETIPO", "PONTOS_OBTIDOS", "PONTOS_MAXIMOS"])
        resumo = df_result.groupby("ARQUETIPO").sum()
        resumo["PERCENTUAL"] = (resumo["PONTOS_OBTIDOS"] / resumo["PONTOS_MAXIMOS"]) * 100
        resumo["PERCENTUAL"] = resumo["PERCENTUAL"].round(4)
        resumo = resumo.reindex(arquetipos)

        email_lider = dados.get("emailLider", "N/D")
        data_envio = dados.get("data", "N/D")

        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(resumo.index, resumo["PERCENTUAL"], color='orange')

        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, height + 1, f'{height:.1f}%', ha='center', va='bottom')

        ax.axhline(50, color='gray', linestyle='--', linewidth=1, label='50% (Suporte)')
        ax.axhline(60, color='red', linestyle='--', linewidth=1, label='60% (Dominante)')

        ax.set_ylim(0, 100)
        ax.set_ylabel('Pontuação (%)')
        ax.set_title(f"EQUIPE - ARQUÉTIPOS DE LIDERANÇA\nLíder Avaliado: {email_lider} | Data: {data_envio}", fontsize=13)
        ax.legend()
        plt.xticks(rotation=0)

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png")
        buf.seek(0)
        plt.close()

        return send_file(buf, mimetype="image/png")

    except Exception as e:
        print("❌ Erro no /grafico-equipe:", str(e))
        return jsonify({"erro": str(e)}), 500


import requests
import os

GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbw5AjoO_3WODqq5pLGDXAHxcC5UjoSoWN8_I_qW3PvL1DUqKBS4yiy_R2XCN7gq-Ozzcg/exec"
PASTA_RAIZ = "Avaliacoes RH"

@app.route("/enviar-avaliacao", methods=["POST"])
def enviar_avaliacao():
    try:
        dados = request.get_json()
        if not dados:
            raise Exception("Nenhum dado recebido.")

        # Campos obrigatórios
        emailRespondente = dados.get("email")
        nomeRespondente = dados.get("nome")
        nomeLider = dados.get("nomeLider")
        emailLider = dados.get("emailLider")
        empresa = dados.get("empresa")
        codRodada = dados.get("codrodada")
        tipo = dados.get("tipo")  # 'autoavaliacao' ou 'avaliacao_equipe'

        if not all([emailRespondente, emailLider, empresa, codRodada, tipo]):
            raise Exception("Campos obrigatórios ausentes.")

        # Geração do nome do arquivo e caminho
        nome_arquivo = f"{emailRespondente}_{tipo}.json"
        caminho = f"{PASTA_RAIZ}/{empresa}/{codRodada}/{emailLider}/{nome_arquivo}"

        # Envia o arquivo via Google Script
        payload = {
            "arquivo": nome_arquivo,
            "caminho": caminho,
            "conteudo": json.dumps(dados, ensure_ascii=False)
        }

        resposta = requests.post(GOOGLE_SCRIPT_URL, json=payload)

        print("📤 Payload enviado ao Google Script:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))

        print("📥 Resposta recebida do Google Script:")
        print(resposta.text)

        if resposta.status_code != 200:
            raise Exception(f"Erro ao enviar para o Drive: {resposta.text}")

        return jsonify({"mensagem": "✅ Avaliação enviada com sucesso!"})

    except Exception as e:
        print("❌ Erro no /enviar-avaliacao:", str(e))
        return jsonify({"erro": str(e)}), 500



@app.route("/verificar-envio", methods=["POST"])
def verificar_envio():
    try:
        dados = request.get_json()
        email = dados.get("email")
        tipo = dados.get("tipo")
        empresa = dados.get("empresa")
        codRodada = dados.get("codrodada")
        emailLider = dados.get("emailLider")

        nome_arquivo = f"{email}_{tipo}.json"
        caminho = f"{PASTA_RAIZ}/{empresa}/{codRodada}/{emailLider}/{nome_arquivo}"

        payload = {"verificar": True, "caminho": caminho}
        resposta = requests.post(GOOGLE_SCRIPT_URL, json=payload)

        if resposta.status_code != 200:
            raise Exception("Erro ao verificar envio.")

        conteudo = resposta.json()
        jaExiste = conteudo.get("existe", False)
        return jsonify({"jaExiste": jaExiste})

    except Exception as e:
        print("❌ Erro no /verificar-envio:", str(e))
        return jsonify({"erro": str(e)}), 500


@app.route("/validar-acesso-formulario", methods=["POST"])
def validar_acesso_formulario():
    try:
        dados = request.get_json()
        email = dados.get("email")
        tipo = dados.get("tipo")
        empresa = dados.get("empresa")
        codRodada = dados.get("codrodada")
        emailLider = dados.get("emailLider")

        if not all([email, tipo, empresa, codRodada, emailLider]):
            raise Exception("Dados incompletos para validação.")

        nome_arquivo = f"{email}_{tipo}.json"
        caminho = f"{PASTA_RAIZ}/{empresa}/{codRodada}/{emailLider}/{nome_arquivo}"

        payload = {"verificar": True, "caminho": caminho}
        resposta = requests.post(GOOGLE_SCRIPT_URL, json=payload)
        existe = resposta.json().get("existe", False)

        return jsonify({"acessoLiberado": not existe})

    except Exception as e:
        print("❌ Erro no /validar-acesso-formulario:", str(e))
        return jsonify({"erro": str(e)}), 500

