from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import io
import matplotlib.pyplot as plt

app = Flask(__name__)
CORS(app)  # ← Permite qualquer origem (pode depois restringir para segurança)

@app.route('/grafico', methods=['POST'])
def gerar_grafico():
    try:
        dados = request.get_json()
        print("🔍 Dados recebidos:", dados)

        # Dados de exemplo — substitua depois pela lógica real
        auto = 75
        equipe = 65
        if dados['emailLider'] == 'marceloesteves@thehrkey.tech':
            auto = 88
            equipe = 77

        fig, ax = plt.subplots()
        ax.bar(['Autoavaliação', 'Equipe'], [auto, equipe], color=['#4e79a7', '#f28e2c'])
        ax.set_ylim(0, 100)
        ax.set_title(f"Avaliação de {dados['periodo']}", fontsize=14)
        ax.set_ylabel('Pontuação (%)')

        buffer = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        plt.close()

        return send_file(buffer, mimetype='image/png')

    except Exception as e:
        print("❌ Erro ao gerar gráfico:", str(e))
        return jsonify({'erro': str(e)}), 500
