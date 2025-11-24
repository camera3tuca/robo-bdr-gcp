# ====================================================================================
# PROJETO BDR GAP TRACKER v1.12 (VERSÃO VS Code / GitHub Actions)
# DESCRIÇÃO: 100% yfinance. Adaptado para automação.
#            Lê secrets de variáveis de ambiente.
#            Salva ficheiros na pasta local (./)
# ====================================================================================

# --- ETAPA 0: IMPORTS ---
print("Importando bibliotecas...")
import pandas as pd
import requests
import yfinance as yf
import numpy as np
from datetime import datetime
import pytz
import time
import json
import os # <-- Importante para ler as variáveis de ambiente
import warnings
import nltk 

# Tenta verificar o léxico
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
    print("Léxico VADER verificado.")
except LookupError:
    print("Léxico VADER não encontrado. O script de automação (workflow) deve instalá-lo.")

warnings.simplefilter(action='ignore', category=FutureWarning)
pd.options.mode.chained_assignment = None

# --- CONFIGURAÇÕES GERAIS (LENDO DO AMBIENTE!) ---
print("Carregando configurações das Variáveis de Ambiente...")
WHATSAPP_PHONE = os.environ.get("WHATSAPP_PHONE")
WHATSAPP_APIKEY = os.environ.get("WHATSAPP_APIKEY")
BRAPI_API_TOKEN = os.environ.get("BRAPI_API_TOKEN")

if not all([WHATSAPP_PHONE, WHATSAPP_APIKEY, BRAPI_API_TOKEN]):
    print("!!! ALERTA: Faltam variáveis de ambiente!")
else:
    print("Variáveis de ambiente carregadas com sucesso.")

# --- CONFIGURAÇÕES GLOBAIS ---
TOP_N_GAPS_FASE1 = 20
TOP_N_TRACKING_FASE2 = 10
BDRS_POR_MENSAGEM_FASE1 = 10 
LOCAL_FILE_PREFIX = "./top_gaps_data_" # <<< CORREÇÃO: Salvar na pasta local
TERMINACOES_BDR = ('34',) 

# --- FUNÇÕES AUXILIARES ---

def obter_lista_bdrs_da_brapi() -> list[dict]:
    print("\nETAPA 1: Buscando lista completa de BDRs e Nomes (via Brapi)...")
    bdrs_com_nome = []
    if not BRAPI_API_TOKEN: print("-> ERRO: BRAPI_API_TOKEN não config."); return []
    url = f"https://brapi.dev/api/quote/list?token={BRAPI_API_TOKEN}"
    try:
        response = requests.get(url, timeout=60); response.raise_for_status()
        dados = response.json().get('stocks', [])
        for d in dados:
            ticker = d.get('stock'); nome = d.get('name')
            if ticker and nome and ticker.endswith(TERMINACOES_BDR):
                bdrs_com_nome.append({'Ticker': ticker, 'Nome': nome.split(' ')[0].replace(',', '')})
        print(f"-> Sucesso. {len(bdrs_com_nome)} BDRs (com nome) encontrados.")
        return bdrs_com_nome
    except Exception as e: print(f"-> ERRO CRÍTICO BDRs: {e}"); return []

