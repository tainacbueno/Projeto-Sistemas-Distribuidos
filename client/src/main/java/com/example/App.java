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

        ZMQ.Socket sub = context.socket(ZMQ.SUB);
        sub.connect("tcp://pubsub-proxy:5558");

        List<String> channels = new ArrayList<>();
        List<String> subscribed = new ArrayList<>();

        String[] mensagens = {
            "Olá, tudo bem?",
            "Alguém por aqui?",
            "Mensagem de teste",
            "Bom dia, pessoal!",
            "Isso é um projeto de SD",
            "Testando publicação no canal",
            "Mensagem automática do bot"
        };

        new Thread(() -> {
            while (true) {
                byte[] msg = sub.recv();

                int index = -1;
                for (int i = 0; i < msg.length; i++) {
                    if (msg[i] == ' ') {
                        index = i;
                        break;
                    }
                }

                if (index == -1) continue;

                String channel = new String(msg, 0, index);
                byte[] payload = java.util.Arrays.copyOfRange(msg, index + 1, msg.length);

                try {
                    MessageUnpacker unpacker = MessagePack.newDefaultUnpacker(payload);
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
                            default:
                                unpacker.skipValue();
                                break;
                        }
                    }

                    long receivedAt = System.currentTimeMillis();

                    System.out.println("[PUBSUB] Canal: " + channel +
                            " | Msg: " + map +
                            " | Recebido em: " + receivedAt);

                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        }).start();

        System.out.println(clientId + " iniciado");

        send(socket, map("type", "login", "user", clientId), clientId);
        recv(socket, clientId);

        send(socket, map("type", "list_channels"), clientId);
        Map<String, Object> reply = recvWithReturn(socket, clientId);
        if (reply.containsKey("channels")) {
            channels = (List<String>) reply.get("channels");
        }

        if (channels.size() < 5) {
            String newChannel = "canal_" + clientId + "_" + channels.size();
            send(
                socket,
                map("type", "create_channel", "channel", newChannel),
                clientId
            );
            recv(socket, clientId);
            channels.add(newChannel);
        }

        send(socket, map("type", "list_channels"), clientId);
        reply = recvWithReturn(socket, clientId);
        if (reply.containsKey("channels")) {
            channels = (List<String>) reply.get("channels");
        }

        for (String ch : channels) {
            if (subscribed.size() >= 3) break;

            sub.subscribe(ch.getBytes());
            subscribed.add(ch);

            System.out.println(
                "[CLIENT " + clientId + "] Inscrito no canal: " + ch
            );
        }       

        while (true) {
            for (String ch : channels) {
                for (int i = 0; i < 10; i++) {
                    int idx = (int) (System.currentTimeMillis() % mensagens.length);
                    String msg = clientId + " diz: " + mensagens[idx];

                    send(
                        socket,
                        map(
                            "type", "publish",
                            "channel", ch,
                            "message", msg
                        ),
                        clientId
                    );

                    recv(socket, clientId);
                    Thread.sleep(1000);
                }
            }
        }
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

    static Map<String, Object> recvWithReturn(
            ZMQ.Socket socket,
            String clientId
    ) throws Exception {

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
            }
        }

        System.out.println("[CLIENT " + clientId + "] RECEBIDO: " + map);
        return map;
    }

    static Map<String, Object> map(Object... kv) {
        Map<String, Object> m = new HashMap<>();
        for (int i = 0; i < kv.length; i += 2) {
            m.put((String) kv[i], kv[i + 1]);
        }
        return m;
    }
}