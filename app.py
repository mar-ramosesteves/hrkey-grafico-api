from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import io
import matplotlib.pyplot as plt
import pandas as pd

app = Flask(__name__)
CORS(app)

@app.route('/grafico', methods=['POST'])
def gerar_grafico():
    try:
        dados = request.get_json()
        email_lider = dados['emailLider']
        data_envio = dados['dataEnvio']  # formato 'YYYY-MM-DD'

        print("🔍 Dados recebidos:", dados)

        # 📄 Arquivos base
        arq_auto = 'form_Arquetipos_auto_aval-export-1746712137.csv'
        arq_equipe = 'form_Arquetipos_Equipe-export-1746712147.csv'
        escalas = 'ESCALAS_ARQUETIPOS.xlsx'
        maximos = 'Pontuacao_Max_por_Afirmacao_Arquetipos.xlsx'

        # 📌 Leitura dos arquivos
        df_auto = pd.read_csv(arq_auto)
        df_eq = pd.read_csv(arq_equipe)
        pesos = pd.read_excel(escalas, sheet_name='pesos')
        mapa = pd.read_excel(escalas, sheet_name='mapa')
        max_df = pd.read_excel(maximos)

        # 🧼 Filtra os dados para o líder e data
        auto = df_auto[(df_auto['emailLider'] == email_lider) & (df_auto['dataEnvio'] == data_envio)]
        equipe = df_eq[(df_eq['emailLider'] == email_lider) & (df_eq['dataEnvio'] == data_envio)]

        if auto.empty or equipe.empty:
            raise Exception("❌ Autoavaliação ou avaliações da equipe não encontradas.")

        # 🔄 Converte Q1 a Q36 para float
        perguntas = [f"Q{i}" for i in range(1, 37)]
        auto[perguntas] = auto[perguntas].astype(float)
        equipe[perguntas] = equipe[perguntas].astype(float)

        def calcular(respostas, tipo):
            linhas = []
            for q in perguntas:
                nota = respostas[q].values[0] if tipo == 'auto' else respostas[q]
                nota = nota.astype(float)

                for idx in range(len(nota)):
                    estrelas = int(nota.iloc[idx])
                    if estrelas >= 4:
                        peso = pesos.loc[pesos['Escala'] == 'Esquerda', str(estrelas)].values[0]
                    else:
                        peso = pesos.loc[pesos['Escala'] == 'Direita', str(estrelas)].values[0]

                    estilo = mapa.loc[mapa['Pergunta'] == q, 'Estilo'].values[0]
                    peso_arq = mapa.loc[mapa['Pergunta'] == q, 'Peso'].values[0]
                    max_arq = max_df.loc[(max_df['Pergunta'] == q) & (max_df['Estilo'] == estilo), 'Máximo'].values[0]

                    pontos = peso * peso_arq
                    percentual = (pontos / max_arq) * 100
                    linhas.append((estilo, percentual))

            df_resultado = pd.DataFrame(linhas, columns=['Estilo', 'Percentual'])
            return df_resultado.groupby('Estilo').mean()

        # 📊 Cálculo final
        resultado_auto = calcular(auto, 'auto')
        resultado_equipe = calcular(equipe, 'equipe')

        estilos = ['Imperativo', 'Resoluto', 'Cuidativo', 'Consultivo', 'Prescritivo', 'Formador']
        auto_vals = resultado_auto.reindex(estilos)['Percentual'].fillna(0)
        equipe_vals = resultado_equipe.reindex(estilos)['Percentual'].fillna(0)

        # 📈 Gráfico
        fig, ax = plt.subplots(figsize=(10, 6))
        x = range(len(estilos))
        ax.bar([i - 0.2 for i in x], auto_vals, width=0.4, label='Autoavaliação')
        ax.bar([i + 0.2 for i in x], equipe_vals, width=0.4, label='Equipe')

        ax.axhline(50, color='gray', linestyle='--', linewidth=1)
        ax.axhline(60, color='red', linestyle='--', linewidth=1)

        ax.set_xticks(x)
        ax.set_xticklabels(estilos)
        ax.set_ylim(0, 100)
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
        print("❌ Erro ao gerar gráfico:", str(e))
        return jsonify({'erro': str(e)}), 500