def buscar_dados_abertura_yf(tickers: list) -> pd.DataFrame:
    print(f"--> Buscando dados Abertura/Fech. (2d) para {len(tickers)} BDRs (yfinance)...")
    if not tickers: return pd.DataFrame()
    tickers_sa = [f"{ticker}.SA" for ticker in tickers]
    try:
        dados = yf.download(tickers_sa, period="2d", interval='1d', auto_adjust=True, progress=False, ignore_tz=True)
        if not isinstance(dados, pd.DataFrame) or dados.empty or len(dados) < 2:
            print(f"-> ERRO yfinance: Dados insuficientes (< 2 dias) ou formato inválido.")
            return pd.DataFrame()

        ontem_close = dados.iloc[-2]['Close'].rename('FechAnterior'); hoje_open = dados.iloc[-1]['Open'].rename('Abertura')

        if isinstance(ontem_close.index, pd.MultiIndex):
            ontem_close.index = ontem_close.index.str.replace('.SA', ''); hoje_open.index = hoje_open.index.str.replace('.SA', '')
        elif 'SA' in ontem_close.index[0]:
            ontem_close.index = pd.Index([i.replace('.SA', '') for i in ontem_close.index])
            hoje_open.index = pd.Index([i.replace('.SA', '') for i in hoje_open.index])

        df_dados_gaps = pd.concat([ontem_close, hoje_open], axis=1); df_dados_gaps.index.name = 'Ticker'
        df_dados_gaps = df_dados_gaps.reset_index()
        print(f"--> Dados yfinance obtidos para {len(df_dados_gaps.dropna())} BDRs.")
        return df_dados_gaps.dropna()
    except Exception as e: print(f"-> ERRO GERAL yfinance (Fase 1): {e}"); return pd.DataFrame()

def buscar_dados_atuais_yf_simplificado(tickers: list) -> dict:
    print(f"--> Buscando dados ATUAIS (yfinance) para {len(tickers)} BDRs (tracking)...")
    dados_atuais = {}
    if not tickers: return {}
    tickers_sa = [f"{ticker}.SA" for ticker in tickers]
    try:
        dados = yf.download(tickers_sa, period="1d", interval='1d', auto_adjust=True, progress=False, ignore_tz=True)
        if not isinstance(dados, pd.DataFrame) or dados.empty: return {} 

        if len(tickers) == 1 and 'Open' in dados.columns:
            hoje = dados.iloc[-1]
            try:
                preco_atual = hoje['Close']
                if pd.notna(preco_atual): dados_atuais[tickers[0]] = preco_atual
            except KeyError: pass
        elif isinstance(dados.columns, pd.MultiIndex):
            hoje = dados.iloc[-1]
            for ticker in tickers:
                ticker_sa = f"{ticker}.SA"
                try:
                    preco_atual = hoje[('Close', ticker_sa)]
                    if pd.notna(preco_atual): dados_atuais[ticker] = preco_atual
                except KeyError: continue
    except Exception as e: print(f"Erro inesperado ao buscar atual (yf): {e}")
    print(f"--> Dados atuais (yfinance) obtidos para {len(dados_atuais)} BDRs.")
    return dados_atuais

def carregar_lista_local(filename: str) -> list | None:
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f: data = json.load(f)
            print(f"Lista de Gaps carregada de '{filename}'.")
            return data
        except Exception as e: print(f"Erro ao carregar lista de '{filename}': {e}"); return None
    else: print(f"Arquivo '{filename}' não encontrado."); return None

def salvar_lista_local(data: list, filename: str):
    try:
        with open(filename, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2)
        print(f"Lista de Gaps salva em '{filename}'.")
    except Exception as e: print(f"Erro ao salvar lista em '{filename}': {e}")

def enviar_whatsapp(msg: str):
    print("\nEnviando notificação para o WhatsApp...")
    if not WHATSAPP_PHONE or not WHATSAPP_APIKEY: print("-> ERRO: Config WhatsApp."); return
    try:
        texto_codificado = requests.utils.quote(msg); url = f"https://api.callmebot.com/whatsapp.php?phone={WHATSAPP_PHONE}&text={texto_codificado}&apikey={WHATSAPP_APIKEY}"
        r = requests.get(url, timeout=30);
        if r.status_code == 200 and ("Message queued" in r.text or "message sent" in r.text.lower()):
            print(f"-> ✅ Notificação enviada (ou enfileirada): {r.text}")
        else:
            print(f"-> ⚠️ Falha envio WhatsApp: {r.status_code} - {r.text}")
    except Exception as e: print(f"-> ⚠️ ERRO envio WhatsApp: {e}")

