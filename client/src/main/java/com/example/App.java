package com.example;

import org.zeromq.ZMQ;
import org.msgpack.core.MessageBufferPacker;
import org.msgpack.core.MessagePack;
import org.msgpack.core.MessageUnpacker;

import java.util.HashMap;
import java.util.Map;
import java.util.List;
import java.util.ArrayList;

public class App {

    public static void main(String[] args) throws Exception {

        String clientId = System.getenv().getOrDefault("CLIENT_ID", "client");

        ZMQ.Context context = ZMQ.context(1);
        ZMQ.Socket socket = context.socket(ZMQ.REQ);
        socket.connect("tcp://broker:5555");

        System.out.println(clientId + " iniciado");

        send(socket, map("type", "login", "user", clientId), clientId);
        recv(socket, clientId);

        send(socket, map("type", "list_channels"), clientId);
        recv(socket, clientId);

        send(socket, map("type", "create_channel", "channel", "geral"), clientId);
        recv(socket, clientId);

        send(socket, map("type", "list_channels"), clientId);
        recv(socket, clientId);
    }

    static void send(ZMQ.Socket socket, Map<String, Object> map, String clientId) throws Exception {
        map.put("timestamp", System.currentTimeMillis());

        MessageBufferPacker packer = MessagePack.newDefaultBufferPacker();
        packer.packMapHeader(map.size());

        for (Map.Entry<String, Object> e : map.entrySet()) {
            packer.packString(e.getKey());

            if (e.getValue() instanceof String) {
                packer.packString((String) e.getValue());
            } else {
                packer.packLong((Long) e.getValue());
            }
        }

        packer.close();

        byte[] bytes = packer.toByteArray();

        System.out.println("[CLIENT " + clientId + "] ENVIANDO: " + map);
        socket.send(bytes);
    }

    static void recv(ZMQ.Socket socket, String clientId) throws Exception {
        byte[] reply = socket.recv();

        MessageUnpacker unpacker = MessagePack.newDefaultUnpacker(reply);
        int size = unpacker.unpackMapHeader();

        Map<String, Object> map = new HashMap<>();

        for (int i = 0; i < size; i++) {
            String key = unpacker.unpackString();

            switch (unpacker.getNextFormat().getValueType()) {
                case STRING:
                    map.put(key, unpacker.unpackString());
                    break;

                case INTEGER:
                    map.put(key, unpacker.unpackLong());
                    break;

                case ARRAY:
                    int n = unpacker.unpackArrayHeader();
                    List<String> list = new ArrayList<>();
                    for (int j = 0; j < n; j++) {
                        list.add(unpacker.unpackString());
                    }
                    map.put(key, list);
                    break;

                default:
                    unpacker.skipValue();
                    break;
            }
        }

        System.out.println("[CLIENT " + clientId + "] RECEBIDO: " + map);
    }

    static Map<String, Object> map(Object... kv) {
        Map<String, Object> m = new HashMap<>();
        for (int i = 0; i < kv.length; i += 2) {
            m.put((String) kv[i], kv[i + 1]);
        }
        return m;
    }
}