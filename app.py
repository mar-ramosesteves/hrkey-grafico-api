from flask import Flask, request, send_file
import matplotlib.pyplot as plt
import io

app = Flask(__name__)

@app.route('/grafico', methods=['POST'])
def gerar_grafico():
    dados = request.json
    # Aqui você processará os dados recebidos e criará o gráfico
    # Este é um exemplo simples de gráfico de barras
    arquetipos = dados['arquetipos']
    valores = dados['valores']

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
