### Relógios e Heartbeat

- Adicionado relógio lógico (`logical_clock`) em clientes e servidores
- Criado serviço de referência para rank e sincronização
- Implementado heartbeat a cada 10 mensagens
- Mensagens persistidas agora incluem `logical_clock`, `server_id` e `server_rank`
