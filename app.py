from flask import Flask, request, send_file, jsonify 

from flask_cors import CORS 

import pandas as pd 

import matplotlib.pyplot as plt 

import io 

import json 

import os 

 

 

app = Flask(__name__)
CORS(app,
     origins=["https://gestor.thehrkey.tech"],
     supports_credentials=True,
     methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"])



 

 

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
            'https://script.google.com/macros/s/AKfycbzovjlx3NNGR6cdbbDWY_lTsMHmHzqZ80KxVjur1bm-7UcG3EP--PRL-B209jYMIQ6C7w/exec',
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

 

@app.route("/enviar-avaliacao-arquetipos", methods=["POST", "OPTIONS"])
def enviar_avaliacao_arquetipos():
    if request.method == "OPTIONS":
        return '', 200

    import datetime
    import requests

    dados = request.get_json()
    if not dados:
        return jsonify({"erro": "Nenhum dado recebido"}), 400

    print("✅ Dados recebidos:", dados)

    try:
        # Campos obrigatórios mínimos
        empresa = dados.get("empresa", "").strip().lower()
        codrodada = dados.get("codrodada", "").strip().lower()
        emailLider = dados.get("emailLider", "").strip().lower()
        tipo = dados.get("tipo", "").strip()

        if not all([empresa, codrodada, emailLider, tipo]):
            return jsonify({"erro": "Campos obrigatórios ausentes."}), 400

        # Separar apenas respostas Q01–Q49
        respostas = {k: v for k, v in dados.items() if k.upper().startswith("Q")}

        # Montar dados_json no formato do Google Drive
        dados_json_formatado = {
            "empresa": empresa,
            "codrodada": codrodada,
            "emailLider": emailLider,
            "respostas": respostas,
            "nome": dados.get("nome", "").strip(),
            "email": dados.get("email", "").strip().lower(),
            "nomeLider": dados.get("nomeLider", "").strip(),
            "estado": dados.get("estado", "").strip(),
            "nascimento": dados.get("nascimento", "").strip(),
            "sexo": dados.get("sexo", "").strip().lower(),
            "etnia": dados.get("etnia", "").strip().lower(),
            "departamento": dados.get("departamento", "").strip(),
            "tipo": tipo,
            "data": dados.get("data", "").strip(),
            "cargo": dados.get("cargo", "").strip(),
            "area": dados.get("area", "").strip(),
            "cidade": dados.get("cidade", "").strip(),
            "pais": dados.get("pais", "").strip()
        }

        # URL da tabela de arquétipos
        url_supabase = "https://xmsjjknpnowsswwrbvpc.supabase.co/rest/v1/relatorios_arquetipos"

        headers = {
            "apikey": os.environ.get("SUPABASE_KEY"),
            "Authorization": f"Bearer {os.environ.get('SUPABASE_KEY')}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

        registro = {
            "empresa": empresa,
            "codrodada": codrodada,
            "emailLider": emailLider,
            "tipo": tipo,
            "nome": dados.get("nome", "").strip(),
            "email": dados.get("email", "").strip().lower(),
            "nomeLider": dados.get("nomeLider", "").strip(),
            "departamento": dados.get("departamento", "").strip(),
            "estado": dados.get("estado", "").strip(),
            "nascimento": dados.get("nascimento", "").strip(),
            "sexo": dados.get("sexo", "").strip().lower(),
            "etnia": dados.get("etnia", "").strip().lower(),
            "data": dados.get("data", "").strip(),
            "cargo": dados.get("cargo", "").strip(),
            "area": dados.get("area", "").strip(),
            "cidade": dados.get("cidade", "").strip(),
            "pais": dados.get("pais", "").strip(),
            "data_criacao": datetime.datetime.now().isoformat(),
            "dados_json": dados_json_formatado
        }

        print("📦 Registro sendo enviado ao Supabase:")
        print(json.dumps(registro, indent=2, ensure_ascii=False))

        resposta = requests.post(url_supabase, headers=headers, json=registro)

        if resposta.status_code == 201:
            print("✅ Avaliação de arquétipos salva no Supabase com sucesso!")
            return jsonify({"status": "✅ Arquétipos → salvo no banco de dados"}), 200
        else:
            print("❌ Erro Supabase:", resposta.status_code)
            try:
                print("❌ Corpo da resposta:", resposta.json())
            except:
                print("❌ Corpo da resposta (raw):", resposta.text)
            return jsonify({"erro": resposta.text}), 500

    except Exception as e:
        print("❌ Erro ao processar dados:", str(e))
        return jsonify({"erro": str(e)}), 500

 

 

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


@app.route("/salvar-consolidado-arquetipos", methods=["POST"])
def salvar_consolidado_arquetipos():
    try:
        import requests
        from datetime import datetime

        dados = request.get_json()
        empresa = dados.get("empresa", "").strip().lower()
        codrodada = dados.get("codrodada", "").strip().lower()
        emailLider = dados.get("emailLider", "").strip().lower()

        print(f"✅ Dados recebidos: {empresa} {codrodada} {emailLider}")
        print("🔁 Iniciando chamada ao Supabase com os dados validados...")

        supabase_url = os.environ.get("SUPABASE_REST_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")

        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json"
        }

        # 🔍 Buscar autoavaliação
        filtro_auto = f"?select=dados_json&empresa=eq.{empresa}&codrodada=eq.{codrodada}&emailLider=eq.{emailLider}&tipo=ilike.Autoavaliação"

        url_auto = f"{supabase_url}/relatorios_arquetipos{filtro_auto}"
        resp_auto = requests.get(url_auto, headers=headers)
        auto_data = resp_auto.json()
        print("📥 Resultado da requisição AUTO:", auto_data)

        if not auto_data:
            print("❌ autoavaliação não encontrada.")
            return jsonify({"erro": "autoavaliação não encontrada."}), 404

        autoavaliacao = auto_data[0]["dados_json"]

        # 🔍 Buscar avaliações de equipe (pode ser 1 ou 1000)
        filtro_equipe = f"?select=dados_json&empresa=eq.{empresa}&codrodada=eq.{codrodada}&emailLider=eq.{emailLider}&tipo=ilike.Avaliação%20Equipe"
        url_equipe = f"{supabase_url}/relatorios_arquetipos{filtro_equipe}"
        resp_equipe = requests.get(url_equipe, headers=headers)
        equipe_data = resp_equipe.json()
        print("📥 Resultado da requisição EQUIPE:", equipe_data)

        avaliacoes_equipe = [r["dados_json"] for r in equipe_data if "dados_json" in r]

        if not avaliacoes_equipe:
            print("❌ Nenhuma avaliação de equipe encontrada.")
            return jsonify({"erro": "Nenhuma avaliação de equipe encontrada."}), 404

        # 🧩 Montar JSON final
        consolidado = {
            "autoavaliacao": autoavaliacao,
            "avaliacoesEquipe": avaliacoes_equipe
        }

        # 💾 Salvar na tabela final
        payload = {
            "empresa": empresa,
            "codrodada": codrodada,
            "emaillider": emailLider,
            "dados_json": consolidado,
            "data_criacao": datetime.utcnow().isoformat(),
            "nome_arquivo": f"consolidado_{empresa}_{codrodada}_{emailLider}.json".lower()
        }

        url_final = f"{supabase_url}/consolidado_arquetipos"
        resp_final = requests.post(url_final, headers=headers, json=payload)

        if resp_final.status_code not in [200, 201]:
            print("❌ Erro ao salvar no Supabase:", resp_final.text)
            return jsonify({"erro": "Erro ao salvar consolidado."}), 500

        print("✅ Consolidado salvo com sucesso.")
        return jsonify({"mensagem": "Consolidado salvo com sucesso."})

    except Exception as e:
        print("💥 ERRO GERAL:", str(e))
        return jsonify({"erro": str(e)}), 500






if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))


 

