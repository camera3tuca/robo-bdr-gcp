import pandas as pd
import requests
import yfinance as yf
from datetime import datetime
import sys
import os
import numpy as np # Importa a biblioteca numpy
import warnings
from google.cloud import secretmanager
from flask import Flask

app = Flask(__name__)

# --- CONFIGURAÇÕES FIXAS DA ESTRATÉGIA CAMPEÃ ---
MME_CURTA = 12
MME_LONGA = 26
PERIODO_IFR = 14
PERIODO_MEDIA_VOLUME = 10
PERIODO_STOP_LOSS = 15
PERIODO_HISTORICO_DIAS = "120d"
TERMINACOES_BDR = ('31', '32', '33', '34', '35', '39')

# --- FUNÇÕES AUXILIARES DO ROBÔ ---

# ... (as outras funções como obter_lista_bdrs, buscar_dados, etc. permanecem as mesmas) ...
def obter_lista_bdrs_da_brapi(token: str) -> list[str]:
    # ... (código da função)
def buscar_dados_historicos_completos(tickers: list[str], periodo: str) -> pd.DataFrame:
    # ... (código da função)

# --- FUNÇÃO CORRIGIDA ---
def calcular_ifr(precos: pd.Series, periodo: int = 14) -> pd.Series:
    delta = precos.diff()
    ganhos = delta.where(delta > 0, 0)
    perdas = -delta.where(delta < 0, 0)

    media_ganhos = ganhos.ewm(com=periodo - 1, adjust=False).mean()
    media_perdas = perdas.ewm(com=periodo - 1, adjust=False).mean()

    # Lógica robusta para evitar divisão por zero
    rs = media_ganhos / media_perdas
    ifr = 100 - (100 / (1 + rs))
    
    # Se a média de perdas for 0, rs será infinito. O IFR deve ser 100.
    # Se ganhos e perdas forem 0, rs será NaN. O IFR deve ser neutro (50).
    ifr = ifr.replace([np.inf, -np.inf], 100).fillna(50)
    
    return ifr
# --- FIM DA CORREÇÃO ---

def encontrar_sinais_potenciais(df_dados: pd.DataFrame) -> list[dict]:
    # ... (código da função)
def verificar_confirmacao_intraday(sinais_potenciais: list) -> list:
    # ... (código da função)
def enviar_whatsapp(msg: str, phone: str, apikey: str):
    # ... (código da função)

# --- FUNÇÃO PRINCIPAL (PONTO DE ENTRADA DO CLOUD RUN) ---
@app.route("/")
def rodar_robo_bdr():
    # ... (código da função principal)

# --- Bloco para rodar o servidor Flask ---
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# (Para manter a resposta curta, omiti o corpo das funções que não mudaram. 
# Por favor, copie e cole o código completo abaixo)            df_ticker['MME_L'] = df_ticker['Close'].ewm(span=MME_LONGA, adjust=False).mean()
            df_ticker['IFR14'] = calcular_ifr(df_ticker['Close'], periodo=PERIODO_IFR)
            df_ticker['VolumeMedio10'] = df_ticker['Volume'].rolling(window=PERIODO_MEDIA_VOLUME).mean()
            ultimo, penultimo = df_ticker.iloc[-1], df_ticker.iloc[-2]
            if (penultimo['MME_C'] <= penultimo['MME_L'] and ultimo['MME_C'] > ultimo['MME_L'] and
                ultimo['Volume'] > (ultimo['VolumeMedio10'] * 1.2) and ultimo['IFR14'] < 70.0):
                sinal = { "BDR": ticker, "DataSinal": ultimo.name, "Preco_Entrada_Ref": ultimo['Close'], 
                          "Stop_Loss_Sugerido": df_ticker.iloc[-PERIODO_STOP_LOSS:]['Low'].min(), "MME_C_Sinal": ultimo['MME_C']}
                sinais_potenciais.append(sinal)
        except (KeyError, IndexError): continue
    print(f"-> Análise concluída. {len(sinais_potenciais)} sinal(is) potencial(is) encontrado(s).")
    return sinais_potenciais

