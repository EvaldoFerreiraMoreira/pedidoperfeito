import logging
from flask import Flask, request, jsonify
import pandas as pd
import requests
import os
from flask_cors import CORS

# Configuração do logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Desativa a verificação SSL
requests.packages.urllib3.disable_warnings()

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

def fetch_data(cnpj, email, empresaId):
    print(f"Recebendo dados para CNPJ: {cnpj}, Email: {email}")
    #
    config_url = f"http://192.168.0.105:8080/V1/api/empresa/findconfiguracaobyempresaid/{empresaId}"
    find_urls = f"http://192.168.0.105:8080/V1/api/api/findbyempresa/{empresaId}"

    config_data = None
    iurls = None

    try:
        config_response = requests.get(config_url)
        config_response.raise_for_status()
        config_data = config_response.json()
        print(f"URL_LOC_CLI: {config_data.get('url_loc_cli', '')}")
        print(f"CONFIG DATA: {config_data}")

        base_url = config_data.get('url_loc_cli', '').format(cnpj=cnpj, email=email)

        response = requests.get(base_url)
        response.raise_for_status()
        data_json = response.json()
        print(f"Resposta inicial da API: {data_json}")

        clientes = data_json.get('dados', [])
        if not clientes:
            print("CLIENTE AQUI: ", clientes)
            raise ValueError("Nenhum cliente encontrado")

        cliente = clientes[0]
        cliente_id = cliente.get('id')
        nome_cliente = cliente.get('nome')

        # Obtendo URLs do segundo endpoint
        config_response2 = requests.get(find_urls)
        config_response2.raise_for_status()
        config_data2 = config_response2.json()
        iurls = [item.get('url') for item in config_data2] # Iterando sobre o dicionário de urls
        print(f"URLS: {iurls}")
        urls = [item.get('url', '').format(cliente_id=cliente_id) for item in config_data2]  # Passando o cliente_id dinamicamente

        dfs = []
        data_jsons = []  # Lista para armazenar os dados json
        for url in urls:
            response = requests.get(url)
            response.raise_for_status()
            data_json2 = response.json()
            print(f"Resposta inicial da API 2: {data_json2}")
            df = json_to_dataframe(data_json2)
            dfs.append(df)
            data_jsons.append(data_json2)  # Armazenar os dados json

        if len(dfs) > 1:
            combined_df = pd.concat(dfs, axis=1, join='inner')
        else:
            combined_df = dfs[0] if dfs else pd.DataFrame()

        return combined_df, cliente_id, nome_cliente, empresaId, data_json, data_jsons, config_data, iurls

    except requests.RequestException as e:
        print(f"Erro na requisição: {e}")
        return pd.DataFrame(), None, None, None, None, None, config_data, iurls
    except ValueError as ve:
        print(f"Valor inválido encontrado: {ve}")
        return pd.DataFrame(), None, None, None, None, None, config_data, iurls
    except AttributeError as ae:
        print(f"Erro de atributo: {ae}")
        return pd.DataFrame(), None, None, None, None, None, config_data, iurls

@app.route('/chat_with_data', methods=['POST'])
def api_chat_with_data():
    # Registro das informações da requisição
    logger.info(f"Recebida uma requisição {request.method} para {request.path} com dados {request.json}")

    content = request.json
    cnpj = content.get('cnpj')
    email = content.get('email')
    prompt = content.get('prompt')
    empresaId = content.get('empresaId')
    
    print(f"Dados recebidos - CNPJ: {cnpj}, Email: {email}, Prompt: {prompt}, empresaId: {empresaId}")  # Debug print
    
    df, cliente_id, nome_cliente, empresaId, data_json, data_json2, config_data, iurls = fetch_data(cnpj, email, empresaId)
    
    if cliente_id is None:
        return jsonify({"error": "clienteId não encontrado", "resposta da api 1": data_json, "resposta da api 2": data_json2, "URL_LOC_CLI": config_data, "URLS": iurls}), 404

    if empresaId is None:
        if config_data is not None:
            url_loc_cli = config_data.get('url_loc_cli', '')
        else:
            url_loc_cli = None
        
        return jsonify({"error": "empresaId não encontrado", "resposta da api 1": data_json, "resposta da api 2": data_json2, "URL_LOC_CLI": url_loc_cli, "URLS": iurls}), 404
    
    print(f"ClienteId DE BAIXO: {cliente_id}")
    print(f"Nome Cliente DE BAIXO: {nome_cliente}")
    print(f"EmpresaId: {empresaId}")
    
    if prompt.lower() == "cadastro":
        return jsonify({"response": "Olá, como posso ajudar?", "cliente_id": cliente_id, "nome_cliente": nome_cliente})
    
    if df.empty:
        print("DataFrame vazio após tentativa de busca.")  # Debug print
        return jsonify({"error": "Nenhum dado encontrado para o cliente especificado"}), 404
    
    result = chat_with_data(df, prompt)
    
    # Código para enviar a resposta ao endpoint
    post_url = "http://192.168.0.105:8080/V1/api/conversa/create"
    post_body = {
        "pergunta": prompt,
        "resposta": result,
        "cnpj_cliente": cnpj,
        "nome_cliente": nome_cliente,
        "empresa": {"id": empresaId}
    }
    try:
        post_response = requests.post(post_url, json=post_body)
        post_response.raise_for_status()  # Verificar se a requisição foi bem-sucedida
        print("POST realizado com sucesso.")  # Debug print
    except requests.RequestException as e:
        print(f"Erro ao fazer POST para o endpoint: {e}")  # Debug print
    
    return jsonify({"response": result, "cliente_id": cliente_id, "resposta da api 1": data_json, "resposta da api 2": data_json2, "URL_LOC_CLI": config_data['url_loc_cli'], "URLS": iurls})

@app.route('/')
def home():
    return "Servidor Rodando"

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
