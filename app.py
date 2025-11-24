import streamlit as st
import pandas as pd
import json
import os
import glob
import yfinance as yf # Vamos usar isso para os gráficos
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="BDR Gap Tracker", page_icon="📈", layout="wide")

# --- TÍTULO ---
st.title("📈 BDR Gap Tracker - Monitor em Tempo Real")
st.markdown("Este painel monitora as **Top 20 BDRs** com maiores Gaps de Baixa.")

# --- FUNÇÃO PARA CARREGAR DADOS ---
def carregar_dados_recentes():
    arquivos = glob.glob('top_gaps_data_*.json')
    if not arquivos: return None, None
    arquivo_mais_recente = max(arquivos, key=os.path.getctime)
    try:
        with open(arquivo_mais_recente, 'r', encoding='utf-8') as f:
            return json.load(f), arquivo_mais_recente
    except Exception: return None, None

# --- CARREGAR JSON ---
dados_json, nome_arquivo = carregar_dados_recentes()

if not dados_json:
    st.warning("Aguardando dados do Robô...")
else:
    # --- PREPARAR TABELA ---
    df = pd.DataFrame(dados_json)
    data_arquivo = nome_arquivo.replace('top_gaps_data_', '').replace('.json', '').replace('./', '')

    # Converter colunas para números
    cols_numericas = ['GapPercent', 'Abertura', 'FechAnterior']
    for col in cols_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    if 'VariacaoVsAbertura' in df.columns:
        df['VariacaoVsAbertura'] = pd.to_numeric(df['VariacaoVsAbertura'], errors='coerce')
    else:
        df['VariacaoVsAbertura'] = 0.0

    # --- MÉTRICAS ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Data", data_arquivo)
    col2.metric("Gaps Monitorados", f"{len(df)}")
    
    melhor = df.sort_values(by='VariacaoVsAbertura', ascending=False).iloc[0] if not df.empty else None
    if melhor is not None and melhor['VariacaoVsAbertura'] != 0:
        emoji = "🔥" if melhor['VariacaoVsAbertura'] > 1 else "📈"
        col3.metric("Melhor Recuperação", f"{melhor['Ticker']}", f"{melhor['VariacaoVsAbertura']:.2f}%")
    else:
        col3.metric("Melhor Recuperação", "Aguardando Fase 2")

    st.divider()

    # --- LAYOUT DIVIDIDO: TABELA NA ESQUERDA, GRÁFICOS NA DIREITA ---
    col_esq, col_dir = st.columns([1, 1.5]) # A coluna da direita é um pouco maior

    with col_esq:
        st.subheader("📋 Lista de Gaps")
        # Tabela Interativa: O usuário pode clicar para ordenar
        st.dataframe(
            df[['Ticker', 'Nome', 'GapPercent', 'VariacaoVsAbertura']],
            column_config={
                "GapPercent": st.column_config.NumberColumn("Gap", format="%.2f %%"),
                "VariacaoVsAbertura": st.column_config.NumberColumn("Recup.", format="%.2f %%"),
            },
            use_container_width=True,
            height=600,
            hide_index=True
        )

    with col_dir:
        st.subheader("📊 Análise Gráfica")
        
        # Menu para escolher qual BDR analisar
        lista_tickers = df['Ticker'].tolist()
        ticker_selecionado = st.selectbox("Selecione um Ativo para ver os gráficos:", lista_tickers)
        
        if ticker_selecionado:
            ticker_sa = f"{ticker_selecionado}.SA"
            
            # --- GRÁFICO 1: INTRADAY (HOJE) ---
            st.write(f"**Movimento Hoje (Intraday 15m) - {ticker_selecionado}**")
            try:
                # Baixa dados de hoje, intervalo de 15 minutos
                df_intra = yf.download(ticker_sa, period="1d", interval="15m", progress=False)
                if not df_intra.empty:
                    # O Streamlit gosta de gráfico de linha simples com o 'Close'
                    st.line_chart(df_intra['Close'], color="#FF4B4B", height=250)
                else:
                    st.info("Dados intraday ainda não disponíveis (o mercado abriu?).")
            except Exception as e:
                st.error("Erro ao carregar gráfico intraday.")

            st.divider()

            # --- GRÁFICO 2: DIÁRIO (6 MESES) ---
            st.write(f"**Tendência (6 Meses) - {ticker_selecionado}**")
            try:
                # Baixa dados históricos
                df_diario = yf.download(ticker_sa, period="6mo", interval="1d", progress=False)
                if not df_diario.empty:
                    st.area_chart(df_diario['Close'], color="#0068C9", height=250)
                else:
                    st.info("Dados históricos indisponíveis.")
            except Exception:
                st.error("Erro ao carregar gráfico diário.")

    st.caption("Dados atualizados automaticamente via GitHub Actions e Yahoo Finance.")

if st.button("🔄 Atualizar"): st.rerun()
