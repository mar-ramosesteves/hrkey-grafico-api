from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import pandas as pd
import io
import matplotlib.pyplot as plt
import os

app = Flask(__name__)
CORS(app)

# Localização dos arquivos CSV e Excel
CAMINHO_AUTO = "form_Arquetipos_auto_aval-export-1746712137.csv"
CAMINHO_EQUIPE = "form_Arquetipos_Equipe-export-1746712147.csv"
CAMINHO_MAXIMOS = "Pontuacao_Max_por_Afirmacao_Arquetipos.xlsx"
CAMINHO_ESCALAS = "ESCALAS_ARQUETIPOS.xlsx"

def calcular_pontuacoes_por_arquetipo(email_lider, data_envio):
    auto_df = pd.read_csv(CAMINHO_AUTO)
    equipe_df = pd.read_csv(CAMINHO_EQUIPE)
    maximos_df = pd.read_excel(CAMINHO_MAXIMOS)
    escalas_df = pd.read_excel(CAMINHO_ESCALAS)

    # ⏳ Filtro por e-mail e data
    auto_linha = auto_df[(auto_df["emailLider"] == email_lider) & (auto_df["data"] == data_envio)]
    equipe_linhas = equipe_df[(equipe_df["emailLider"] == email_lider) & (equipe_df["data"] == data_envio)]

    if auto_linha.empty or equipe_linhas.empty:
        raise Exception("Dados não encontrados para este líder nesta data.")

    # 🔢 Montagem das notas
    def peso(estrela):
        estrela = int(estrela)
        if estrela == 6:
            return 2
        elif estrela == 5:
            return 1.5
        elif estrela == 4:
            return 1
        elif estrela == 3:
            return 1
        elif estrela == 2:
            return 1.5
        elif estrela == 1:
            return 2
        return 0

    def calcular_resposta(linha):
        resultados = {}
        for coluna in linha.index:
            if str(coluna).startswith("Q"):
                estrelas = linha[coluna]
                if pd.isna(estrelas): continue
                try:
                    estrelas = int(estrelas)
                except:
                    continue
                afirmacao = coluna.replace("Q", "")
                estilo = maximos_df[maximos_df["ID"].astype(str) == afirmacao]["ARQUÉTIPO"].values[0]
                max_ponto = maximos_df[maximos_df["ID"].astype(str) == afirmacao]["PONTUAÇÃO MÁXIMA"].values[0]
                p = peso(estrelas)
                resultado = p * estrelas
                resultados.setdefault(estilo, []).append((resultado, max_ponto))
        return resultados

    def consolidar_resultados(respostas):
        totais = {}
        for estilo in respostas:
            pontos = sum(r[0] for r in respostas[estilo])
            maximos = sum(r[1] for r in respostas[estilo])
            totais[estilo] = round(100 * pontos / maximos, 2) if maximos > 0 else 0
        return totais

    auto_resultados = calcular_resposta(auto_linha.iloc[0])
    equipe_resultados_somados = {}

    for _, linha in equipe_linhas.iterrows():
        r = calcular_resposta(linha)
        for k in r:
            equipe_resultados_somados.setdefault(k, []).extend(r[k])

    equipe_resultados = {}
    for estilo in equipe_resultados_somados:
        pontos = sum(r[0] for r in equipe_resultados_somados[estilo])
        maximos = sum(r[1] for r in equipe_resultados_somados[estilo])
        media = round(100 * pontos / maximos, 2) if maximos > 0 else 0
        equipe_resultados[estilo] = media

    return consolidar_resultados(auto_resultados), equipe_resultados

@app.route('/grafico', methods=['POST'])
def gerar_grafico():
    try:
        dados = request.get_json()
        print("🔍 Dados recebidos:", dados)

        email = dados["emailLider"]
        data = dados["dataEnvio"]

        auto, equipe = calcular_pontuacoes_por_arquetipo(email, data)

        estilos = ['Imperativo', 'Resoluto', 'Cuidativo', 'Consultivo', 'Prescritivo', 'Formador']
        auto_valores = [auto.get(e, 0) for e in estilos]
        equipe_valores = [equipe.get(e, 0) for e in estilos]

        fig, ax = plt.subplots(figsize=(10, 6))
        largura = 0.35
        x = range(len(estilos))

        ax.bar(x, auto_valores, width=largura, label='Autoavaliação')
        ax.bar([i + largura for i in x], equipe_valores, width=largura, label='Equipe')

        ax.set_xticks([i + largura / 2 for i in x])
        ax.set_xticklabels(estilos)
        ax.set_ylim(0, 100)
        ax.axhline(50, color='gray', linestyle='--', linewidth=1)
        ax.axhline(60, color='gray', linestyle='--', linewidth=1)
        ax.set_title(f"Avaliação de {email} - {data}")
        ax.set_ylabel("Pontuação (%)")
        ax.legend()

        buffer = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        plt.close()

        return send_file(buffer, mimetype='image/png')

    except Exception as e:
        print("❌ Erro ao gerar gráfico:", str(e))
        return jsonify({'erro': str(e)}), 500
