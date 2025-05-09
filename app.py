from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import pandas as pd
import matplotlib.pyplot as plt
import io

app = Flask(__name__)
CORS(app)

# Carrega a matriz com CHAVE pronta
matriz = pd.read_csv('tabela_arquétipos_com_chave.csv')

@app.route('/grafico', methods=['POST'])
def gerar_grafico():
    try:
        dados = request.get_json()
        email_lider = dados['emailLider']
        data_envio = dados['dataEnvio']

        # CSVs exportados do WordPress (MetForm)
        df_auto = pd.read_csv('form_Arquetipos_auto_aval-export-1746712137.csv')
        df_equipe = pd.read_csv('form_Arquetipos_Equipe-export-1746712147.csv')

        # Filtrar por e-mail do líder e data
        auto = df_auto[(df_auto['emailLider'] == email_lider) & (df_auto['data'] == data_envio)]
        equipe = df_equipe[(df_equipe['emailLider'] == email_lider) & (df_equipe['data'] == data_envio)]

        if auto.empty or equipe.empty:
            raise Exception("❌ Não foram encontradas respostas para essa data ou esse líder.")

        perguntas = [f"Q{str(i).zfill(2)}" for i in range(1, 37)]

        def gerar_chaves(df, tipo):
            linhas = []
            for _, linha in df.iterrows():
                for cod in perguntas:
                    nota = int(linha[cod])
                    for arq in matriz['ARQUETIPO'].unique():
                        chave = f"{arq}{nota}{cod}"
                        match = matriz[matriz['CHAVE'] == chave]
                        if not match.empty:
                            pontos = match.iloc[0]['PONTOS_OBTIDOS']
                            maximo = match.iloc[0]['PONTOS_MAXIMOS']
                            linhas.append((arq, pontos, maximo))
            return pd.DataFrame(linhas, columns=['ARQUETIPO', 'PONTOS_OBTIDOS', 'PONTOS_MAXIMOS'])

        df_auto_result = gerar_chaves(auto, 'auto')
        df_eq_result = gerar_chaves(equipe, 'equipe')

        auto_grouped = df_auto_result.groupby('ARQUETIPO').sum()
        equipe_grouped = df_eq_result.groupby('ARQUETIPO').sum()

        auto_grouped['PERCENTUAL'] = (auto_grouped['PONTOS_OBTIDOS'] / auto_grouped['PONTOS_MAXIMOS']) * 100
        equipe_grouped['PERCENTUAL'] = (equipe_grouped['PONTOS_OBTIDOS'] / equipe_grouped['PONTOS_MAXIMOS']) * 100

        estilos = matriz['ARQUETIPO'].unique().tolist()
        auto_vals = auto_grouped.reindex(estilos)['PERCENTUAL'].fillna(0)
        equipe_vals = equipe_grouped.reindex(estilos)['PERCENTUAL'].fillna(0)

        # Gráfico
        fig, ax = plt.subplots(figsize=(10, 6))
        x = range(len(estilos))
        ax.bar([i - 0.2 for i in x], auto_vals, width=0.4, label='Autoavaliação')
        ax.bar([i + 0.2 for i in x], equipe_vals, width=0.4, label='Equipe')

        ax.axhline(50, color='gray', linestyle='--', linewidth=1)
        ax.axhline(60, color='red', linestyle='--', linewidth=1)

        ax.set_xticks(x)
        ax.set_xticklabels(estilos)
        ax.set_ylim(0, 120)
        ax.set_ylabel('Pontuação (%)')
        ax.set_title(f"ARQUÉTIPOS DE GESTÃO\nLíder: {email_lider} | Data: {data_envio}\n{len(equipe)} avaliações da equipe", fontsize=12)
        ax.legend()

        buffer = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        plt.close()

        return send_file(buffer, mimetype='image/png')

    except Exception as e:
        print("❌ Erro:", str(e))
        return jsonify({'erro': str(e)}), 500

@app.route('/')
def home():
    return "API de Arquétipos VIVA no Render! 💥"
