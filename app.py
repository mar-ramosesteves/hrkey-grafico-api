from flask import Flask, request, send_file, jsonify 

from flask_cors import CORS 

import pandas as pd 

import matplotlib.pyplot as plt 

import io 

import json 

import os 

 

 

app = Flask(__name__)

# CORS global
CORS(app, resources={r"/*": {"origins": "https://gestor.thehrkey.tech"}}, supports_credentials=True)

@app.after_request
def aplicar_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "https://gestor.thehrkey.tech"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

def familia_tipo_arquetipos(tipo):
    tipo_normalizado = (tipo or "").strip().lower()
    if "auto" in tipo_normalizado:
        return "auto"
    if "equipe" in tipo_normalizado:
        return "equipe"
    return tipo_normalizado

def buscar_primeira_resposta_arquetipos(url_supabase, headers, empresa, codrodada, email_lider, tipo, email):
    params = {
        "select": "id,data_criacao,tipo",
        "empresa": f"eq.{empresa}",
        "codrodada": f"eq.{codrodada}",
        "emailLider": f"eq.{email_lider}",
        "email": f"eq.{email}",
        "order": "data_criacao.asc",
    }
    resposta = requests.get(url_supabase, headers=headers, params=params, timeout=30)
    if resposta.status_code != 200:
        print("Erro ao verificar duplicidade no Supabase:", resposta.status_code, resposta.text)
        return None
    dados = resposta.json()
    familia_alvo = familia_tipo_arquetipos(tipo)
    for registro in dados:
        if familia_tipo_arquetipos(registro.get("tipo")) == familia_alvo:
            return registro
    return None

def primeiras_respostas_arquetipos_por_email(registros):
    primeiras = {}
    for registro in sorted(registros, key=lambda r: r.get("data_criacao") or ""):
        dados_json = registro.get("dados_json") or {}
        email = (dados_json.get("email") or registro.get("email") or "").strip().lower()
        if email and email not in primeiras:
            primeiras[email] = dados_json
    return list(primeiras.values())



 

 

# Carrega a matriz de cÃ¡lculo com a coluna CHAVE 

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

                raise Exception("Formato de JSON em 'entries' invÃ¡lido.") 

 

        if not dados: 

            raise Exception("Nenhum dado recebido.") 

        print("ðŸ“¦ Dados recebidos (apÃ³s unpack):", dados) 

 

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

            raise Exception("Nenhuma resposta vÃ¡lida encontrada para gerar o grÃ¡fico.") 

 

        df_result = pd.DataFrame(linhas, columns=["ARQUETIPO", "PONTOS_OBTIDOS", "PONTOS_MAXIMOS"]) 

        resumo = df_result.groupby("ARQUETIPO").sum() 

        resumo["PERCENTUAL"] = (resumo["PONTOS_OBTIDOS"] / resumo["PONTOS_MAXIMOS"]) * 100 

        resumo["PERCENTUAL"] = resumo["PERCENTUAL"].round(4) 

 

        resumo = resumo.reindex(arquetipos) 

 

        email_lider = dados.get("emailLider", "N/D") 

        data_envio = dados.get("data", "N/D") 

 

        # GrÃ¡fico atualizado 

        fig, ax = plt.subplots(figsize=(10, 6)) 

        bars = ax.bar(resumo.index, resumo["PERCENTUAL"], color='skyblue') 

 

        for bar in bars: 

            height = bar.get_height() 

            ax.text(bar.get_x() + bar.get_width() / 2, height + 1, f'{height:.1f}%', ha='center', va='bottom') 

 

        ax.axhline(50, color='gray', linestyle='--', linewidth=1, label='50% (Suporte)') 

        ax.axhline(60, color='red', linestyle='--', linewidth=1, label='60% (Dominante)') 

 

        ax.set_ylim(0, 100) 

        ax.set_ylabel('PontuaÃ§Ã£o (%)') 

        ax.set_title(f"AUTOAVALIAÃ‡ÃƒO - ARQUÃ‰TIPOS DE LIDERANÃ‡A\nRespondente: {email_lider} | Data: {data_envio}", fontsize=13) 

        ax.legend() 

        plt.xticks(rotation=0) 

 

        buf = io.BytesIO() 

        plt.tight_layout() 

        plt.savefig(buf, format="png") 

        buf.seek(0) 

        plt.close() 

 

        return send_file(buf, mimetype="image/png") 

 

    except Exception as e: 

        print("âŒ Erro:", str(e)) 

        return jsonify({"erro": str(e)}), 500 

 

