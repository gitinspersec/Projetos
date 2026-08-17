# Desafios e Extensões

Estas são coisas concretas que você pode construir sobre a base de código existente. Cada uma tem um ponto de partida claro no código e um motivo pelo qual vale a pena ser feita.

## Iniciante

### 1. Adicionar Detalhamento de Tipos ICMP

Atualmente, os pacotes ICMP contam como uma única entrada de protocolo. O ICMP carrega muitos tipos de mensagens: echo request/reply (ping), port unreachable, time exceeded (saltos de traceroute), etc.

**O que fazer:** Em `IPv4::handle_icmp()` (`src/packet/IP.cpp:73`), faça o cast do payload para `icmphdr` e leia `type` e `code`. Estenda o `ApplicationProtocol` em `packet.hpp` para incluir `ICMP_ECHO`, `ICMP_UNREACHABLE`, etc., ou adicione um campo `icmp_type` separado ao `Packet`.

**Por que isso importa:** O ICMP é frequentemente usado para reconhecimento (ping sweeps) e para canais ocultos (ferramentas de tunelamento ICMP como `icmptunnel` codificam dados no payload). Ser capaz de distinguir requisições de eco de mensagens de inacessibilidade informa se você está sendo escaneado ou se as rotas estão quebradas.

### 2. Codificar Protocolos por Cores na TUI

Adicione cores às tabelas de protocolos de transporte e aplicação — TCP em azul, UDP em verde, ICMP em amarelo, desconhecido em vermelho.

**O que fazer:** Em `view.cpp:render_transport()`, acesse células individuais com `table.SelectCell(row, col).Decorate(color(Color::Blue))`. O `Table::SelectCell()` do FTXUI recebe índices de linha e coluna.

**Por que isso importa:** Operadores de segurança analisam dashboards sob pressão de tempo. A codificação por cores permite que o olho salte para anomalias (tráfego UDP inesperado, protocolos desconhecidos) sem ler cada linha.

### 3. Adicionar um Contador de Taxa de Pacotes

Exiba pacotes/seg ao lado do gráfico de largura de banda. O gráfico de largura de banda mostra bytes/seg, mas a taxa de pacotes é útil separadamente — um flood de pacotes minúsculos com baixa largura de banda é um padrão diferente de algumas transferências grandes.

**O que fazer:** Adicione `uint32_t last_p = 0` ao `Stats` (ao lado de `last_b`). Em `update_bandwidth()` (`protocolStats.cpp:230`), compute `delta_packets / elapsed` junto com o cálculo de bytes existente. Adicione ao `StatsSnapshot` e exiba em `render_header()` ou `render_stats()`.

---

## Intermediário

### 4. Remontagem de Fluxo TCP

Atualmente, cada pacote TCP é analisado de forma independente. Protocolos de nível de aplicação que abrangem múltiplos pacotes (respostas HTTP, transferências FTP) não são reconstruídos. A remontagem combina segmentos TCP na ordem do número de sequência em um fluxo (stream).

**O que fazer:** Adicione uma classe `StreamTable` que mapeia `(src_ip, dst_ip, src_port, dst_port)` para um buffer ordenado de segmentos (indexado pelo número de sequência). Em `got_packet()` (`pcapCapture.cpp:152`), após construir um `Packet` TCP, insira-o na tabela de fluxos. Quando os segmentos chegarem em ordem, anexe ao buffer do fluxo. Quando uma lacuna for preenchida, execute a identificação da camada de aplicação no buffer completo.

**Por que isso importa:** A detecção de HTTP por correspondência de verbos (`memcmp(payload_ptr, "GET ", 4)` em `packet.cpp:9`) só funciona se a requisição HTTP couber no primeiro pacote. Para corpos grandes de PUT/POST ou conexões lentas, o verbo pode estar em um segmento anterior que já foi processado. A remontagem é como Snort, Suricata e engines de DPI comerciais lidam com isso.

### 5. Log de Consultas DNS

Extraia nomes de consultas DNS de pacotes UDP na porta 53 e registre-os com timestamps.

**O que fazer:** Em `Packet::get_application_protocol()` (`packet.cpp:14`), quando o DNS for identificado, analise a seção de pergunta (question section) do `payload_ptr`. O DNS é binário: os bytes 0–11 são o cabeçalho (ID, flags, contagens), os bytes 12+ são a seção de pergunta como uma sequência de labels prefixados pelo comprimento (ex: `\x03www\x07example\x03com\x00`). Percorra os labels para extrair o FQDN. Adicione um campo string `dns_query` ao `Packet` e exiba-o na tabela de pacotes.

**Por que isso importa:** O DNS é a lista telefônica que os atacantes sempre usam. Beacons de C2 fazem check-in via DNS. A exfiltração de dados codifica informações em consultas DNS (tunelamento DNS). Um log de consultas simples captura malwares como o `dnscat2`, que usa registros DNS TXT para um shell de comando — as consultas mostram nomes de subdomínios absurdamente longos.

### 6. Engine de Regras de Alerta

