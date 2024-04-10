from flask import Flask, request, jsonify
import pandas as pd
import requests
import os
from flask_cors import CORS

# Obtém a chave de API da OpenAI a partir das variáveis de ambiente.
openai_api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
CORS(app)

def json_to_dataframe(data, prefix=''):
    print(f"Convertendo JSON para DataFrame: {data}")  # Debug print
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
    df = pd.DataFrame([flat_data])
    print(f"DataFrame resultante: {df}")  # Debug print
    return df

def chat_with_data(df, prompt):
    print(f"Iniciando chat com dados - DataFrame: {df}, Prompt: {prompt}")  # Debug print
    from pandasai.llm.openai import OpenAI
    from pandasai import PandasAI
    prompt_in_portuguese = "Responda em português: " + prompt
    llm = OpenAI(api_token=openai_api_key)
    pandas_ai = PandasAI(llm)
    result = pandas_ai.run(df, prompt=prompt_in_portuguese)
    print(f"Resultado do chat: {result}")  # Debug print
    return result

def fetch_data(cnpj, email):
    print(f"Recebendo dados para CNPJ: {cnpj}, Email: {email}")  # Debug print
    empresa = "5"  # Assumindo que o código da empresa é sempre 5, ajuste conforme necessário
    base_url = f"https://fjinfor.ddns.net/fvendas/api/api_busca_cli.php?funcao=get_buscacli&empresa={empresa}&cnpj={cnpj}&email={email}"
    
    try:
        response = requests.get(base_url)
        response.raise_for_status()
        data_json = response.json()
        print(f"Resposta inicial da API: {data_json}")  # Debug print
        cliente_id = data_json['dados'][0]['id'] if data_json['dados'] else None
        
        print(f"Cliente ID: {cliente_id}")  # Debug print

        urls = [
            f"https://fjinfor.ddns.net/fvendas/api/api_sitpedido.php?funcao=get_sitpedido&cliente={cliente_id}",
            f"https://fjinfor.ddns.net/fvendas/api/api_sit_boleto.php?funcao=get_sitboleto_1&cliente={cliente_id}"
        ]

        dfs = []
        for url in urls:
            response = requests.get(url)
            response.raise_for_status()
            data_json = response.json()
            df = json_to_dataframe(data_json)
            dfs.append(df)

        combined_df = pd.concat(dfs, axis=1)
        return combined_df, cliente_id
    except requests.RequestException as e:
        print(f"Erro na requisição: {e}")  # Debug print
        return pd.DataFrame(), None

@app.route('/chat_with_data', methods=['POST'])
def api_chat_with_data():
    content = request.json
    cnpj = content.get('cnpj')
    email = content.get('email')
    prompt = content.get('prompt')
    
    print(f"Dados recebidos - CNPJ: {cnpj}, Email: {email}, Prompt: {prompt}")  # Debug print
    
    # Primeiro, busque os dados e o ID do cliente
    df, cliente_id = fetch_data(cnpj, email)
    
    if prompt.lower() == "cadastro":
        return jsonify({"response": "Olá, como posso ajudar?", "cliente_id": cliente_id})
    
    if df.empty:
        print("DataFrame vazio após tentativa de busca.")  # Debug print
        return jsonify({"error": "Nenhum dado encontrado para o cliente especificado"}), 404
    
    result = chat_with_data(df, prompt)
    return jsonify({"response": result, "cliente_id": cliente_id})

@app.route('/')
def home():
    return "Servidor Rodando"

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)