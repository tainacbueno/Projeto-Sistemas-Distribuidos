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

coordinator = None
sync = context.socket(zmq.REP)
sync.bind("tcp://*:6000")

sub = context.socket(zmq.SUB)
sub.connect("tcp://pubsub-proxy:5558")
sub.subscribe(b"servers")

poller = zmq.Poller()
poller.register(socket, zmq.POLLIN)  # mensagens dos clientes
poller.register(sync, zmq.POLLIN)    # mensagens de outros servidores
poller.register(sub, zmq.POLLIN)     # avisos no tópico servers

rank_reply = utils.sync_with_reference(ref, SERVER_ID, "register")
SERVER_RANK = rank_reply["rank"]

print(f"[SERVER {SERVER_ID}] rank recebido: {SERVER_RANK}", flush=True)

received_messages = 0

##################################################################
##      Funções auxiliares

def sync_clock_with_coordinator():
    global coordinator

    if not coordinator:
        elect_coordinator()
        return False

    try:
        req = context.socket(zmq.REQ)
        req.setsockopt(zmq.RCVTIMEO, 3000)
        req.setsockopt(zmq.LINGER, 0)
        req.connect(f"tcp://{coordinator}:6000")

        req.send(msgpack.packb({
            "type": "clock",
            "server": SERVER_ID,
            "logical_clock": utils.increment_clock()
        }))

        reply = msgpack.unpackb(req.recv(), raw=False)
        utils.update_clock(reply.get("logical_clock"))

        if "current_time" in reply:
            utils.set_physical_time(reply["current_time"])
            print(f"[SERVER {SERVER_ID}] relógio sincronizado com {coordinator}: {reply}", flush=True)
            return True

    except Exception as e:
        print(f"[SERVER {SERVER_ID}] falha ao sincronizar com {coordinator}: {e}", flush=True)

    return False

def elect_coordinator():
    global coordinator

    reply = utils.sync_with_reference(ref, SERVER_ID, "list")
    servers = reply.get("servers", [])

    alive = [
        {"name": SERVER_ID, "rank": SERVER_RANK}
    ]

    for server in servers:
        name = server["name"]

        if name == SERVER_ID:
            continue

        try:
            req = context.socket(zmq.REQ)
            req.setsockopt(zmq.RCVTIMEO, 3000)
            req.setsockopt(zmq.LINGER, 0)
            req.connect(f"tcp://{name}:6000")

            req.send(msgpack.packb({
                "type": "election",
                "server": SERVER_ID,
                "logical_clock": utils.increment_clock()
            }))

            election_reply = msgpack.unpackb(req.recv(), raw=False)
            utils.update_clock(election_reply.get("logical_clock"))

            if election_reply.get("status") == "ok":
                alive.append(server)

        except Exception:
            pass

    elected = sorted(alive, key=lambda x: x["rank"])[0]
    coordinator = elected["name"]

    print(f"[SERVER {SERVER_ID}] coordenador eleito: {coordinator}", flush=True)

    if coordinator == SERVER_ID:
        announce_coordinator()

def announce_coordinator():
    msg = {
        "type": "coordinator",
        "server": SERVER_ID,
        "logical_clock": utils.increment_clock()
    }

    pub.send(b"servers " + msgpack.packb(msg))

    save_message({
        "type": "coordinator_announcement",
        "server_id": SERVER_ID,
        "coordinator": SERVER_ID,
        "logical_clock": utils.increment_clock()
    })
    
    print(f"[SERVER {SERVER_ID}] anunciou coordenador: {SERVER_ID}", flush=True)


##################################################################
##      Loop principal

while True:
    socks = dict(poller.poll())

    if socket in socks:
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

            payload = {
                "channel": channel,
                "message": message,
                "timestamp": data["timestamp"],
                "logical_clock": utils.increment_clock(),
                "server_id": SERVER_ID
            }

            pub.send(channel.encode() + b" " + msgpack.packb(payload))

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

        print(f"[SERVER {SERVER_ID}] ENVIANDO: {response}", flush=True)

        socket.send_multipart([
            client_id,
            b'',
            msgpack.packb(response)
        ])

    if sync in socks:
        raw = sync.recv()
        data = msgpack.unpackb(raw, raw=False)

        utils.update_clock(data.get("logical_clock"))

        if data["type"] == "clock":
            reply = {
                "status": "ok",
                "current_time": utils.physical_time(),
                "server": SERVER_ID,
                "logical_clock": utils.increment_clock()
            }

        elif data["type"] == "election":
            reply = {
                "status": "ok",
                "server": SERVER_ID,
                "rank": SERVER_RANK,
                "logical_clock": utils.increment_clock()
            }

        else:
            reply = {
                "status": "error",
                "message": "tipo inválido",
                "logical_clock": utils.increment_clock()
            }

        sync.send(msgpack.packb(reply))
    
    if sub in socks:
        raw = sub.recv()

        index = raw.find(b" ")
        if index != -1:
            topic = raw[:index].decode()
            payload = raw[index + 1:]

            data = msgpack.unpackb(payload, raw=False)
            utils.update_clock(data.get("logical_clock"))

            if topic == "servers" and data.get("type") == "coordinator":
                coordinator = data["server"]
                print(f"[SERVER {SERVER_ID}] novo coordenador recebido: {coordinator}", flush=True)

    if received_messages % 15 == 0:
        utils.sync_with_reference(ref, SERVER_ID, "heartbeat")

        if coordinator is None:
            elect_coordinator()
        elif coordinator == SERVER_ID:
            print(f"[SERVER {SERVER_ID}] sou coordenador, relógio: {utils.physical_time()}", flush=True)
        else:
            ok = sync_clock_with_coordinator()
            if not ok:
                print(f"[SERVER {SERVER_ID}] coordenador indisponível, iniciando eleição", flush=True)
                elect_coordinator()     