# --- FUNÇÃO PRINCIPAL DO ROBÔ ---
def rodar_monitor_gap_tracker():
    fuso_brasil = pytz.timezone('America/Sao_Paulo'); hora_utc = datetime.now(pytz.utc)
    hora_brasil_agora = hora_utc.astimezone(fuso_brasil); agora_str = hora_brasil_agora.strftime("%d/%m/%Y %H:%M")
    hoje_str_arquivo = hora_brasil_agora.strftime("%Y-%m-%d")
    local_filename = f"{LOCAL_FILE_PREFIX}{hoje_str_arquivo}.json"
    print(f"\n{'='*70}\n### BDR GAP TRACKER (GITHUB ACTIONS v1.12) ###\nExecução: {agora_str} (Brasília)\n{'='*70}")

    lista_salva_hoje = carregar_lista_local(local_filename)

    if lista_salva_hoje is None:
        # --- FASE 1: Identificar Gaps (TOP 20) ---
        print("\nFASE 1: Identificando Top 20 Gaps de Baixa (yfinance)...")
        bdrs_com_nome = obter_lista_bdrs_da_brapi()
        if not bdrs_com_nome: return
        df_nomes = pd.DataFrame(bdrs_com_nome).set_index('Ticker')
        lista_tickers_para_yf = list(df_nomes.index)
        dados_precos_yf = buscar_dados_abertura_yf(lista_tickers_para_yf)

        if not isinstance(dados_precos_yf, pd.DataFrame) or dados_precos_yf.empty:
            print("Nenhum dado de abertura válido (yfinance). Salvando lista vazia.");
            salvar_lista_local([], local_filename)
            return

        df_gaps = dados_precos_yf.join(df_nomes, on='Ticker').dropna()
        df_gaps['GapPercent'] = df_gaps.apply(lambda row: ((row['Abertura']/row['FechAnterior']) - 1) * 100 if row['FechAnterior'] != 0 else 0, axis=1)
        df_gaps = df_gaps.sort_values(by='GapPercent', ascending=True)
        top_20_gap_down = df_gaps[df_gaps['GapPercent'] < 0].head(TOP_N_GAPS_FASE1)

        if top_20_gap_down.empty:
            print("Nenhum Gap de Baixa significativo encontrado.")
            msg_final = f"ℹ️ *BDR Gap Tracker* ({agora_str} Brasília) ℹ️\n\nNenhum Gap de Baixa significativo encontrado hoje."
            salvar_lista_local([], local_filename)
            enviar_whatsapp(msg_final)
        else:
            lista_para_salvar = top_20_gap_down.reset_index(drop=True).to_dict('records')
            salvar_lista_local(lista_para_salvar, local_filename)
            print(f"Top {len(lista_para_salvar)} Gaps de Baixa encontrados:")

            msg_cabecalho = f"📉 *TOP {len(lista_para_salvar)} GAPS DE BAIXA NA ABERTURA* 📉\n_(Análise: {agora_str} Brasília)_\n"
            enviar_whatsapp(msg_cabecalho)
            time.sleep(5)

            msg_chunk = ""
            total_chunks = (len(lista_para_salvar) + BDRS_POR_MENSAGEM_FASE1 - 1) // BDRS_POR_MENSAGEM_FASE1
            for i, item in enumerate(lista_para_salvar):
                if i % BDRS_POR_MENSAGEM_FASE1 == 0:
                    msg_chunk = f"*(Lote {i//BDRS_POR_MENSAGEM_FASE1 + 1}/{total_chunks})*\n"
                msg_chunk += f"\n-> *{item['Ticker']}* ({item['Nome']}): *{item['GapPercent']:.2f}%*\n   (Abert: R${item['Abertura']:.2f} vs Fech: R${item['FechAnterior']:.2f})"
                if (i + 1) % BDRS_POR_MENSAGEM_FASE1 == 0 or (i + 1) == len(lista_para_salvar):
                    print(f"\n--- ENVIANDO CHUNK FASE 1 ({i//BDRS_POR_MENSAGEM_FASE1 + 1}) ---")
                    print(msg_chunk)
                    enviar_whatsapp(msg_chunk)
                    msg_chunk = ""
                    if (i + 1) < len(lista_para_salvar): time.sleep(5)

    else:
        # --- FASE 2: Acompanhar Top 10 em Recuperação ---
        print(f"\nFASE 2: Acompanhando os {len(lista_salva_hoje)} BDRs (yfinance)...")
        if not lista_salva_hoje: print("Lista de Gaps vazia."); return

        tickers_para_buscar = [d['Ticker'] for d in lista_salva_hoje]
        dados_atuais_yf = buscar_dados_atuais_yf_simplificado(tickers_para_buscar)

        if not dados_atuais_yf: print("Não foi possível obter dados atuais (yfinance)."); return

        resultados_tracking = []
        for item_salvo in lista_salva_hoje:
            ticker = item_salvo['Ticker']
            preco_atual = dados_atuais_yf.get(ticker)
            abertura_salva = item_salvo.get('Abertura')
            if preco_atual is not None and abertura_salva is not None and abertura_salva > 0:
                 variacao_vs_abertura = ((preco_atual / abertura_salva) - 1) * 100
                 resultados_tracking.append({
                     'Ticker': ticker, 'Nome': item_salvo.get('Nome', ticker),
                     'GapPercent': item_salvo.get('GapPercent', 0.0),
                     'VariacaoVsAbertura': variacao_vs_abertura
                 })
            else: resultados_tracking.append({'Ticker': ticker, 'Nome': item_salvo.get('Nome', ticker), 'VariacaoVsAbertura': None})

        positivos = [res for res in resultados_tracking if res.get('VariacaoVsAbertura') is not None and res['VariacaoVsAbertura'] > 0]

        if not positivos:
            print(f"Nenhum dos {len(lista_salva_hoje)} BDRs está em recuperação (>0%) no momento.")
            msg_final = f"⏱️ *ACOMPANHAMENTO GAPS* ⏱️\n_(Análise: {agora_str} Brasília)_\n\nNenhum dos {len(lista_salva_hoje)} BDRs com Gap de Baixa está em recuperação (var. > 0%) no momento."
        else:
            positivos.sort(key=lambda x: x['VariacaoVsAbertura'], reverse=True)
            top_10_positivos = positivos[:TOP_N_TRACKING_FASE2]

            print(f"Resultados do acompanhamento (Top {len(top_10_positivos)} em recuperação > 0%):")
            msg_final = f"⏱️ *ACOMPANHAMENTO GAPS (TOP {len(top_10_positivos)} EM RECUPERAÇÃO)* ⏱️\n_(Análise: {agora_str} Brasília)_\n\n"
            msg_final += f"Top {TOP_N_TRACKING_FASE2} em Recuperação (dos {len(lista_salva_hoje)} Gaps de Hoje):\n"

            for res in top_10_positivos:
                linha_bdr = ""
                if res.get('VariacaoVsAbertura') is not None:
                    emoji = "🔼"
                    linha_bdr = (f"-> {res['Ticker']} ({res['Nome']}): "
                                 f"Gap: {res['GapPercent']:.1f}% | "
                                 f"Var. Dia: {res['VariacaoVsAbertura']:+.1f}% {emoji}")
                    linha_bdr = f"*{linha_bdr}*"
                else:
                    linha_bdr = f"_{res['Ticker']} ({res['Nome']}): Dados Indisp._"
                msg_final += "\n" + linha_bdr
        enviar_whatsapp(msg_final)

    print("\nExecução do Gap Tracker finalizada.")
    print("="*70)

if __name__ == "__main__":
    rodar_monitor_gap_tracker()
