from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import pandas as pd
import matplotlib.pyplot as plt
import io
import json
import os





app = Flask(__name__)
from flask_cors import CORS

CORS(app, supports_credentials=True)

@app.after_request
def aplicar_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "https://gestor.thehrkey.tech"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response





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
        full_path = os.path.join("/tmp", caminho)

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
        full_path = os.path.join("/tmp", caminho)

        if os.path.exists(full_path):
            return jsonify({"status": "bloqueado"})
        else:
            return jsonify({"status": "liberado"})

    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500






def gerar_tabela_comparativa(json_auto, jsons_equipe, empresa, codrodada, emailLider):
    try:
        matriz = df.copy()
        arquetipos = ['Imperativo', 'Consultivo', 'Resoluto', 'Prescritivo', 'Formador', 'Cuidativo']
        dados = []

        for i in range(1, 50):
            q = f"Q{i:02d}"
            linha = {"Código": q}
            linha["Descrição"] = df_questoes_auto[df_questoes_auto["COD_AFIRMACAO"] == q]["AFIRMACAO"].values[0]

            for a in arquetipos:
                linha[f"{a}_auto"] = 0
                linha[f"{a}_media_eq"] = 0

            estrelas_auto = int(json_auto["respostas"][q])
            linhas_auto = matriz[(matriz["COD_AFIRMACAO"] == q) & (matriz["QTD_ESTRELAS"] == estrelas_auto)]
            for _, la in linhas_auto.iterrows():
                linha[f"{la['ARQUETIPO']}_auto"] = la["PONTOS_OBTIDOS"]

            contadores_eq = {a: 0 for a in arquetipos}
            somas_eq = {a: 0 for a in arquetipos}
            for json_eq in jsons_equipe:
                estrelas = int(json_eq["respostas"][q])
                linhas_eq = matriz[(matriz["COD_AFIRMACAO"] == q) & (matriz["QTD_ESTRELAS"] == estrelas)]
                for _, le in linhas_eq.iterrows():
                    a = le["ARQUETIPO"]
                    somas_eq[a] += le["PONTOS_OBTIDOS"]
                    contadores_eq[a] += 1

            for a in arquetipos:
                if contadores_eq[a]:
                    linha[f"{a}_media_eq"] = somas_eq[a] / contadores_eq[a]

            dados.append(linha)

        df_resultado = pd.DataFrame(dados)
        return df_resultado

    except Exception as e:
        print("❌ Erro ao gerar a tabela comparativa:", str(e))
        return None



import requests

def baixar_pasta_do_drive(empresa, codrodada, emailLider):
    caminho_local = f"/tmp/Avaliacoes RH/{empresa}/{codrodada}/{emailLider}"
    os.makedirs(caminho_local, exist_ok=True)

    payload = {
        "empresa": empresa,
        "codrodada": codrodada,
        "emailLider": emailLider
    }

    resposta = requests.post(
        "https://script.google.com/macros/s/AKfycbzMqrlVTOMeqPPqqGf9mfa-0-N8dTUWk7IA4X74VgpOm11nyGJvASMzOOCC2dIs2MfEyQ/exec",
        json=payload
    )

    dados = resposta.json()
    if "arquivos" not in dados:
        raise Exception("Erro ao listar arquivos no Drive: " + str(dados))

    for item in dados["arquivos"]:
        nome = item["nome"]
        conteudo = item["conteudo"]
        caminho_arquivo = os.path.join(caminho_local, nome)
        with open(caminho_arquivo, "w", encoding="utf-8") as f:
            f.write(conteudo)

    return caminho_local








app = Flask(__name__)
CORS(app, supports_credentials=True)

@app.after_request
def aplicar_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "https://gestor.thehrkey.tech"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

import os
import json
import base64
import requests
import pandas as pd
from flask import request, jsonify
from flask_cors import CORS

