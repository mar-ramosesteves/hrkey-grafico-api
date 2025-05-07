from flask import Flask, request, send_file
from flask_cors import CORS

import matplotlib.pyplot as plt
import io

app = Flask(__name__)

@app.route('/grafico', methods=['POST'])
def gerar_grafico():
    try:
        dados = request.json

        print("📥 Dados recebidos:", dados)

        arquetipos = dados['arquetipos']
        valores = dados['valores']

        print("✅ Arquetipos:", arquetipos)
        print("✅ Valores:", valores)

        plt.figure(figsize=(10, 6))
        plt.bar(arquetipos, valores, color='skyblue')
        plt.xlabel('Arquétipos')
        plt.ylabel('Pontuação')
        plt.title('Gráfico de Arquétipos')
        plt.tight_layout()

        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        plt.close()

        return send_file(img, mimetype='image/png')

    except Exception as e:
        print("❌ Erro ao gerar gráfico:", str(e))
        return f"Erro ao gerar gráfico: {str(e)}", 500
