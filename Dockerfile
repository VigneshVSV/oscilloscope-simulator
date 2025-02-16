FROM python:3.11-alpine
WORKDIR /usr/local/app
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python3", "server.py"]