@app.route("/") 

def home(): 

    return "ðŸŽ¯ API de GrÃ¡ficos de ArquÃ©tipos estÃ¡ ativa!" 

 

 

 

@app.route("/relatorio", methods=["POST"]) 

def relatorio_detalhado(): 

    try: 

        dados = request.get_json() 

        if not dados: 

            raise Exception("Nenhum dado recebido.") 

 

        # Carrega a matriz principal (com tendÃªncia) 

        matriz = pd.read_excel("TABELA_GERAL_ARQUETIPOS_COM_CHAVE.xlsx") 

 

        # Carrega as frases corretas da autoavaliaÃ§Ã£o 

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

 

            top2 = matches.sort_values(by="% TendÃªncia", ascending=False).head(2) 

            arqs = top2["ARQUETIPO"].tolist() 

            tendencia = top2["TendÃªncia"].values[0] 

            percentual = top2["% TendÃªncia"].values[0] 

 

            frase = frases_dict.get(cod, cod)  # Busca no dicionÃ¡rio correto 

 

            linhas.append({ 

                "codigo": cod, 

                "frase": frase, 

                "percentual": round(percentual, 3), 

                "tendencia": tendencia, 

                "arquetipos": arqs 

            }) 

 

        return jsonify({"resultado": linhas}) 

 

    except Exception as e: 

        print("âŒ Erro no /relatorio:", str(e)) 

        return jsonify({"erro": str(e)}), 500 

 

 

 

@app.route('/grafico-equipe', methods=['POST']) 

