## Projeto de Sistemas Distribuídos

### Introdução

Este projeto implementa um sistema distribuído de comunicação baseado no padrão cliente-servidor utilizando ZeroMQ para troca de mensagens.

O objetivo é simular a interação entre múltiplos clientes (bots) e múltiplos servidores, permitindo operações básicas como login, listagem de canais e criação de canais.

Toda a execução ocorre de forma automatizada através de containers Docker orquestrados com Docker Compose, sem necessidade de interação manual.

---

### Arquitetura

A arquitetura do sistema foi organizada de forma modular, separando responsabilidades e seguindo os padrões recomendados:

- **Clientes (Java)**: Bots responsáveis por solicitar informações ao servidor, criar canais, se inscrever em canais e publicar mensagens.
- **Broker (Python)**: Atua como intermediário entre clientes e servidores, utilizando o padrão ROUTER/DEALER. É responsável por rotear mensagens REQ/REP e manter o estado global dos canais existentes.
- **Servidores (Python)**: Responsáveis por processar requisições dos clientes, publicar mensagens nos canais e persistir as publicações em disco.
- **Proxy Pub/Sub (Python)**: Serviço independente que implementa o padrão Publisher-Subscriber, desacoplando completamente publicadores e assinantes.

A comunicação segue o fluxo:<br>
<img width="403" height="148" alt="image" src="https://github.com/user-attachments/assets/cd1c62d0-18d9-4fab-b34b-aa7411909b04" />

---

### Comunicação

- **Comunicação Cliente–Servidor (REQ/REP)**

Para comunicação síncrona, foi utilizado o ZeroMQ com o padrão REQ (cliente), ROUTER (broker) e DEALER (servidor), por ser simples de usar, leve e funcionar bem para sistemas distribuídos. Ele permite que diferentes serviços troquem mensagens sem precisar de um servidor HTTP ou algo mais complexo.<br>
Esse modelo permite múltiplos clientes, múltiplos servidores, balanceamento de carga e escalabilidade sem acoplamento direto.
Todas as mensagens trocadas nesse fluxo são serializadas com MessagePack e incluem timestamp de envio.

- **Publicação em Canais (Publisher–Subscriber)**
  
A distribuição de mensagens em canais foi implementada com o padrão Pub/Sub. Para isso, foi criado um proxy Pub/Sub separado do broker.<br>
O proxy utiliza a porta 5557 (XSUB) para receber publicações dos servidores e a porta 5558 (XPUB) para distribuir mensagens aos clientes.<br>
O nome do canal é utilizado como tópico da mensagem, permitindo que clientes se inscrevam em múltiplos canais por meio de uma única conexão SUB. As inscrições são realizadas exclusivamente no cliente, garantindo desacoplamento e flexibilidade.

---

### Relógios e Heartbeat
Foram adicionados mecanismos de controle de tempo e disponibilidade dos servidores.

- **Relógio lógico (Lamport)**

Clientes e servidores passaram a utilizar um contador (`logical_clock`) que é incrementado antes de cada envio e atualizado ao receber mensagens, garantindo a ordenação lógica dos eventos.

- **Serviço de referência**

Foi criado um novo serviço responsável por atribuir um rank aos servidores e manter a lista de servidores ativos e fornecer o horário atual para sincronização*.

*o mecanismo de eleição passa a ser o responsável pelo horário atual

- **Heartbeat**

Os servidores enviam periodicamente um heartbeat (a cada 10 mensagens processadas) para o serviço de referência, informando que continuam ativos. Servidores que não enviam heartbeat são removidos da lista.

---
### Eleição e Sincronização de Relógio

Foi implementado um mecanismo de eleição de coordenador entre os servidores, substituindo o serviço de referência como fonte de tempo.

- **Eleição de coordenador**

Os servidores utilizam o rank fornecido pelo serviço de referência para eleger um coordenador.  
Quando um servidor não consegue se comunicar com o coordenador atual, ele inicia um processo de eleição, enviando requisições para os demais servidores ativos.  
O servidor com melhor rank (menor valor) entre os disponíveis é escolhido como coordenador.

- **Anúncio do coordenador**

Após a eleição, o servidor eleito publica seu identificador no tópico `servers` utilizando o padrão Pub/Sub.  
Todos os servidores inscritos nesse tópico atualizam localmente quem é o coordenador atual.

- **Sincronização de relógio (Berkeley)**

A sincronização de relógio passa a ser feita diretamente entre servidores.  
A cada 15 mensagens processadas, os servidores solicitam o horário ao coordenador, que responde com o tempo atual.  
Os servidores então ajustam seus relógios locais com base na resposta recebida.

Esse mecanismo elimina a dependência do serviço de referência para sincronização de tempo, tornando o sistema mais distribuído e resiliente a falhas.

---

### Persistência

O armazenamento é feito no servidor, centralizando a persistência. O formato escolhido é JSON por linha, facilitando a leitura manual, o processamento posterior e a recuperação de dados. Cada execução do servidor gera um novo arquivo de log, evitando sobrescrita de dados.

Exemplo de estrutura:<br>
<img width="324" height="65" alt="image" src="https://github.com/user-attachments/assets/230eb445-b252-4c8e-b6ba-a78058ba520d" />


Exemplo de entrada no arquivo de log:<br>
```
{"type": "publish", "channel": "canal_client1_0",  "message": "client1 diz: Isso é um projeto de SD",  "timestamp": "2026-04-07 14:23:33 BRT", "logical_clock": 35, "server_id": "server2", "server_rank": 1, "stored_at": "2026-04-24 23:11:55 BRT"}
{"type": "coordinator_announcement", "server_id": "server1", "coordinator": "server1", "logical_clock": 83, "stored_at": "2026-05-01 14:46:53 BRT"}
```
Os timestamps são armazenados no horário de Brasília (BRT) para facilitar a leitura e análise.

---

### Containers

- **Docker**
- **Docker Compose**

Utilizados para isolar serviços, facilitar execução e simular ambiente distribuído. A persistência em disco é feita com o uso de volumes Docker, permitindo que os arquivos de log gerados pelos servidores sejam facilmente acessados no host, sem necessidade de entrar no container.

---

### Funcionamento

Ao executar:

```bash
docker compose up --build
```

O sistema inicia automaticamente os serviços (2 servidores, 1 broker e 1 proxy Pub/Sub) e o comportamento dos bots (2 clientes), sem necessidade de interação manual, em **loop infito**. <br>
