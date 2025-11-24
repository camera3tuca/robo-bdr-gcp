import streamlit as st
import pandas as pd
import json
import os
import glob
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="BDR Gap Tracker",
    page_icon="📈",
    layout="wide"
)

# --- TÍTULO E CABEÇALHO ---
st.title("📈 BDR Gap Tracker - Monitor em Tempo Real")
st.markdown("""
Este painel monitora as **Top 20 BDRs** com maiores Gaps de Baixa na abertura e acompanha a sua recuperação durante o dia.
*Dados atualizados automaticamente pelo Robô.*
""")

# --- FUNÇÃO PARA CARREGAR O ARQUIVO MAIS RECENTE ---
def carregar_dados_recentes():
    # Procura todos os arquivos que começam com "top_gaps_data_"
    arquivos = glob.glob('top_gaps_data_*.json')
    
    if not arquivos:
        return None, None
    
    # Pega o arquivo mais recente (baseado na data de criação/modificação)
    arquivo_mais_recente = max(arquivos, key=os.path.getctime)
    
    try:
        with open(arquivo_mais_recente, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        return dados, arquivo_mais_recente
    except Exception as e:
        st.error(f"Erro ao ler arquivo: {e}")
        return None, None

# --- CARREGAR DADOS ---
dados_json, nome_arquivo = carregar_dados_recentes()

if dados_json is None:
    st.warning("⚠️ Nenhum dado encontrado ainda. O Robô precisa rodar pelo menos uma vez.")
    st.info("Aguarde a próxima execução agendada ou execute manualmente no GitHub Actions.")

elif len(dados_json) == 0:
    st.info("✅ O Robô rodou, mas não encontrou nenhum Gap de Baixa significativo hoje.")

else:
    # --- PROCESSAR DADOS PARA EXIBIÇÃO ---
    # Transforma o JSON em Tabela (DataFrame)
    df = pd.DataFrame(dados_json)
    
    # Extrai a data do nome do arquivo (ex: top_gaps_data_2025-11-24.json)
    data_arquivo = nome_arquivo.replace('top_gaps_data_', '').replace('.json', '').replace('./', '')
    
    st.write("---")
    
    # --- MÉTRICAS PRINCIPAIS ---
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Data dos Dados", data_arquivo)
    with col2:
        st.metric("Total de Gaps Monitorados", f"{len(df)}")
    with col3:
        # Pega a melhor recuperação (se houver dados disso)
        if 'VariacaoVsAbertura' in df.columns:
            # Filtra apenas quem tem valor válido
            df_recuperacao = df[df['VariacaoVsAbertura'].notna()]
            if not df_recuperacao.empty:
                melhor = df_recuperacao.sort_values(by='VariacaoVsAbertura', ascending=False).iloc[0]
                st.metric("Melhor Recuperação do Dia", f"{melhor['Ticker']}", f"{melhor['VariacaoVsAbertura']:.2f}%")
            else:
                st.metric("Melhor Recuperação", "-")
        else:
            st.metric("Melhor Recuperação", "Aguardando Fase 2")

    st.write("---")

    # --- ABA 1: TABELA DETALHADA ---
    st.subheader("📋 Tabela Detalhada dos Gaps")
    
    # Renomear colunas para ficar bonito
    df_display = df.copy()
    
    # Se ainda não tivermos dados de variação (Fase 1), criamos a coluna vazia
    if 'VariacaoVsAbertura' not in df_display.columns:
        df_display['VariacaoVsAbertura'] = None

    # Formatar as colunas numéricas
    df_display = df_display[['Ticker', 'Nome', 'GapPercent', 'Abertura', 'FechAnterior', 'VariacaoVsAbertura']]
    
    # Configurar cores para a tabela (destaque nos Gaps negativos)
    st.dataframe(
        df_display.style.format({
            'GapPercent': '{:.2f}%',
            'Abertura': 'R$ {:.2f}',
            'FechAnterior': 'R$ {:.2f}',
            'VariacaoVsAbertura': '{:.2f}%'
        }).background_gradient(subset=['GapPercent'], cmap='Reds_r'),
        use_container_width=True,
        height=500
    )

    st.caption("Nota: 'VariacaoVsAbertura' só aparece após a execução da Fase 2 (Monitoramento).")

# --- RODAPÉ ---
st.write("---")
st.markdown("Desenvolvido com Python + Streamlit + GitHub Actions 🚀")
if st.button("🔄 Atualizar Dados"):
    st.rerun()
