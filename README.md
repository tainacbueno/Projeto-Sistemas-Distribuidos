## Projeto de Sistemas Distribuídos

### Introdução

Este projeto implementa um sistema distribuído de comunicação baseado no padrão cliente-servidor utilizando ZeroMQ para troca de mensagens.

O objetivo é simular a interação entre múltiplos clientes (bots) e múltiplos servidores, permitindo operações básicas como login, listagem de canais e criação de canais.

Toda a execução ocorre de forma automatizada através de containers Docker orquestrados com Docker Compose, sem necessidade de interação manual.

---

### Arquitetura

O sistema é composto por:

- **Clientes (Java)**: bots que realizam login, listam canais e criam canais
- **Servidores (Python)**: processam requisições
- **Broker (Python)**: responsável por rotear mensagens e manter o estado dos canais

A comunicação segue o padrão:
Cliente → Broker → Servidor → Broker → Cliente

---

###  Linguagens utilizadas

- **Python**: utilizado para servidor e broker
- **Java**: utilizado para implementação dos clientes

A escolha foi feita para demonstrar interoperabilidade entre diferentes linguagens em um sistema distribuído.

---

### Comunicação

- **ZeroMQ (REQ/REP + ROUTER/DEALER)**

O ZeroMQ escolhido por ser simples de usar, leve e funcionar bem para sistemas distribuídos. Ele permite que diferentes serviços troquem mensagens sem precisar de um servidor HTTP ou algo mais complexo.

---

### Serialização

- **MessagePack**

Todas as mensagens são serializadas em formato binário utilizando MessagePack. As mensagens têm tamanhos menores e maior desempenho, além de incluírem o tipo da requisição, dados necessários e timestamp de envio.

---

### Containers

- **Docker**
- **Docker Compose**

Utilizados para isolar serviços, facilitar execução e simular ambiente distribuído.

---

### Funcionamento

Ao executar:

```bash
docker compose up --build
```

O sistema inicia automaticamente 2 clientes, 2 servidores e 1 broker. <br>
Cada cliente executa login, listagem de canais, criação de canal e nova listagem.

---

### Persistência

Nesta primeira etapa, não há persistência em disco. Os dados (como canais e logins) são mantidos em memória no broker durante a execução do sistema.<br>
Nas próximas etapas, será implementado armazenamento persistente.
