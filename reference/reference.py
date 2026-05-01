import zmq
import msgpack
import time

HEARTBEAT_TIMEOUT = 30

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5560")

servers = {}
next_rank = 1

print("[REFERENCE] iniciado", flush=True)

def cleanup():
    now = time.time()
    inactive = [
        name for name, data in servers.items()
        if now - data["last_seen"] > HEARTBEAT_TIMEOUT
    ]

    for name in inactive:
        print(f"[REFERENCE] removendo servidor inativo: {name}")
        del servers[name]

while True:
    raw = socket.recv()
    data = msgpack.unpackb(raw, raw=False)

    cleanup()

    msg_type = data.get("type")
    server_name = data.get("server")

    if msg_type == "register":
        if server_name not in servers:
            servers[server_name] = {
                "rank": next_rank,
                "last_seen": time.time()
            }
            next_rank += 1
        else:
            servers[server_name]["last_seen"] = time.time()

        reply = {
            "status": "ok",
            "rank": servers[server_name]["rank"]
        }

    elif msg_type == "list":
        reply = {
            "status": "ok",
            "servers": [
                {"name": name, "rank": info["rank"]}
                for name, info in servers.items()
            ]
        }

    elif msg_type == "heartbeat":
        if server_name in servers: 
            servers[server_name]["last_seen"] = time.time()
            reply = {
                "status": "ok" 
            }

    else:
        reply = {
            "status": "error",
            "message": "tipo inválido"
        }

    print(f"[REFERENCE] RECEBIDO: {data}", flush=True)
    print(f"[REFERENCE] ENVIANDO: {reply}", flush=True)

    socket.send(msgpack.packb(reply))