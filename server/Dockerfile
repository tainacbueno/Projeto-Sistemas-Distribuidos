FROM python:3.11-slim

WORKDIR /app

RUN pip install pyzmq msgpack pytz

COPY . .

CMD ["python", "server.py"]