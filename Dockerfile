# Use uma versão específica do Python para garantir compatibilidade
FROM python:3.10-slim

# Define o diretório de trabalho no contêiner
WORKDIR /app

# Copia apenas o arquivo requirements.txt inicialmente para aproveitar o cache do Docker
COPY requirements.txt .

# Instala as dependências especificadas no requirements.txt
RUN pip install --prefer-binary --no-cache-dir -r requirements.txt

# Copia os arquivos restantes do diretório atual para o diretório de trabalho (/app) no contêiner
COPY . .

# Define a variável de ambiente FLASK_APP
ENV FLASK_APP=flaskApi.py

# Expõe a porta 5000, que é a porta padrão do Flask
EXPOSE 5000

# Comando para executar a aplicação Flask quando o contêiner for iniciado
CMD ["flask", "run", "--host=0.0.0.0"]
