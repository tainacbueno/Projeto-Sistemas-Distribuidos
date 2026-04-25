logical_clock = 0
physical_clock_offset = 0


def increment_clock():
    global logical_clock
    logical_clock += 1
    return logical_clock


def update_clock(received_clock):
    global logical_clock
    if received_clock is not None:
        logical_clock = max(logical_clock, received_clock)


def physical_time():
    import time
    return time.time() + physical_clock_offset


def sync_with_reference(ref_socket, server_id, msg_type):
    import msgpack, time

    global physical_clock_offset

    request = {
        "type": msg_type,
        "server": server_id,
        "logical_clock": increment_clock()
    }

    ref_socket.send(msgpack.packb(request))
    reply = msgpack.unpackb(ref_socket.recv(), raw=False)

    if "current_time" in reply:
        physical_clock_offset = reply["current_time"] - time.time()

    return reply