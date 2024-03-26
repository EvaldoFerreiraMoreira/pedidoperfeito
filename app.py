import streamlit as st
from flask import Flask, request, jsonify
import pandas as pd
import requests
from pandasai.llm.openai import OpenAI
from pandasai import PandasAI
import os

# Obtém a chave de API da OpenAI a partir das variáveis de ambiente.
openai_api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

# Define uma função para interagir com um DataFrame e um prompt de texto usando inteligência artificial.
def chat_with_data(df, prompt):
    prompt_in_portuguese = "Responda em português: " + prompt
    llm = OpenAI(api_token=openai_api_key)
    pandas_ai = PandasAI(llm)
    result = pandas_ai.run(df, prompt=prompt_in_portuguese)
    return result

def json_to_dataframe(data, prefix=''):
    def flatten_json(y, prefix=''):
        out = {}
        def flatten(x, name=''):
            if isinstance(x, dict):
                for a in x:
                    flatten(x[a], name + a + '_')
            elif isinstance(x, list):
                i = 0
                for a in x:
                    flatten(a, name + str(i) + '_')
                    i += 1
            else:
                out[name[:-1]] = x
        flatten(y)
        return out

    flat_data = flatten_json(data)
    return pd.DataFrame([flat_data])

def fetch_data(cnpj, email):
    empresa = "5"  # Assumindo que o código da empresa é sempre 5, ajuste conforme necessário
    base_url = f"https://fjinfor.ddns.net/fvendas/api/api_busca_cli.php?funcao=get_buscacli&empresa={empresa}&cnpj={cnpj}&email={email}"
    
    try:
        response = requests.get(base_url)
        response.raise_for_status()
        data_json = response.json()
        cliente_id = data_json['dados'][0]['id'] if data_json['dados'] else None
        if cliente_id:
            # Constrói a segunda URL com o ID do cliente obtido
            detalhe_url = f"https://fjinfor.ddns.net/fvendas/api/api_sitpedido.php?funcao=get_sitpedido&cliente={cliente_id}"
            response_detalhe = requests.get(detalhe_url)
            response_detalhe.raise_for_status()
            detalhe_data_json = response_detalhe.json()
            df = json_to_dataframe(detalhe_data_json)
            return df
        else:
            st.error("Cliente não encontrado. Verifique o CNPJ e o e-mail fornecidos.")
            return pd.DataFrame()
    except requests.RequestException as e:
        st.error(f"Erro ao buscar dados da API. Erro: {e}")
        return pd.DataFrame()

@app.route('/chat_with_data', methods=['POST'])
def api_chat_with_data():
    content = request.json
    cnpj = content.get('cnpj')
    email = content.get('email')
    prompt = content.get('prompt')
    
    df = fetch_data(cnpj, email)
    if df.empty:
        return jsonify({"error": "Nenhum dado encontrado para o cliente especificado"}), 404
    
    result = chat_with_data(df, prompt)
    return jsonify({"response": result})

# Configuração da página do Streamlit
st.set_page_config(layout='wide')
st.title("Siad.AI Chat")

# Iniciar chat
if 'dados_enviados' not in st.session_state:
    st.session_state.dados_enviados = False

if not st.session_state.dados_enviados:
    cnpj = st.text_input("Favor informar seu CNPJ:", key="cnpj_input")
    email = st.text_input("Favor informar seu email:", key="email_input")

    if st.button("Enviar Dados"):
        st.session_state.dados_enviados = True
        st.session_state.cnpj = cnpj
        st.session_state.email = email

if st.session_state.dados_enviados:
    # Carregando dados das APIs
    data = fetch_data(st.session_state.cnpj, st.session_state.email)

    if not data.empty:
        st.info("Dados carregados das APIs")
        st.dataframe(data, use_container_width=True)

        input_text = st.text_area("Digite sua consulta", key="consulta")
        if input_text:
            if st.button("Buscar Dados", key="buscar"):
                st.info(f"Sua consulta: {input_text}")
                result = chat_with_data(data, input_text)
                st.success(result)
    else:
        st.error("Não foi possível carregar dados das APIs. Verifique as URLs e tente novamente.")
        

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
