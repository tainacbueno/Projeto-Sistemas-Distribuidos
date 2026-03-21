import zmq
import msgpack

context = zmq.Context()

frontend = context.socket(zmq.ROUTER)
frontend.bind("tcp://*:5555")

backend = context.socket(zmq.DEALER)
backend.bind("tcp://*:5556")

channels = set()

print("[BROKER] iniciado")

poller = zmq.Poller()
poller.register(frontend, zmq.POLLIN)
poller.register(backend, zmq.POLLIN)

while True:
    socks = dict(poller.poll())

    # CLIENT → BROKER
    if frontend in socks:
        client_id, empty, msg = frontend.recv_multipart()

        data = msgpack.unpackb(msg, raw=False)
        print(f"[BROKER] RECEBIDO DO CLIENTE: {data}")

        if data["type"] == "create_channel":
            channels.add(data["channel"])

        elif data["type"] == "list_channels":
            reply = {
                "status": "ok",
                "channels": list(channels)
            }
            frontend.send_multipart([
                client_id,
                b'',
                msgpack.packb(reply)
            ])
            continue

        backend.send_multipart([client_id, b'', msg])

    # SERVER → BROKER
    if backend in socks:
        msg = backend.recv_multipart()

        # DEALER não mantém identity → só repassa
        frontend.send_multipart(msg)