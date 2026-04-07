import zmq
import msgpack
import time
import os

from storage import now_brt, save_message

SERVER_ID = os.getenv("SERVER_ID", "server")

context = zmq.Context()

socket = context.socket(zmq.DEALER)
socket.connect("tcp://broker:5556")

pub = context.socket(zmq.PUB)
pub.connect("tcp://pubsub-proxy:5557")

print(f"[SERVER {SERVER_ID}] iniciado")

while True:
    client_id, empty, raw_message = socket.recv_multipart()
    data = msgpack.unpackb(raw_message, raw=False)

    print(f"[SERVER {SERVER_ID}] RECEBIDO: {data}")

    response = {
        "timestamp": time.time(),
        "status": "ok"
    }

    if data["type"] == "login":
        response["msg"] = "login_ok"

    elif data["type"] == "create_channel":
        response["msg"] = "channel_created"

    elif data["type"] == "publish":
        channel = data["channel"]
        message = data["message"]
        timestamp = data["timestamp"]

        payload = {
            "channel": channel,
            "message": message,
            "timestamp": timestamp
        }
            
        packed = msgpack.packb(payload)

        pub.send(channel.encode() + b" " + packed)

        sent_at = now_brt()

        save_message({
            "type": "publish",
            "channel": channel,
            "message": message,
            "timestamp": sent_at
        })

        response["msg"] = "published"

    print(f"[SERVER {SERVER_ID}] ENVIANDO: {response}")

    socket.send_multipart([
        client_id,
        b'',
        msgpack.packb(response)
    ])