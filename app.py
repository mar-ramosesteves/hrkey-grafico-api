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

        # Carrega a matriz principal (com tendência)
        matriz = pd.read_excel("TABELA_GERAL_ARQUETIPOS_COM_CHAVE.xlsx")

        # Carrega as frases corretas da autoavaliação
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

            frase = frases_dict.get(cod, cod)  # Busca no dicionário correto

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



@app.route('/grafico-equipe', methods=['POST'])
def grafico_equipe():
    dados = request.get_json()
    email = dados.get('emailLider')
    data = dados.get('data')

    # Caminho do CSV com dados da equipe
    df = pd.read_csv('avaliacao_equipes.csv')

    # Filtrar pelas entradas do líder e data
    df_filtrado = df[(df['emailLider'] == email) & (df['data'] == data)]

    if df_filtrado.empty:
        return jsonify({'erro': 'Nenhuma avaliação encontrada para esse líder e data.'}), 404

    resultados = []

    for cod in df_filtrado['cod_afirmacao'].unique():
        grupo = df_filtrado[df_filtrado['cod_afirmacao'] == cod]
        media_estrelas = grupo['nota'].mean()

        # Peso para equipe (escala reversa)
        if media_estrelas == 1:
            peso = 2
        elif media_estrelas == 2:
            peso = 1.5
        elif media_estrelas == 3:
            peso = 1
        else:
            peso = 0  # segurança

        percentual = round((peso / 2) * 100, 1)

        resultados.append({
            'cod_afirmacao': cod,
            'percentual': percentual
        })

        # Gerar gráfico
        fig, ax = plt.subplots(figsize=(6, 1.2))
        ax.barh([cod], [percentual], color='orange')
        ax.set_xlim([0, 100])
        ax.set_title(f'{cod} - {percentual}%')
        ax.set_xlabel('Percentual (Equipe)')
        plt.tight_layout()

        # Salvar
        import os
        if not os.path.exists('graficos_equipe'):
            os.makedirs('graficos_equipe')
        nome_arquivo = f'graficos_equipe/{email}_{data}_{cod}.png'
        plt.savefig(nome_arquivo)
        plt.close()

    return jsonify({'mensagem': 'Gráficos gerados com sucesso!', 'total': len(resultados)})



import requests

@app.route('/enviar-avaliacao', methods=['POST'])
def enviar_avaliacao():
    try:
        dados = request.get_json()

        resposta = requests.post(
            'https://script.google.com/macros/s/AKfycbzAAMWWhjEnF-g0ZaZOUjP6et28T7_wXqXOxf4b9ysGodnA2lARUlR447PRehoRt2aivw/exec',
            json=dados,
            timeout=10
        )

        return jsonify({
            'status': 'ok',
            'google_response': resposta.text
        }), 200

    except Exception as e:
        print("❌ Erro ao enviar para Google Script:", str(e))
        return jsonify({
            'status': 'erro',
            'mensagem': str(e)
        }), 500

