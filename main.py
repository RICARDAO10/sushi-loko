import os
import json
import requests
from flask import Flask, request
from openai import OpenAI

app = Flask(__name__)

# Dados sensíveis (use variáveis de ambiente no Railway se preferir)
TOKEN = os.getenv("EAAKhY88ZAzLUBPIrvbnhimEVCmZCK0dJOsxrAVvANEe74ZAxAO0mqB89NzxPBK4WeWHB1iYSsBbE2WrIyOkSDJUEgaiFJ8zjAhFJqcwb5PRvMmgmBMZB2axfUIdAXZAZChfFxHE5ZCIZBz4FxSwHWv9ILuT8bqOCI8LoJDqlkaTBZAO1nCZCppLuwevRY1trNA4tKubkP3YERVVfLJEioBiNbxF83jMF0fJCFJkEZBUpl0X2gZDZD") or "SEU_TOKEN_DO_WHATSAPP"
ID_TELEFONE = os.getenv("697307343464625") or "SEU_ID_DE_TELEFONE"
IA_TOKEN = os.getenv("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") or "SEU_TOKEN_OPENROUTER"

# Dicionário para armazenar os estados dos clientes
clientes = {}

@app.route("/", methods=["GET"])
def verificar():
    token = request.args.get("hub.verify_token")
    desafio = request.args.get("hub.challenge")
    if token == "123456r":
        return desafio
    return "Token inválido", 403

@app.route("/", methods=["POST"])
def receber():
    body = request.json
    try:
        mensagem = body["entry"][0]["changes"][0]["value"]["messages"][0]
        texto = mensagem.get("text", {}).get("body") or mensagem.get("button", {}).get("payload")
        numero = mensagem["from"]

        if numero not in clientes:
            clientes[numero] = {
                "nome": "",
                "pedido": "",
                "endereco": "",
                "total": 0.0,
                "finalizado": False
            }

        cliente = clientes[numero]

        if not cliente["nome"]:
            cliente["nome"] = texto
            enviar_mensagem(numero, f"Oi {cliente['nome']}! 😄 Que bom ter você aqui no Sushi Loko! 🍣")
            enviar_mensagem_com_botao(numero, "Clique abaixo para ver nosso cardápio:", "Ver Cardápio")
        elif texto.lower() == "ver cardápio":
            enviar_imagem(numero, "https://i.imgur.com/VWUgO1a.png", "📸 Este é o nosso cardápio!")
            enviar_mensagem(numero, "Digite o que você deseja pedir:")
        elif not cliente["pedido"]:
            cliente["pedido"] = texto
            cliente["total"] = calcular_total(texto)
            enviar_mensagem(numero, "Ótimo! Agora me diga seu endereço de entrega 🏠:")
        elif not cliente["endereco"]:
            cliente["endereco"] = texto
            resumo = (
                f"✅ Pedido finalizado:\n"
                f"📦 Pedido: {cliente['pedido']}\n"
                f"📍 Endereço: {cliente['endereco']}\n"
                f"💵 Total: R${cliente['total']:.2f}"
            )
            enviar_mensagem(numero, resumo + "\n\nConfirma o pedido? Clique abaixo:")
            enviar_botoes(numero, "Confirmar pedido?", ["Sim", "Cancelar"])
        elif texto.lower() in ["sim", "0"] and not cliente["finalizado"]:
            cliente["finalizado"] = True
            resumo = (
                f"✅ Pedido finalizado:\n"
                f"📦 Pedido: {cliente['pedido']}\n"
                f"📍 Endereço: {cliente['endereco']}\n"
                f"💵 Total: R${cliente['total']:.2f}"
            )
            enviar_mensagem(numero, resumo + "\nObrigado pelo pedido! 😄🍣")
        elif texto.lower() in ["cancelar", "1"] and not cliente["finalizado"]:
            enviar_mensagem(numero, "Pedido cancelado 😢 Se quiser fazer um novo, é só digitar novamente.")
            clientes.pop(numero)
        elif cliente["finalizado"]:
            clientes.pop(numero)
            enviar_mensagem(numero, "Se quiser fazer um novo pedido, digite seu nome 📝:")
        else:
            resposta = consultar_ia(texto)
            enviar_mensagem(numero, resposta)

    except Exception as e:
        print("Erro ao processar mensagem:", e)

    return "ok", 200

def enviar_mensagem(numero, texto):
    url = f"https://graph.facebook.com/v19.0/{ID_TELEFONE}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": texto}
    }
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    requests.post(url, headers=headers, json=payload)

def enviar_imagem(numero, link, texto):
    url = f"https://graph.facebook.com/v19.0/{ID_TELEFONE}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "image",
        "image": {
            "link": link,
            "caption": texto
        }
    }
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    requests.post(url, headers=headers, json=payload)

def enviar_mensagem_com_botao(numero, texto, titulo_botao):
    url = f"https://graph.facebook.com/v19.0/{ID_TELEFONE}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": texto},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {"id": titulo_botao.lower(), "title": titulo_botao}
                    }
                ]
            }
        }
    }
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    requests.post(url, headers=headers, json=payload)

def enviar_botoes(numero, texto, opcoes):
    botoes = []
    for i, opcao in enumerate(opcoes):
        botoes.append({
            "type": "reply",
            "reply": {"id": str(i), "title": opcao}
        })

    url = f"https://graph.facebook.com/v19.0/{ID_TELEFONE}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": texto},
            "action": {"buttons": botoes}
        }
    }
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    requests.post(url, headers=headers, json=payload)

def calcular_total(pedido):
    menu = {
        "sushi": 20,
        "temaki": 25,
        "hot roll": 18,
        "combo": 50,
        "yakisoba": 30
    }
    total = 0
    pedido = pedido.lower()
    for item, preco in menu.items():
        if item in pedido:
            total += preco
    return total

def consultar_ia(pergunta):
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=IA_TOKEN
    )
    resposta = client.chat.completions.create(
        model="openchat/openchat-7b",
        messages=[
            {"role": "system", "content": "Você é um atendente do restaurante Sushi Loko. Seja simpático, informal e ajude com pedidos."},
            {"role": "user", "content": pergunta}
        ]
    )
    return resposta.choices[0].message.content.strip()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
