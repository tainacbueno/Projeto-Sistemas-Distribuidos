### Eleição
- Implementado mecanismo de eleição de coordenador entre os servidores, utilizando o rank fornecido pelo serviço de referência.
- O servidor eleito passa a ser responsável pela sincronização de relógio, que é realizada diretamente entre servidores a cada 15 mensagens processadas, seguindo o algoritmo de Berkeley.
- Também foi adicionado um tópico Pub/Sub (`servers`) para anunciar o coordenador aos demais servidores.