def grafico_equipe(): 

    dados = request.get_json() 

    email = dados.get('emailLider') 

    data = dados.get('data') 

 

    # Caminho do CSV com dados da equipe 

    df = pd.read_csv('avaliacao_equipes.csv') 

 

    # Filtrar pelas entradas do lÃ­der e data 

    df_filtrado = df[(df['emailLider'] == email) & (df['data'] == data)] 

 

    if df_filtrado.empty: 

        return jsonify({'erro': 'Nenhuma avaliaÃ§Ã£o encontrada para esse lÃ­der e data.'}), 404 

 

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

            peso = 0  # seguranÃ§a 

 

        percentual = round((peso / 2) * 100, 1) 

 

        resultados.append({ 

            'cod_afirmacao': cod, 

            'percentual': percentual 

        }) 

 

        # Gerar grÃ¡fico 

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

 

    return jsonify({'mensagem': 'GrÃ¡ficos gerados com sucesso!', 'total': len(resultados)}) 

 

 

 

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

        if "jÃ¡ enviou" in texto:
            return jsonify({
                'status': 'duplicado',
                'mensagem': texto
            }), 409

        return jsonify({
            'status': 'ok',
            'mensagem': texto
        }), 200

    except Exception as e:
        print("âŒ Erro ao enviar para Google Script:", str(e))
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

    print("âœ… Dados recebidos:", dados)

    try:
        # Campos obrigatÃ³rios mÃ­nimos
        empresa = dados.get("empresa", "").strip().lower()
        codrodada = dados.get("codrodada", "").strip().lower()
        emailLider = dados.get("emailLider", "").strip().lower()
        tipo = dados.get("tipo", "").strip()
        email = dados.get("email", "").strip().lower()

        if not all([empresa, codrodada, emailLider, tipo, email]):
            return jsonify({"erro": "Campos obrigatÃ³rios ausentes."}), 400

        # Separar apenas respostas Q01â€“Q49
        respostas = {k: v for k, v in dados.items() if k.upper().startswith("Q")}

        # Montar dados_json no formato do Google Drive
        dados_json_formatado = {
            "empresa": empresa,
            "codrodada": codrodada,
            "emailLider": emailLider,
            "respostas": respostas,
            "nome": dados.get("nome", "").strip(),
            "email": email,
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

        # URL da tabela de arquÃ©tipos
        url_supabase = "https://xmsjjknpnowsswwrbvpc.supabase.co/rest/v1/relatorios_arquetipos"

        headers = {
            "apikey": os.environ.get("SUPABASE_KEY"),
            "Authorization": f"Bearer {os.environ.get('SUPABASE_KEY')}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

        resposta_existente = buscar_primeira_resposta_arquetipos(
            url_supabase,
            headers,
            empresa,
            codrodada,
            emailLider,
            tipo,
            email
        )

        if resposta_existente:
            return jsonify({
                "erro": "inventario_ja_respondido",
                "mensagem": "Este inventario ja foi respondido anteriormente.",
                "data_criacao": resposta_existente.get("data_criacao")
            }), 409

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

        print("ðŸ“¦ Registro sendo enviado ao Supabase:")
        print(json.dumps(registro, indent=2, ensure_ascii=False))

        resposta = requests.post(url_supabase, headers=headers, json=registro)

        if resposta.status_code == 201:
            print("âœ… AvaliaÃ§Ã£o de arquÃ©tipos salva no Supabase com sucesso!")
            return jsonify({"status": "âœ… ArquÃ©tipos â†’ salvo no banco de dados"}), 200
        else:
            print("âŒ Erro Supabase:", resposta.status_code)
            try:
                print("âŒ Corpo da resposta:", resposta.json())
            except:
                print("âŒ Corpo da resposta (raw):", resposta.text)
            return jsonify({"erro": resposta.text}), 500

    except Exception as e:
        print("âŒ Erro ao processar dados:", str(e))
        return jsonify({"erro": str(e)}), 500

 

 

@app.route("/verificar-avaliacao-arquetipos", methods=["POST", "OPTIONS"])
def verificar_avaliacao_arquetipos():
    if request.method == "OPTIONS":
        return '', 200

    dados = request.get_json() or {}
    empresa = dados.get("empresa", "").strip().lower()
    codrodada = dados.get("codrodada", "").strip().lower()
    emailLider = dados.get("emailLider", "").strip().lower()
    tipo = dados.get("tipo", "").strip()
    email = dados.get("email", "").strip().lower()

    if not all([empresa, codrodada, emailLider, tipo, email]):
        return jsonify({"erro": "Campos obrigatorios ausentes."}), 400

    supabase_url = os.environ.get("SUPABASE_REST_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        return jsonify({"erro": "Supabase nao configurado."}), 500

    url_supabase = f"{supabase_url}/relatorios_arquetipos"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json"
    }

    resposta_existente = buscar_primeira_resposta_arquetipos(
        url_supabase,
        headers,
        empresa,
        codrodada,
        emailLider,
        tipo,
        email
    )

    if resposta_existente:
        return jsonify({
            "respondido": True,
            "mensagem": "Este inventario ja foi respondido anteriormente.",
            "data_criacao": resposta_existente.get("data_criacao")
        }), 200

    return jsonify({"respondido": False}), 200


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

            return jsonify({"status": "erro", "mensagem": "Campos obrigatÃ³rios ausentes."}), 400 

 

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

            return jsonify({"status": "erro", "mensagem": "Campos obrigatÃ³rios ausentes."}), 400 

 

        nome_arquivo = f"{email}_{tipo}.json" 

        caminho = f"Avaliacoes RH/{empresa}/{codrodada}/{emailLider}/{nome_arquivo}" 

        full_path = os.path.join("/mnt/data", caminho) 

 

        if os.path.exists(full_path): 

            return jsonify({"status": "bloqueado"}) 

        else: 

            return jsonify({"status": "liberado"}) 

 

    except Exception as e: 

        return jsonify({"status": "erro", "mensagem": str(e)}), 500 


@app.route("/salvar-consolidado-arquetipos", methods=["POST", "OPTIONS"])
def salvar_consolidado_arquetipos():
    if request.method == "OPTIONS":
        # Resposta rÃ¡pida sÃ³ para o preflight CORS
        return '', 204

    try:


     
        import requests
        from datetime import datetime

        dados = request.get_json()
        empresa = dados.get("empresa", "").strip().lower()
        codrodada = dados.get("codrodada", "").strip().lower()
        emailLider = dados.get("emailLider", "").strip().lower()

        print(f"âœ… Dados recebidos: {empresa} {codrodada} {emailLider}")
        print("ðŸ” Iniciando chamada ao Supabase com os dados validados...")

        supabase_url = os.environ.get("SUPABASE_REST_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")

        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json"
        }

        # Buscar respostas do lÃ­der sem depender de acento/codificaÃ§Ã£o do campo tipo.
        url_respostas = f"{supabase_url}/relatorios_arquetipos"
        resp_respostas = requests.get(url_respostas, headers=headers, params={
            "select": "dados_json,tipo,email,data_criacao",
            "empresa": f"eq.{empresa}",
            "codrodada": f"eq.{codrodada}",
            "emailLider": f"eq.{emailLider}",
            "order": "data_criacao.asc",
            "limit": "10000",
        }, timeout=30)

        if resp_respostas.status_code != 200:
            print("Erro ao consultar respostas de arquetipos:", resp_respostas.status_code, resp_respostas.text)
            return jsonify({"erro": "Erro ao consultar respostas de arquetipos.", "detalhe": resp_respostas.text}), 500

        respostas_data = resp_respostas.json() or []
        print("Resultado da requisiÃ§Ã£o ARQUETIPOS:", respostas_data)

        auto_data = [
            row for row in respostas_data
            if familia_tipo_arquetipos(row.get("tipo")) == "auto"
        ]

        if not auto_data:
            print("autoavaliacao nao encontrada.")
            return jsonify({"erro": "autoavaliacao nao encontrada."}), 404

        autoavaliacao = auto_data[0]["dados_json"]

        equipe_data = [
            row for row in respostas_data
            if familia_tipo_arquetipos(row.get("tipo")) == "equipe"
        ]
        avaliacoes_equipe = primeiras_respostas_arquetipos_por_email(equipe_data)

        if not avaliacoes_equipe:
            print("âŒ Nenhuma avaliaÃ§Ã£o de equipe encontrada.")
            return jsonify({"erro": "Nenhuma avaliaÃ§Ã£o de equipe encontrada."}), 404

        # ðŸ§© Montar JSON final
        consolidado = {
            "autoavaliacao": autoavaliacao,
            "avaliacoesEquipe": avaliacoes_equipe
        }

        # ðŸ’¾ Salvar na tabela final
        payload = {
            "empresa": empresa,
            "codrodada": codrodada,
            "emaillider": emailLider,
            "dados_json": consolidado,
            "data_criacao": datetime.utcnow().isoformat(),
            "nome_arquivo": f"consolidado_{empresa}_{codrodada}_{emailLider}.json".lower()
        }

        url_final = f"{supabase_url}/consolidado_arquetipos"
        filtro_existente = {
            "select": "id",
            "empresa": f"eq.{empresa}",
            "codrodada": f"eq.{codrodada}",
            "emaillider": f"eq.{emailLider}",
            "order": "data_criacao.desc",
            "limit": "1"
        }
        resp_existente = requests.get(url_final, headers=headers, params=filtro_existente, timeout=30)

        if resp_existente.status_code != 200:
            print("Erro ao verificar consolidado existente:", resp_existente.text)
            return jsonify({"erro": "Erro ao verificar consolidado existente."}), 500

        existentes = resp_existente.json() or []

        if existentes:
            consolidado_id = existentes[0].get("id")
            url_update = f"{url_final}?id=eq.{consolidado_id}"
            resp_final = requests.patch(url_update, headers=headers, json=payload, timeout=30)
            acao = "atualizado"
        else:
            resp_final = requests.post(url_final, headers=headers, json=payload, timeout=30)
            acao = "criado"

        if resp_final.status_code not in [200, 201, 204]:
            print("âŒ Erro ao salvar no Supabase:", resp_final.text)
            return jsonify({"erro": "Erro ao salvar consolidado."}), 500

        print("âœ… Consolidado salvo com sucesso.")
        return jsonify({"mensagem": "Consolidado salvo com sucesso."})

    except Exception as e:
        print("ðŸ’¥ ERRO GERAL:", str(e))
        return jsonify({"erro": str(e)}), 500






if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))


 

