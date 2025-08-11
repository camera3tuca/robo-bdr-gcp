import os
import requests
from flask import Flask
from datetime import datetime

app = Flask(__name__)

# Suas chaves (fixas para o teste — substitua se necessário, mas use as do seu setup)
WHATSAPP_PHONE = "+556299755774"  # Seu número com código do país
WHATSAPP_APIKEY = "9675989"  # Sua API key do CallMeBot
TELEGRAM_BOT_TOKEN = "8261089588:AAGYyH2xCBglasTU0Yx2N7DOMDWBt4kijkE"
TELEGRAM_CHAT_ID = "7991966793"

@app.route("/")
def run_connectivity_tests():
    """
    Executa testes de conexão com as APIs de notificação, incluindo um teste neutro.
    """
    timestamp = datetime.now().strftime('%d/%m %H:%M:%S')
    results = f"--- Resultados do Teste de Conexão ({timestamp}) ---\n\n"
    
    # Teste 0: Conexão neutra para confirmar outbound HTTP (deve funcionar sempre)
    print("Testando Conexão Neutra com Google.com...")
    try:
        response_google = requests.get("https://www.google.com", timeout=5)
        results += f"-> Google.com: SUCESSO - Status {response_google.status_code}\n"
        print(f"-> Google.com respondeu com status: {response_google.status_code}")
    except Exception as e:
        results += f"-> Google.com: FALHA NA CONEXÃO - {e}\n"
        print(f"-> Falha na conexão com Google.com: {e}")

    # Teste 1: CallMeBot (WhatsApp)
    print("\nTestando Conexão com CallMeBot (WhatsApp)...")
    try:
        url_whatsapp = f"https://api.callmebot.com/whatsapp.php?phone={WHATSAPP_PHONE}&text=Teste_de_Conexao_do_Google_Cloud_{timestamp}&apikey={WHATSAPP_APIKEY}"
        response_wp = requests.get(url_whatsapp, timeout=15)
        results += f"-> WhatsApp (CallMeBot): SUCESSO - Status {response_wp.status_code}\n"
        print(f"-> CallMeBot respondeu com status: {response_wp.status_code}")
    except Exception as e:
        results += f"-> WhatsApp (CallMeBot): FALHA NA CONEXÃO - {e}\n"
        print(f"-> Falha na conexão com CallMeBot: {e}")

    # Teste 2: Telegram (usando requests diretamente, como no navegador)
    print("\nTestando Conexão com Telegram (via HTTP direto)...")
    try:
        url_telegram = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text=Teste_de_Conexao_do_Google_Cloud_{timestamp}"
        response_tg = requests.get(url_telegram, timeout=15)
        response_tg.raise_for_status()  # Levanta erro se não for 200
        results += f"-> Telegram (HTTP direto): SUCESSO - Status {response_tg.status_code}\n"
        print(f"-> Telegram respondeu com status: {response_tg.status_code}")
    except Exception as e:
        results += f"-> Telegram (HTTP direto): FALHA NA CONEXÃO - {e}\n"
        print(f"-> Falha na conexão com Telegram: {e}")

    # Retorna o resultado para ser exibido no navegador
    return f"<pre>{results}</pre>", 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
