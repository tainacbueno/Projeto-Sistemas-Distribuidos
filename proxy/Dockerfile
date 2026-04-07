FROM python:3.10

WORKDIR /app
COPY pubsub_proxy.py .

RUN pip install pyzmq

CMD ["python", "pubsub_proxy.py"]