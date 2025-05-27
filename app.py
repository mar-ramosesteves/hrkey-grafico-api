from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import pandas as pd
import matplotlib.pyplot as plt
import io
import json
import os


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
    'https://script.google.com/macros/s/AKfycbw5AjoO_3WODqq5pLGDXAHxcC5UjoSoWN8_I_qW3PvL1DUqKBS4yiy_R2XCN7gq-Ozzcg/exec',
    json=dados,
    timeout=10
)


        texto = resposta.text.strip()

        if "já enviou" in texto:
            return jsonify({
                'status': 'duplicado',
                'mensagem': texto
            }), 409

        return jsonify({
            'status': 'ok',
            'mensagem': texto
        }), 200

    except Exception as e:
        print("❌ Erro ao enviar para Google Script:", str(e))
        return jsonify({
            'status': 'erro',
            'mensagem': str(e)
        }), 500


@app.route('/verificar-envio', methods=['POST'])
def verificar_envio():
    try:
        dados = request.get_json()
        empresa = dados.get("empresa")
        codrodada = dados.get("codrodada")
        emailLider = dados.get("emailLider")
        emailRespondente = dados.get("email")
        tipo = dados.get("tipo", "Avaliacao").replace(" ", "_")

        if not all([empresa, codrodada, emailLider, emailRespondente]):
            return jsonify({"status": "erro", "mensagem": "Campos obrigatórios ausentes."}), 400

        nome_arquivo = f"{emailRespondente}_{tipo}.json"
        caminho = f"Avaliacoes RH/{empresa}/{codrodada}/{emailLider}/{nome_arquivo}"
        full_path = os.path.join("/mnt/data", caminho)

        if os.path.exists(full_path):
            return jsonify({"status": "existe"})
        else:
            return jsonify({"status": "nao_existe"})

    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


@app.route('/validar-acesso-formulario', methods=['POST'])
def validar_acesso_formulario():
    try:
        dados = request.get_json()
        empresa = dados.get("empresa")
        codrodada = dados.get("codrodada")
        emailLider = dados.get("emailLider")
        email = dados.get("email")
        tipo = dados.get("tipo", "Avaliacao").replace(" ", "_")

        if not all([empresa, codrodada, emailLider, email]):
            return jsonify({"status": "erro", "mensagem": "Campos obrigatórios ausentes."}), 400

        nome_arquivo = f"{email}_{tipo}.json"
        caminho = f"Avaliacoes RH/{empresa}/{codrodada}/{emailLider}/{nome_arquivo}"
        full_path = os.path.join("/mnt/data", caminho)

        if os.path.exists(full_path):
            return jsonify({"status": "bloqueado"})
        else:
            return jsonify({"status": "liberado"})

    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500




    @app.route('/gerar-graficos-comparativos', methods=['POST'])
def gerar_graficos_comparativos():
    try:
        dados = request.get_json()
        empresa = dados.get("empresa")
        codrodada = dados.get("codrodada")
        emailLider = dados.get("emailLider")
        json_auto = dados.get("json_auto")
        jsons_equipe = dados.get("jsons_equipe")

        if not all([empresa, codrodada, emailLider, json_auto, jsons_equipe]):
            return jsonify({"erro": "Faltam dados obrigatórios para gerar os gráficos."}), 400

        resultados = gerar_graficos_para_drive(json_auto, jsons_equipe, empresa, codrodada, emailLider)

        return jsonify({
            "mensagem": "Gráficos comparativos gerados com sucesso!",
            "arquivos_salvos": resultados
        }), 200

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

import base64
import tempfile
import requests
from matplotlib.backends.backend_pdf import PdfPages

