# Imagem base: Python 3.12 slim
FROM python:3.12-slim

# Define o diretório de trabalho no container
WORKDIR /app

# Copia o requirements.txt e instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código do projeto para o container
COPY . .

# Define a variável de ambiente (opcional, para logs)
ENV PYTHONUNBUFFERED=1

# Comando para executar o script diretamente (sem Gunicorn/Flask)
CMD ["python", "main.py"]
