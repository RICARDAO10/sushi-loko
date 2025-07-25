import os
import json
import requests
from flask import Flask, request
from openai import OpenAI

app = Flask(__name__)

# Tokens e IDs via variáveis de ambiente
TOKEN = os.getenv("TOKEN")
ID_TELEFONE = os.getenv("ID_TELEFONE")
IA_TOKEN = os.getenv("OPENAI_API_KEY")  # Corrigido aqui

# Inicialização do cliente OpenAI via OpenRouter
client = OpenAI(
    api_key=IA_TOKEN,
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "https://zapmaster.ai",
        "X-Title": "ZapMaster"
    }
)

# Rota principal (GET e POST do webhook)
@app.route("/webhook", methods=["GET", "POST"])
def receber():
    if request.method == "GET":
        # Verificação de webhook
        if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == "123456":
            return request.args.get("hub.challenge"), 200
        return "Erro na verificação", 403

    if request.method == "POST":
        body = request.json

        try:
            # Proteção: nem toda requisição POST tem mensagens
            if "messages" not in body["entry"][0]["changes"][0]["value"]:
                return "ok", 200

            mensagens = body["entry"][0]["changes"][0]["value"]["messages"]
            for mensagem in mensagens:
                texto = mensagem.get("text", {}).get("body", "").lower()
                numero = mensagem["from"]
                nome = mensagem["profile"]["name"]

                if texto in ["ver cardápio", "ver cardapio"]:
                    enviar_imagem(numero)
                else:
                    resposta = gerar_resposta_ia(texto, nome)
                    enviar_mensagem(resposta, numero)

        except Exception as e:
            print("Erro ao processar mensagem:", e)
            print("Body recebido:", json.dumps(body, indent=2))
            return "erro", 200

        return "ok", 200

# Envia mensagem de texto
def enviar_mensagem(texto, numero):
    url = f"https://graph.facebook.com/v18.0/{ID_TELEFONE}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": texto}
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        print("Erro ao enviar mensagem:", response.text)

# Envia imagem do cardápio
def enviar_imagem(numero):
    url = f"https://graph.facebook.com/v18.0/{ID_TELEFONE}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "image",
        "image": {
            "link": "https://i.imgur.com/mzbdFQ6.jpeg",
            "caption": "🍣 Cardápio do Sushi Loko"
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        print("Erro ao enviar imagem:", response.text)

# Gera resposta usando IA do OpenRouter
def gerar_resposta_ia(texto, nome):
    mensagem_padrao = (
        f"Você é o atendente virtual do restaurante Sushi Loko. "
        f"Fale com simpatia e de forma descontraída com o cliente chamado {nome}. "
        f"Ajude ele a fazer um pedido com base no cardápio, pergunte se for preciso. "
        f"Se ele pedir algo, pergunte o nome completo e o endereço de entrega. "
        f"Nunca invente informações. "
        f"O que o cliente falou foi: \"{texto}\""
    )

    resposta = client.chat.completions.create(
        model="openchat/openchat-7b:free",
        messages=[{"role": "user", "content": mensagem_padrao}],
        temperature=0.7
    )
    return resposta.choices[0].message.content.strip()

# Inicializa servidor local/Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
