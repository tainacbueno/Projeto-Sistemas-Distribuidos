### Consistência e Replicação

- Implementada a replicação das mensagens entre os servidores, garantindo que todos mantenham uma cópia do histórico, mesmo com o broker distribuindo as requisições por round-robin.

- Utilizada uma estratégia de réplica ativa com atualização por push: quando um servidor recebe uma mensagem do tipo `publish`, ele salva localmente e envia um evento de replicação para os demais servidores pelo tópico Pub/Sub `servers`.

- Adicionada sincronização inicial por pull: quando um servidor inicia ou retorna após uma parada, ele consulta o serviço de referência, encontra outro servidor ativo e solicita o histórico armazenado para recuperar mensagens perdidas.

- Cada mensagem publicada recebe um `event_id`, utilizado para evitar duplicidade caso a mesma mensagem seja recebida mais de uma vez por replicação ou sincronização.

- O modelo adotado é de consistência eventual: após a propagação das atualizações, todos os servidores passam a possuir o mesmo conjunto de mensagens.