Adicione uma engine de avaliação de regras que dispara alertas quando o tráfego corresponde a condições configuráveis: "alertar se qualquer IP único enviar > 1000 pacotes em 10 segundos" (port scan), "alertar se consultas DNS/seg > 100" (tunelamento), "alertar se um novo IP aparecer que não estava na linha de base" (movimentação lateral).

**O que fazer:** Crie uma struct `AlertRule` com uma função de condição e um limite (threshold). Crie uma `AlertEngine` que a thread de atualização da UI chama após `update_ip_stats()`. As regras inspecionam o snapshot de `Stats` em busca de violações de limite. Armazene os alertas disparados em um `deque<Alert>` e adicione um painel ao `view.cpp` para exibi-los.

**Por que isso importa:** Este é o núcleo do que um SIEM faz. SIEMs (Splunk, Elastic SIEM, IBM QRadar) correlacionam eventos de múltiplas fontes, mas a ideia subjacente — avaliar condições de regras contra métricas observadas, disparar alerta quando excedidas — é o que você está construindo aqui.

---

## Avançado

### 7. Hex Dump do Payload do Pacote

Adicione uma visão detalhada que mostre os bytes hexadecimais brutos e a representação ASCII do payload de um pacote selecionado — como o painel inferior do Wireshark.

**O que fazer:** O `payload_ptr` é atualmente anulado após a execução de `get_application_protocol()` (`packet.hpp:53`). Para suportar o hex dump, copie os bytes do payload para um `vector<uint8_t>` antes de anular. Adicione um índice de pacote selecionado ao estado da `View`, uma forma de navegá-lo (teclas de seta via `CatchEvent`) e um método `render_hex_dump()` que formata os bytes como linhas `XX XX XX ... | .texto..`.

O FTXUI não possui um widget de hex dump integrado. Você teria que construí-lo com uma série de elementos `hbox({text(hex_col) | fixed(50), text(ascii_col)})`.

**Por que isso importa:** A inspeção de payload é como você verifica se um alerta é real. "Tráfego DNS" é fácil de detectar. Saber se esse tráfego DNS contém consultas normais ou exfiltração codificada em base64 requer olhar para os bytes.

### 8. Linha de Base de Anomalias e Detecção de Desvios

Registre uma linha de base (baseline) de tráfego durante uma janela configurável (ex: primeiros 60 segundos) e, em seguida, sinalize desvios. Um novo protocolo aparecendo, um IP normalmente silencioso tornando-se um dos principais emissores, ou tráfego TCP em uma porta apenas UDP, todos justificam investigação.

**O que fazer:** Adicione uma classe `Baseline` que tira um snapshot do `transport_map` e `ip_map` após a janela de linha de base. Adicione uma função `compare(current_snapshot, baseline)` que computa Z-scores ou deltas percentuais para cada métrica. Armazene os desvios em um `vector<Deviation>` e renderize-os em um novo painel da TUI.

**Por que isso importa:** O ataque SolarWinds de 2020 persistiu sem detecção por 9 meses, em parte porque o tráfego malicioso imitava a telemetria normal do produto Orion — parecia tráfego esperado para qualquer pessoa que verificasse manualmente. A comparação automatizada de linha de base teria sinalizado o novo padrão de beacon contra a linha de base anterior ao comprometimento.

### 9. Exportação PCAP Durante a Captura ao Vivo

Permita que o usuário escreva um arquivo `.pcap` do tráfego capturado em tempo real, não apenas exporte estatísticas ao final. Isso permite a análise offline no Wireshark posteriormente.

**O que fazer:** Use `pcap_dump_open()` para criar um handle de arquivo de dump, e `pcap_dump()` dentro de `got_packet()` (`pcapCapture.cpp:152`) para escrever cada pacote bruto com seu `pcap_pkthdr`. Adicione uma flag `--write` ao `argsParser` (`argsParse.cpp`). O handle de dump é outro recurso C que se beneficia do encapsulamento RAII.

**Por que isso importa:** Ferramentas de captura ao vivo em resposta a incidentes sempre escrevem arquivos pcap. Você quer capturar primeiro e analisar depois — especialmente se o ataque ainda estiver em andamento. Ferramentas como `tcpdump -w` e `dumpcap` fazem exatamente isso.

### 10. Detecção de Port Scanning Consciente de Protocolo

Detecte fluxos apenas de SYN (onde conexões TCP são iniciadas, mas nunca concluídas) e sinalize-os como potenciais port scans.

**O que fazer:** Na tabela de fluxos TCP (do desafio 4), rastreie as flags TCP em cada pacote. Um SYN sem resposta SYN-ACK dentro de um timeout é um scan half-open. Conte o número de portas de destino distintas de um único IP de origem dentro de uma janela de tempo — mais de N portas únicas em M segundos = provável scan. Este é o algoritmo que o `portsentry`, `snort` e firewalls modernos usam.

A botnet Mirai de 2016 escaneou toda a internet IPv4 em busca de portas Telnet/SSH abertas em menos de uma hora, executando scans SYN a partir de mais de 100.000 dispositivos infectados simultaneamente. Detectar padrões de scan no nível do pacote — não apenas contar tentativas de conexão — é como os sistemas de IDS de rede capturam isso.
