logical_clock = 0
physical_clock_offset = 0


def increment_clock():
    global logical_clock
    logical_clock += 1
    return logical_clock


def update_clock(received_clock):
    global logical_clock
    if received_clock is not None:
        logical_clock = max(logical_clock, int(received_clock))


def physical_time():
    import time
    return time.time() + physical_clock_offset


def set_physical_time(correct_time):
    import time

    global physical_clock_offset
    physical_clock_offset = correct_time - time.time()


def sync_with_reference(ref_socket, server_id, msg_type):
    import msgpack

    request = {
        "type": msg_type,
        "server": server_id,
        "logical_clock": increment_clock()
    }

    ref_socket.send(msgpack.packb(request))
    reply = msgpack.unpackb(ref_socket.recv(), raw=False)

    update_clock(reply.get("logical_clock"))

    return reply