def verificar_confirmacao_intraday(sinais_potenciais: list) -> list:
    if not sinais_potenciais: return []
    print(f"\nETAPA 4: Verificando confirmação intraday...")
    tickers_potenciais = [s['BDR'] for s in sinais_potenciais]
    dados_intraday = yf.download([f"{t}.SA" for t in tickers_potenciais], period="1d", interval="15m", progress=False, ignore_tz=True)
    if dados_intraday.empty:
        print("-> Não foi possível obter dados intraday para confirmação.")
        return []
    sinais_confirmados = []
    for sinal in sinais_potenciais:
        try:
            preco_atual = None
            ticker_sa = f"{sinal['BDR']}.SA"
            if len(tickers_potenciais) > 1:
                if ticker_sa in dados_intraday['Close'].columns:
                    preco_atual = dados_intraday['Close'][ticker_sa].dropna().iloc[-1]
            else:
                if 'Close' in dados_intraday:
                    preco_atual = dados_intraday['Close'].dropna().iloc[-1]
            if preco_atual and preco_atual > sinal['MME_C_Sinal']:
                print(f"-> ✅ SINAL CONFIRMADO para {sinal['BDR']}")
                sinais_confirmados.append(sinal)
            else:
                print(f"-> ❌ SINAL NÃO CONFIRMADO para {sinal['BDR']}")
        except Exception: continue
    print(f"-> Verificação concluída. {len(sinais_confirmados)} sinal(is) confirmado(s).")
    return sinais_confirmados

def enviar_whatsapp(msg: str, phone: str, apikey: str):
    print("\nETAPA 5: Enviando notificação para o WhatsApp...")
    try:
        texto_codificado = requests.utils.quote(msg)
        url_whatsapp = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={texto_codificado}&apikey={apikey}"
        response = requests.get(url_whatsapp, timeout=20)
        if response.status_code == 200: print("-> ✅ Notificação enviada com sucesso!")
        else: print(f"-> ⚠️ Falha no envio: {response.status_code} - {response.text}")
    except Exception as e: print(f"-> ⚠️ ERRO ao tentar enviar notificação: {e}")

# --- FUNÇÃO PRINCIPAL (PONTO DE ENTRADA DO CLOUD RUN) ---
@app.route("/")
def rodar_robo_bdr():
    warnings.simplefilter(action='ignore', category=FutureWarning)
    print(f"Iniciando Robô BDRs v3.2 em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    try:
        project_id = "prjrobobdrs01"
        client = secretmanager.SecretManagerServiceClient()
        def access_secret(secret_id):
            name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")

        whatsapp_phone = access_secret("WHATSAPP_PHONE")
        whatsapp_apikey = access_secret("WHATSAPP_APIKEY")
        brapi_api_token = access_secret("BRAPI_API_TOKEN")
        print("Chaves de API carregadas com sucesso.")
    except Exception as e:
        error_message = f"ERRO CRÍTICO ao carregar chaves do Secret Manager: {e}"
        print(error_message, file=sys.stderr)
        return error_message, 500

    lista_de_bdrs = obter_lista_bdrs_da_brapi(brapi_api_token)
    if not lista_de_bdrs: return "Finalizado: sem lista de BDRs.", 200
    
    dados_diarios = buscar_dados_historicos_completos(lista_de_bdrs, periodo=PERIODO_HISTORICO_DIAS)
    if dados_diarios.empty: 
        msg_whatsapp = f"✅ Robô BDRs ({datetime.now().strftime('%d/%m/%Y %H:%M')}) ✅\nExecução concluída. Falha ao obter dados históricos."
        enviar_whatsapp(msg_whatsapp, whatsapp_phone, whatsapp_apikey)
        return "Finalizado: sem dados históricos.", 200
        
    sinais_potenciais = encontrar_sinais_potenciais(dados_diarios)
    sinais_confirmados = verificar_confirmacao_intraday(sinais_potenciais)
    
    data_hoje_msg = datetime.now().strftime('%d/%m/%Y %H:%M')
    if sinais_confirmados:
        msg_whatsapp = f"🚨 Robô BDRs ({data_hoje_msg}) 🚨\nSinais de Compra ({MME_CURTA}x{MME_LONGA}) CONFIRMADOS:\n"
        for sinal in sinais_confirmados:
            preco_entrada_str = f"R$ {sinal['Preco_Entrada_Ref']:.2f}"
            stop_loss_str = f"R$ {sinal['Stop_Loss_Sugerido']:.2f}"
            msg_whatsapp += f"\n-> {sinal['BDR']}: Entr. {preco_entrada_str} / Stop {stop_loss_str}"
    else:
        print("Nenhum sinal de compra foi confirmado hoje.")
        msg_whatsapp = f"✅ Robô BDRs ({data_hoje_msg}) ✅\nExecução concluída. Nenhum sinal de compra foi confirmado hoje."
        
    enviar_whatsapp(msg_whatsapp, whatsapp_phone, whatsapp_apikey)
    print("Monitoramento finalizado.")
    
    return "Processo finalizado com sucesso.", 200

# --- Bloco para rodar o servidor Flask (exigido pelo Cloud Run) ---
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
