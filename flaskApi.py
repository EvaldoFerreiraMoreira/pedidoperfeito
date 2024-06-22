from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from flask_cors import CORS

# Carregar variáveis de ambiente
load_dotenv()

# Obtém a chave de API da OpenAI a partir das variáveis de ambiente.
openai_api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
CORS(app)

# Função para buscar dados de múltiplas APIs
def fetch_data(cnpj, email, empresaId):
    # Aqui vai a lógica para buscar dados conforme seu código original
    config_url = f"https://fjinfor.ddns.net/api/V1/api/empresa/findconfiguracaobyempresaid/{empresaId}"
    find_urls = f"https://fjinfor.ddns.net/api/V1/api/api/findbyempresa/{empresaId}"

    try:
        # Obter a primeira configuração
        config_response = requests.get(config_url)
        config_response.raise_for_status()
        config_data = config_response.json()
        base_url = config_data.get('url_loc_cli')
        if not base_url:
            raise ValueError("URL base não encontrada na resposta da API")

        base_url = base_url.format(cnpj=cnpj, email=email)
        response = requests.get(base_url)
        response.raise_for_status()
        data_json = response.json()
        print(f"Resposta inicial da API: {data_json}")

        clientes = data_json.get('dados', [])
        if not clientes:
            raise ValueError("Nenhum cliente encontrado na resposta da API")

        cliente = clientes[0]
        cliente_id = cliente.get('id')
        nome_cliente = cliente.get('nome')

        # Obter as URLs do segundo endpoint
        config_response2 = requests.get(find_urls)
        config_response2.raise_for_status()
        config_data2 = config_response2.json()
        urls = [item['url'].format(cliente_id=cliente_id) for item in config_data2 if 'url' in item]

        data_json_list = []

        for url in urls:
            try:
                response = requests.get(url)
                response.raise_for_status()
                data_json = response.json()
                print(f"Resposta da API: {data_json}")

                # Armazenando os dados em data_json_list
                data_json_list.append(data_json)

            except requests.RequestException as e:
                print(f"Erro ao fazer requisição GET para a URL: {url}, Erro: {e}")

        return data_json_list, cliente_id, nome_cliente, empresaId

    except requests.RequestException as e:
        print(f"Erro na requisição: {e}")
        return [], None, None, None
    except ValueError as ve:
        print(f"Valor inválido encontrado: {ve}")
        return [], None, None, None

@app.route('/chat_with_data', methods=['POST'])
def api_chat_with_data():
    content = request.json
    cnpj = content.get('cnpj')
    email = content.get('email')
    prompt = content.get('prompt')
    empresaId = content.get('empresaId')

    data_json_list, cliente_id, nome_cliente, empresaId = fetch_data(cnpj, email, empresaId)

    if cliente_id is None:
        return jsonify({"error": "clienteId não encontrado"}), 404

    if not data_json_list:
        return jsonify({"error": "Nenhum dado encontrado para o cliente especificado"}), 404

    # Construir a conversa a partir do prompt recebido
    template = """
    Você está interagindo com um usuário que está fazendo perguntas sobre os dados combinados da API.
    Baseado nos dados recebidos, na pergunta e na resposta em linguagem natural, forneça uma resposta significativa.
    
    Dados da API: {api_data}
    Histórico da Conversa: {chat_history}
    Pergunta do Usuário: {question}
    
    Lembre-se de que estou aqui para ajudar com informações específicas sobre a empresa e seus dados. 
    Se precisar de ajuda com isso, por favor, pergunte novamente sobre a empresa.
    """

    prompt_template = ChatPromptTemplate.from_template(template)

    llm = ChatOpenAI(model="gpt-4-0125-preview")

    chain = (
        RunnablePassthrough.assign(api_data=lambda _: data_json_list)
        | prompt_template
        | llm
        | StrOutputParser()
    )

    response = chain.invoke({
        "question": prompt,
        "chat_history": [],
    })

    # Dados para enviar no POST
    data_to_post = {
        "pergunta": prompt,
        "resposta": response,
        "cnpj_cliente": cnpj,
        "nome_cliente": nome_cliente,
        "empresa": {"id": empresaId}
    }

    # Enviar POST para a rota especificada
    try:
        post_url = "https://fjinfor.ddns.net/api/V1/api/conversa/create"
        post_response = requests.post(post_url, json=data_to_post)
        post_response.raise_for_status()
        print(f"POST bem-sucedido para {post_url}")
    except requests.RequestException as e:
        print(f"Erro ao fazer POST para {post_url}: {e}")

    return jsonify({"response": response})

@app.route('/')
def home():
    return "Servidor Rodando"

if __name__ == '__main__':
    app.run(debug=True)