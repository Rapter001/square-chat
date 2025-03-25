FROM python:3.13.2-slim

RUN apt update && apt upgrade -y

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python3", "main.py"]