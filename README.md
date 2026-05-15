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

### Consistência e Replicação

Foi implementada a replicação das mensagens entre os servidores para evitar que cada servidor mantenha apenas uma parte do histórico.

Como o broker distribui as requisições entre os servidores por balanceamento de carga, uma mensagem publicada pode ser processada pelo `server1` ou pelo `server2`. Sem replicação, se um servidor parasse de funcionar, parte das mensagens armazenadas poderia ficar indisponível.

Para resolver esse problema, foi utilizada uma combinação de **réplica ativa**, **atualização por push**, **atualização por pull** e **consistência eventual**.

- **Réplica ativa**

Na réplica ativa, a operação de atualização é propagada entre as réplicas.  
No projeto, quando um servidor recebe uma mensagem do tipo `publish`, ele salva a publicação localmente e envia um evento de replicação para os demais servidores.

- **Atualização por push**

A atualização por push ocorre quando o servidor que recebeu a mensagem inicia a propagação para os outros servidores.  
Essa propagação é feita pelo tópico interno `servers`, utilizando o Pub/Sub já existente no projeto.

Com isso, quando um servidor recebe uma publicação, os demais servidores ativos recebem uma cópia da mesma mensagem e também armazenam em disco.

- **Atualização por pull**

Além do push, foi implementada uma sincronização inicial por pull.  
Quando um servidor inicia ou volta depois de uma parada, ele consulta o serviço de referência para descobrir outros servidores ativos e solicita o histórico armazenado por uma réplica disponível.

Esse mecanismo permite que um servidor que ficou fora do ar recupere as mensagens que perdeu enquanto estava indisponível.

- **Consistência eventual**

O modelo adotado é de consistência eventual.  
Pode existir um pequeno intervalo em que uma mensagem recém-publicada está presente apenas no servidor que a recebeu originalmente. Porém, após a propagação por push, os demais servidores também armazenam essa mensagem.

Da mesma forma, se um servidor voltar após uma falha, ele pode iniciar desatualizado, mas após o pull inicial volta a possuir o histórico replicado.

---

### Persistência

O armazenamento é feito no servidor, centralizando a persistência. O formato escolhido é JSON por linha, facilitando a leitura manual, o processamento posterior e a recuperação de dados.

Ambos os servidores possuem uma pasta separada para seus arquivos de log, permitindo verificar individualmente o histórico armazenado por cada um:<br>
```text
data/
├── server1/
│   └── messages_2026-05-15_18-05-21.log
└── server2/
    └── messages_2026-05-15_18-05-21.log
```

Cada mensagem publicada possui um `event_id`, utilizado para evitar duplicidade na gravação. Assim, se uma mesma mensagem for recebida novamente por replicação ou sincronização, ela não é salva mais de uma vez pelo mesmo servidor.

Exemplo de entrada no arquivo de log:<br>

```
{
  "type": "publish",
  "event_id": "86915cbf-0ebc-4f68-8062-770515e63d53",
  "channel": "canal_client2_0",
  "message": "client2 diz: Isso é um projeto de SD",
  "origin_server": "server2",
  "stored_by": "server1",
  "replicated": true
}
```
*Os timestamps são armazenados no horário de Brasília (BRT) para facilitar a leitura e análise.

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
