import zmq
import msgpack
import time
import os

SERVER_ID = os.getenv("SERVER_ID", "server")

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.connect("tcp://broker:5556")

print(f"[SERVER {SERVER_ID}] iniciado")

while True:
    message = socket.recv()
    data = msgpack.unpackb(message, raw=False)

    print(f"[SERVER {SERVER_ID}] RECEBIDO: {data}")

    response = {
        "timestamp": time.time(),
        "status": "ok"
    }

    if data["type"] == "login":
        response["msg"] = "login_ok"

    elif data["type"] == "create_channel":
        response["msg"] = "channel_created"

    print(f"[SERVER {SERVER_ID}] ENVIANDO: {response}")

    socket.send(msgpack.packb(response))