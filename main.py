from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# === CONFIGURAÇÕES ===
VERIFY_TOKEN = "sushiloko"
ACCESS_TOKEN = "EAAKhY88ZAzLUBPDzZCo65f1jedrS0uInZBMZCTlyxNdpOxxg7KjQvuVhd5ulNSLZAJ92WR2NzFBjQOj5c5ARDPjTO8OjbmS4ZBsqo6LRKrh4bQGhZBPhLHMdaKIw6xETSj1NscJmM3CldXURgGyJOZBSofvGB5X2ga8t4vrbh8px9D8FLPD3HnYUi6f3AXmkkeFDMt4ZC9r5EhrhD2Wa9H7ZCv6q3rwJpxZCplMqAoTwNrLOLAZD"
PHONE_NUMBER_ID = "697307343464625"
OPENROUTER_API_KEY = "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"
CARDAPIO_IMAGE_URL = "https://via.placeholder.com/600x400.png?text=Sushi+Loko+Cardápio"

# === DADOS TEMPORÁRIOS EM MEMÓRIA ===
clientes = {}

# === FUNÇÕES AUXILIARES ===

def enviar_mensagem(numero, texto, opcoes=None, imagem=None):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": texto}
    }

    if imagem:
        data["type"] = "image"
        data["image"] = {"link": imagem}
    elif opcoes:
        botoes = [{"type": "reply", "reply": {"id": str(i), "title": op}} for i, op in enumerate(opcoes)]
        data["type"] = "interactive"
        data["interactive"] = {
            "type": "button",
            "body": {"text": texto},
            "action": {"buttons": botoes}
        }

    requests.post(url, headers=headers, json=data)

def gerar_resposta_ia(mensagem, contexto):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "openai/gpt-3.5-turbo",
        "messages": contexto + [{"role": "user", "content": mensagem}]
    }
    try:
        resposta = requests.post(url, headers=headers, json=payload, timeout=10)
        if resposta.status_code == 200:
            return resposta.json()["choices"][0]["message"]["content"]
        elif resposta.status_code == 403:
            return "Erro: Token inválido"
        elif resposta.status_code == 401:
            return "Erro: Assinatura expirada"
        else:
            return "Erro ao acessar IA"
    except Exception as e:
        return f"Erro na requisição: {str(e)}"

def calcular_preco(pedido):
    total = 0
    if "sushi" in pedido.lower():
        total += 25
    if "temaki" in pedido.lower():
        total += 18
    if "combo" in pedido.lower():
        total += 40
    return total if total else 30

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if token == VERIFY_TOKEN:
            return str(challenge), 200
        else:
            return "Token inválido", 403

    if request.method == "POST":
        data = request.get_json()
        if data.get("object") == "whatsapp_business_account":
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    mensagem = change.get("value", {}).get("messages", [{}])[0]
                    numero = mensagem.get("from")
                    texto = mensagem.get("text", {}).get("body", "").strip().lower()

                    if not numero:
                        continue

                    if numero not in clientes:
                        clientes[numero] = {
                            "nome": None,
                            "pedido": None,
                            "endereco": None,
                            "finalizado": False,
                            "contexto": [{"role": "system", "content": "Você é um atendente simpático e divertido de um restaurante de sushi chamado SushiLoko."}]
                        }
                        enviar_mensagem(numero, "Olá! 👋 Bem-vindo ao SushiLoko 🍣", ["Mostrar cardápio"])
                        continue

                    cliente = clientes[numero]

                    if not cliente["nome"]:
                        cliente["nome"] = texto.title()
                        enviar_mensagem(numero, f"Prazer, {cliente['nome']}! Me diga seu pedido. 🍱")
                    elif not cliente["pedido"]:
                        cliente["pedido"] = texto
                        enviar_mensagem(numero, "Beleza! Agora me diga o endereço de entrega 🏡")
                    elif not cliente["endereco"]:
                        cliente["endereco"] = texto
                        preco = calcular_preco(cliente["pedido"])
                        cliente["total"] = preco
                        enviar_mensagem(numero, f"Seu pedido ficou R${preco:.2f}. Deseja finalizar?", ["Sim", "Cancelar"])
                    elif texto == "sim" and not cliente["finalizado"]:
                        cliente["finalizado"] = True
                        resumo = (
                            f"✅ Pedido finalizado:
"
                            f"📦 Pedido: {cliente['pedido']}
"
                            f"📍 Endereço: {cliente['endereco']}
"
                            f"💵 Total: R${cliente['total']:.2f}"
                        )
                        enviar_mensagem(numero, resumo + "
Obrigado pelo pedido! 😄🍣")
                    elif texto == "mostrar cardápio":
                        enviar_mensagem(numero, "Aqui está nosso cardápio:", imagem=CARDAPIO_IMAGE_URL)
                    elif cliente["finalizado"]:
                        clientes.pop(numero)
                        enviar_mensagem(numero, "Vamos recomeçar seu atendimento. Qual seu nome?")
                    else:
                        resposta = gerar_resposta_ia(texto, cliente["contexto"])
                        cliente["contexto"].append({"role": "user", "content": texto})
                        cliente["contexto"].append({"role": "assistant", "content": resposta})
                        enviar_mensagem(numero, resposta)

        return jsonify({"status": "ok"}), 200

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