def gerar_graficos_para_drive(json_auto, jsons_equipe, empresa, codrodada, emailLider):
    try:
        matriz = df.copy()
        arquetipos = ['Imperativo', 'Consultivo', 'Resoluto', 'Prescritivo', 'Formador', 'Cuidativo']
        pontos_auto = {a: 0 for a in arquetipos}
        max_auto = {a: 0 for a in arquetipos}
        pontos_eq = {a: 0 for a in arquetipos}
        max_eq = {a: 0 for a in arquetipos}

        for i in range(1, 50):
            q = f"Q{i:02d}"
            estrelas_auto = int(json_auto["respostas"][q])
            linhas_auto = matriz[(matriz["COD_AFIRMACAO"] == q) & (matriz["QTD_ESTRELAS"] == estrelas_auto)]
            for _, linha in linhas_auto.iterrows():
                a = linha["ARQUETIPO"]
                pontos_auto[a] += float(linha["PONTOS_OBTIDOS"])
                max_auto[a] += float(linha["PONTOS_MAXIMOS"])

            for json_eq in jsons_equipe:
                estrelas_eq = int(json_eq["respostas"][q])
                linhas_eq = matriz[(matriz["COD_AFIRMACAO"] == q) & (matriz["QTD_ESTRELAS"] == estrelas_eq)]
                for _, linha in linhas_eq.iterrows():
                    a = linha["ARQUETIPO"]
                    pontos_eq[a] += float(linha["PONTOS_OBTIDOS"])
                    max_eq[a] += float(linha["PONTOS_MAXIMOS"])

        percentuais_auto = {a: pontos_auto[a] / max_auto[a] if max_auto[a] > 0 else 0 for a in arquetipos}
        percentuais_eq = {a: pontos_eq[a] / max_eq[a] if max_eq[a] > 0 else 0 for a in arquetipos}

        pares = []
        for i in range(1, 50):
            q = f"Q{i:02d}"
            estrelas_auto = int(json_auto["respostas"][q])
            texto_auto = df_questoes_auto[df_questoes_auto["COD_AFIRMACAO"] == q]["AFIRMACAO"].values[0]
            linha_auto = matriz[(matriz["COD_AFIRMACAO"] == q) & (matriz["QTD_ESTRELAS"] == estrelas_auto)]
            perc_auto = float(linha_auto["% Tendência"].mean()) * 100
            status_auto = linha_auto["Tendência"].mode().values[0]

            valores_eq = []
            status_eq = []
            for json_eq in jsons_equipe:
                estrelas = int(json_eq["respostas"][q])
                linha = matriz[(matriz["COD_AFIRMACAO"] == q) & (matriz["QTD_ESTRELAS"] == estrelas)]
                if not linha.empty:
                    valores_eq.extend(linha["% Tendência"].astype(float).tolist())
                    status_eq.extend(linha["Tendência"].tolist())

            perc_eq = sum(valores_eq) / len(valores_eq) * 100 if valores_eq else 0
            status_eq_final = max(set(status_eq), key=status_eq.count) if status_eq else ""
            texto_eq = matriz[matriz["COD_AFIRMACAO"] == q]["AFIRMACAO"].values[0]

            pares.append({
                "auto": {"valor": perc_auto, "texto": texto_auto, "status": status_auto},
                "equipe": {"valor": perc_eq, "texto": texto_eq, "status": status_eq_final}
            })

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            caminho_pdf = tmp.name
            with PdfPages(caminho_pdf) as pdf:
                fig1 = gerar_grafico_principal(percentuais_auto, percentuais_eq, arquetipos)
                pdf.savefig(fig1)
                plt.close(fig1)

                for bloco in range(0, len(pares), 3):
                    fig = plt.figure(figsize=(8.5, 10), facecolor='white')
                    spec = gridspec.GridSpec(nrows=6, ncols=1, figure=fig)

                    for i, par in enumerate(pares[bloco:bloco+3]):
                        if i >= 3: break
                        ax_auto = fig.add_subplot(spec[i*2])
                        ax_auto.barh([0], [par["auto"]["valor"]], color='blue', height=0.1)
                        ax_auto.set_xlim(0, 100)
                        ax_auto.set_yticks([])
                        ax_auto.set_xticks(list(range(0, 110, 10)))
                        ax_auto.set_xticklabels([f"{x}%" for x in range(0, 110, 10)], fontsize=8)
                        ax_auto.set_title(f'{par["auto"]["texto"]}\n📌 Status: {par["auto"]["status"]}  •  Resultado: {par["auto"]["valor"]:.2f}%',
                                          fontsize=10, pad=8, loc='left')
                        ax_auto.set_facecolor('white')
                        for spine in ax_auto.spines.values():
                            spine.set_edgecolor('black')

                        ax_eq = fig.add_subplot(spec[i*2+1])
                        ax_eq.barh([0], [par["equipe"]["valor"]], color='orange', height=0.1)
                        ax_eq.set_xlim(0, 100)
                        ax_eq.set_yticks([])
                        ax_eq.set_xticks(list(range(0, 110, 10)))
                        ax_eq.set_xticklabels([f"{x}%" for x in range(0, 110, 10)], fontsize=8)
                        ax_eq.set_title(f'{par["equipe"]["texto"]}\n📌 Status: {par["equipe"]["status"]}  •  Resultado: {par["equipe"]["valor"]:.2f}%',
                                        fontsize=10, pad=8, loc='left')
                        ax_eq.set_facecolor('white')
                        for spine in ax_eq.spines.values():
                            spine.set_edgecolor('black')

                    fig.tight_layout(pad=2.5)
                    pdf.savefig(fig)
                    plt.close(fig)

        with open(caminho_pdf, "rb") as f:
            pdf_b64 = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "empresa": empresa,
            "codrodada": codrodada,
            "emailLider": emailLider,
            "nomeArquivo": f"relatorio_{emailLider}.pdf",
            "base64Image": pdf_b64
        }

        resposta = requests.post(
            "https://script.google.com/macros/s/AKfycbw5AjoO_3WODqq5pLGDXAHxcC5UjoSoWN8_I_qW3PvL1DUqKBS4yiy_R2XCN7gq-Ozzcg/exec",
            json=payload
        )

        return {"status": "ok", "resposta": resposta.text.strip(), "arquivo": f"relatorio_{emailLider}.pdf"}

    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}
