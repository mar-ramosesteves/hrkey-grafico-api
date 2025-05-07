@app.route('/grafico', methods=['POST'])
def gerar_grafico():
    try:
        dados = request.json
        print("📥 Dados recebidos:", dados)

        if dados.get('tipo') == 'demo':
            # Simulação estática
            arquetipos = ['Estratégico', 'Inspirador', 'Analítico', 'Executor']
            valores = [85, 70, 60, 90]
        elif dados.get('tipo') == 'real':
            email = dados.get('emailLider')
            periodo = dados.get('periodo')

            print("🔎 Procurando dados reais para:", email, "no período", periodo)

            # Aqui entra o código real de consulta (exemplo abaixo simula)
            arquetipos = ['Estratégico', 'Inspirador', 'Analítico', 'Executor']
            valores = [88, 72, 63, 91]  # ← Substitua por consulta real no futuro
        else:
            return "Tipo de gráfico inválido", 400

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


