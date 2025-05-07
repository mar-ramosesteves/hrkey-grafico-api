from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io
import matplotlib.pyplot as plt

app = FastAPI()

class Avaliacao(BaseModel):
    email: str
    lider: str
    empresa: str
    tipo: str
    respostas: dict

# Tabela de pesos
escala_pesos = {
    1: ("DIREITA", 2),
    2: ("DIREITA", 1.5),
    3: ("DIREITA", 1),
    4: ("ESQUERDA", 1),
    5: ("ESQUERDA", 1.5),
    6: ("ESQUERDA", 2)
}

# Exemplo de escala simplificada
from ESCALAS import ESCALAS  # Arquivo separado com os dados de pontuação por questão

@app.post("/grafico")
async def gerar_grafico(dados: Avaliacao):
    pontuacoes = {
        'Imperativo': 0,
        'Resoluto': 0,
        'Cuidativo': 0,
        'Consultivo': 0,
        'Prescritivo': 0,
        'Formador': 0
    }

    for q, val in dados.respostas.items():
        if q not in ESCALAS: continue
        lado, peso = escala_pesos.get(val, ("ESQUERDA", 1))
        for arquétipo in pontuacoes:
            pontuacoes[arquétipo] += ESCALAS[q][lado][arquétipo] * peso

    # Máximos fixos por arquétipo
    maximos = {
        'Imperativo': 86,
        'Resoluto': 94,
        'Cuidativo': 92,
        'Consultivo': 95,
        'Prescritivo': 90,
        'Formador': 96
    }

    percentuais = {k: round((v / maximos[k]) * 100, 1) for k, v in pontuacoes.items()}

    fig, ax = plt.subplots(figsize=(9, 5))
    nomes = list(percentuais.keys())
    valores = list(percentuais.values())

    bars = ax.bar(nomes, valores)
    ax.axhline(50, color='gray', linestyle='--', linewidth=1)
    ax.axhline(60, color='green', linestyle='--', linewidth=1)

    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, height + 1, f'{height:.1f}%', ha='center', fontsize=10)

    ax.set_ylim(0, 100)
    ax.set_ylabel('Pontuação (%)')
    ax.set_title(f"Arquétipos – {dados.lider} ({dados.empresa})")

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png')
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
