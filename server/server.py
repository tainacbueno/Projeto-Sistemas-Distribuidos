import zmq
import msgpack
import time
import os

from storage import now_brt, save_message
import utils as utils

SERVER_ID = os.getenv("SERVER_ID", "server")

context = zmq.Context()

socket = context.socket(zmq.DEALER)
socket.connect("tcp://broker:5556")

pub = context.socket(zmq.PUB)
pub.connect("tcp://pubsub-proxy:5557")

ref = context.socket(zmq.REQ)
ref.connect("tcp://reference:5560")

rank_reply = utils.sync_with_reference(ref, SERVER_ID, "register")
SERVER_RANK = rank_reply["rank"]

print(f"[SERVER {SERVER_ID}] rank recebido: {SERVER_RANK}", flush=True)

received_messages = 0

while True:
    client_id, empty, raw_message = socket.recv_multipart()
    data = msgpack.unpackb(raw_message, raw=False)
    utils.update_clock(data.get("logical_clock"))
    received_messages += 1

    print(f"[SERVER {SERVER_ID}] RECEBIDO: {data}", flush=True)

    response = {
        "timestamp": time.time(),
        "logical_clock": utils.increment_clock(),
        "server_id": SERVER_ID,
        "server_rank": SERVER_RANK,
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
            "timestamp": timestamp,
            "logical_clock": utils.increment_clock(),
            "server_id": SERVER_ID
        }
            
        packed = msgpack.packb(payload)

        pub.send(channel.encode() + b" " + packed)

        sent_at = now_brt()

        save_message({
            "type": "publish",
            "channel": channel,
            "message": message,
            "timestamp": sent_at,
            "logical_clock": payload["logical_clock"],
            "server_id": SERVER_ID,
            "server_rank": SERVER_RANK
        })

        response["msg"] = "published"

    if received_messages % 10 == 0:
        heartbeat_reply = utils.sync_with_reference(ref, SERVER_ID, "heartbeat")
        print(f"[SERVER {SERVER_ID}] HEARTBEAT: {heartbeat_reply}", flush=True)

    print(f"[SERVER {SERVER_ID}] ENVIANDO: {response}", flush=True)

    socket.send_multipart([
        client_id,
        b'',
        msgpack.packb(response)
    ])