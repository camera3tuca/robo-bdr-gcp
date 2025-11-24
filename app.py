import streamlit as st
import pandas as pd
import json
import os
import glob
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

# --- CARREGAR ---
dados_json, nome_arquivo = carregar_dados_recentes()

if not dados_json:
    st.warning("Aguardando dados do Robô...")
else:
    # --- PREPARAR TABELA ---
    df = pd.DataFrame(dados_json)
    data_arquivo = nome_arquivo.replace('top_gaps_data_', '').replace('.json', '').replace('./', '')

    # 1. Garantir que as colunas são numéricas (Isso corrige o TypeError!)
    cols_numericas = ['GapPercent', 'Abertura', 'FechAnterior']
    for col in cols_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    if 'VariacaoVsAbertura' in df.columns:
        df['VariacaoVsAbertura'] = pd.to_numeric(df['VariacaoVsAbertura'], errors='coerce')
    else:
        df['VariacaoVsAbertura'] = 0.0 # Valor padrão se não existir

    # --- MÉTRICAS ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Data", data_arquivo)
    col2.metric("Gaps Monitorados", f"{len(df)}")
    
    melhor = df.sort_values(by='VariacaoVsAbertura', ascending=False).iloc[0] if not df.empty else None
    if melhor is not None and melhor['VariacaoVsAbertura'] != 0:
        col3.metric("Melhor Recuperação", f"{melhor['Ticker']}", f"{melhor['VariacaoVsAbertura']:.2f}%")
    else:
        col3.metric("Melhor Recuperação", "Aguardando Fase 2")

    st.divider()

    # --- TABELA SIMPLIFICADA (Sem erros de estilo) ---
    st.subheader("📋 Tabela Detalhada")

    # Selecionar colunas para exibir
    colunas_finais = ['Ticker', 'Nome', 'GapPercent', 'Abertura', 'FechAnterior']
    if 'VariacaoVsAbertura' in df.columns:
        colunas_finais.append('VariacaoVsAbertura')

    # Exibir usando st.dataframe simples (mais seguro)
    st.dataframe(
        df[colunas_finais],
        column_config={
            "GapPercent": st.column_config.NumberColumn("Gap (%)", format="%.2f %%"),
            "Abertura": st.column_config.NumberColumn("Abertura (R$)", format="R$ %.2f"),
            "FechAnterior": st.column_config.NumberColumn("Fech. Ant. (R$)", format="R$ %.2f"),
            "VariacaoVsAbertura": st.column_config.NumberColumn("Recuperação (%)", format="%.2f %%"),
        },
        use_container_width=True,
        height=600,
        hide_index=True
    )

    st.caption("Dados atualizados automaticamente via GitHub Actions.")

if st.button("🔄 Atualizar"): st.rerun()
