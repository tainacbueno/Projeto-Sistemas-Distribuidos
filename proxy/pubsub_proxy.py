import zmq

context = zmq.Context()

# Recebe publishers (servidores)
xsub = context.socket(zmq.XSUB)
xsub.bind("tcp://*:5557")

# Envia para subscribers (clientes)
xpub = context.socket(zmq.XPUB)
xpub.bind("tcp://*:5558")

print("PubSub proxy rodando...")

zmq.proxy(xsub, xpub)