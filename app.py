import streamlit as st
import requests
import pandas as pd

# Configuração da página do Streamlit
st.set_page_config(layout='wide')
st.title("Siad.AI Chat")

# Endereço do servidor Flask (ajuste conforme necessário)
FLASK_SERVER_URL = "http://localhost:5000/chat_with_data"

def fetch_data(cnpj, email):
    data = {'cnpj': cnpj, 'email': email, 'prompt': 'Digite sua consulta'}
    response = requests.post(FLASK_SERVER_URL, json=data)
    if response.status_code == 200:
        return pd.DataFrame(response.json()['response'])
    else:
        st.error("Não foi possível carregar dados da API.")
        return pd.DataFrame()

# Lógica para capturar entradas do usuário e fazer solicitações à API Flask
if 'dados_enviados' not in st.session_state:
    st.session_state.dados_enviados = False

if not st.session_state.dados_enviados:
    cnpj = st.text_input("Favor informar seu CNPJ:", key="cnpj_input")
    email = st.text_input("Favor informar seu email:", key="email_input")

    if st.button("Enviar Dados"):
        st.session_state.dados_enviados