@app.route("/gerar-relatorio-xlsx", methods=["POST"])
def gerar_relatorio_xlsx():
    try:
        dados = request.get_json()
        empresa = dados.get("empresa")
        codrodada = dados.get("codrodada")
        emailLider = dados.get("emailLider")

        if not all([empresa, codrodada, emailLider]):
            return jsonify({"erro": "Faltam parâmetros obrigatórios."}), 400

        # Caminho seguro no Render
        caminho_pasta = f"/tmp/{empresa}/{codrodada}/{emailLider}"
        os.makedirs(caminho_pasta, exist_ok=True)

        # ⚠️ Simulação de arquivos (remover depois)
        exemplo_json_auto = {
            "tipo": "Autoavaliação",
            "respostas": {f"Q{i:02d}": "5" for i in range(1, 50)}
        }
        exemplo_json_equipe = {
            "tipo": "Avaliação Equipe",
            "respostas": {f"Q{i:02d}": "4" for i in range(1, 50)}
        }
        with open(os.path.join(caminho_pasta, "auto.json"), "w", encoding="utf-8") as f:
            json.dump(exemplo_json_auto, f, ensure_ascii=False, indent=2)
        for i in range(2):
            with open(os.path.join(caminho_pasta, f"equipe{i+1}.json"), "w", encoding="utf-8") as f:
                json.dump(exemplo_json_equipe, f, ensure_ascii=False, indent=2)

        # Leitura real dos arquivos
        jsons_auto, jsons_equipe = [], []
        for nome in os.listdir(caminho_pasta):
            if nome.endswith(".json"):
                with open(os.path.join(caminho_pasta, nome), "r", encoding="utf-8") as f:
                    conteudo = json.load(f)
                    if conteudo.get("tipo") == "Autoavaliação":
                        jsons_auto.append(conteudo)
                    elif conteudo.get("tipo") == "Avaliação Equipe":
                        jsons_equipe.append(conteudo)

        if not jsons_auto:
            return jsonify({"erro": "Nenhuma autoavaliação encontrada."}), 400
        if not jsons_equipe:
            return jsonify({"erro": "Nenhuma avaliação de equipe encontrada."}), 400

        # ✅ Gerar dataframe com respostas
        df = pd.DataFrame()
        for i, av in enumerate(jsons_equipe):
            col = pd.Series(av["respostas"], name=f"Equipe {i+1}")
            df = pd.concat([df, col], axis=1)

        df["Autoavaliacao"] = pd.Series(jsons_auto[0]["respostas"])
        df.to_excel(os.path.join(caminho_pasta, "relatorio.xlsx"), index_label="Questao")

        # Nome descritivo do arquivo
        nome_arquivo = f"relatorio_{empresa}_{codrodada}_{emailLider}.xlsx"
        caminho_arquivo_xlsx = os.path.join(caminho_pasta, "relatorio.xlsx")

        # Codifica em base64
        with open(caminho_arquivo_xlsx, "rb") as f:
            conteudo_xlsx_b64 = base64.b64encode(f.read()).decode("utf-8")

        # Envia para o Google Drive via Apps Script
        payload = {
            "empresa": empresa,
            "codrodada": codrodada,
            "emailLider": emailLider,
            "nomeArquivo": nome_arquivo,
            "base64Image": conteudo_xlsx_b64
        }

        resposta = requests.post(
            "https://script.google.com/macros/s/AKfycbw5AjoO_3WODqq5pLGDXAHxcC5UjoSoWN8_I_qW3PvL1DUqKBS4yiy_R2XCN7gq-Ozzcg/exec",
            json=payload
        )
        status_envio = resposta.text.strip()

        return jsonify({
            "mensagem": "✅ XLSX gerado com sucesso!",
            "arquivo": nome_arquivo,
            "caminho": caminho_pasta,
            "envio": status_envio
        })

    except Exception as e:
        return jsonify({"erro": str(e)}), 500


# Manter CORS
@app.after_request
def aplicar_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "https://gestor.thehrkey.tech"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

@app.route("/gerar-relatorio-json", methods=["POST"])
def gerar_relatorio_json():
    try:
        print("📩 request.data:", request.data)

        dados = request.get_json(force=True)  # força leitura segura do JSON
        empresa = dados.get("empresa")
        codrodada = dados.get("codrodada")
        emailLider = dados.get("emailLider")

        if not all([empresa, codrodada, emailLider]):
            return jsonify({"erro": "Faltam parâmetros obrigatórios."}), 400

        # 🔹 Baixa os arquivos JSON da pasta do líder
        caminho_local = baixar_pasta_do_drive(empresa, codrodada, emailLider)
        if not os.path.exists(caminho_local):
            return jsonify({"erro": f"Pasta '{caminho_local}' não encontrada no servidor."}), 400

        # 🔹 Lê os arquivos JSON
        jsons_auto = []
        jsons_equipe = []

        for nome in os.listdir(caminho_local):
            if nome.endswith(".json"):
                with open(os.path.join(caminho_local, nome), "r", encoding="utf-8") as f:
                    try:
                        conteudo = json.load(f)
                        tipo = conteudo.get("tipo", "").lower()
                        if "auto" in tipo:
                            jsons_auto.append(conteudo)
                        elif "equipe" in tipo:
                            jsons_equipe.append(conteudo)
                    except Exception as e:
                        print(f"⚠️ Erro ao ler {nome}: {e}")

        if not jsons_auto:
            return jsonify({"erro": "Nenhuma autoavaliação encontrada."}), 400
        if not jsons_equipe:
            return jsonify({"erro": "Nenhuma avaliação de equipe encontrada."}), 400

        # 🔹 Calcula média por questão
        total_respostas = {}
        quantidade_respostas = {}

        for avaliacao in jsons_equipe:
            for q, valor in avaliacao.get("respostas", {}).items():
                try:
                    valor_float = float(valor)
                    total_respostas[q] = total_respostas.get(q, 0) + valor_float
                    quantidade_respostas[q] = quantidade_respostas.get(q, 0) + 1
                except ValueError:
                    print(f"⚠️ Valor inválido em {q}: {valor}")

        medias_equipe = {
            q: round(total_respostas[q] / quantidade_respostas[q], 2)
            for q in total_respostas
        }

        # 🔹 Prepara o dicionário final
        relatorio = {
            "empresa": empresa,
            "codrodada": codrodada,
            "emailLider": emailLider,
            "autoavaliacao": jsons_auto[0].get("respostas", {}),
            "mediaEquipe": medias_equipe,
            "qtdAvaliacoesEquipe": len(jsons_equipe)
        }

        # 🔹 Salva como relatorio_completo.json
        caminho_arquivo = os.path.join(caminho_local, "relatorio_completo.json")
        with open(caminho_arquivo, "w", encoding="utf-8") as f:
            json.dump(relatorio, f, ensure_ascii=False, indent=2)

        return jsonify({
            "mensagem": "✅ Relatório consolidado salvo como relatorio_completo.json!",
            "arquivo": "relatorio_completo.json",
            "caminho": caminho_local
        })

    except Exception as e:
        return jsonify({"erro": str(e)}), 500
