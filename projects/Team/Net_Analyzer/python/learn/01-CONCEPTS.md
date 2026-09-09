# Conceitos de Segurança Fundamentais

Este documento explica os conceitos de segurança que você encontrará ao construir este projeto. Estas não são apenas definições. Vamos nos aprofundar em por que eles importam e como eles realmente funcionam.

## Captura de Pacotes e Raw Sockets

### O Que É

Captura de pacotes significa ler quadros de rede diretamente da interface de rede antes que o sistema operacional os processe. Normalmente, seu SO apenas mostra às aplicações os dados endereçados a elas. A captura de pacotes permite que você veja TODO o tráfego no segmento de rede, incluindo as comunicações de outras máquinas.

Raw sockets fornecem acesso direto aos protocolos de rede abaixo da camada de transporte. Ao contrário dos sockets TCP normais, onde o kernel lida com o estado da conexão, os raw sockets permitem que você crie e inspecione pacotes no nível IP ou inferior.

### Por Que Isso Importa

Durante a violação da DigiNotar em 2011, atacantes emitiram certificados SSL fraudulentos para o Google e outros sites. O monitoramento de rede detectou isso porque os certificados falsos apareceram em handshakes TLS visíveis para ferramentas de captura de pacotes. O certificate pinning não foi suficiente porque os usuários confiavam na CA. A inspeção em nível de pacote revelou a falsificação.

Sem a capacidade de captura de pacotes, você fica cego para:

- Quais protocolos estão realmente rodando em sua rede (não apenas o que deveria estar rodando)
- Credenciais não criptografadas enviadas via HTTP ou FTP
- Exfiltração de dados via DNS tunneling ou ICMP
- Movimentação lateral entre máquinas comprometidas

### Como Funciona

A pilha de rede do sistema operacional se parece com isto:

```
Camada de Aplicação
      ↓
  API de Socket
      ↓
Camada de Transporte (TCP/UDP)
      ↓
  Camada de Rede (IP)
      ↓
   Camada de Link (Ethernet)
      ↓
Interface de Rede Física
```

Aplicações normais interagem no nível da API de Socket. Elas chamam `socket.connect()` e o kernel lida com tudo abaixo. A captura de pacotes opera na Camada de Link, vendo quadros Ethernet brutos antes que o kernel os processe.

No Linux, isso requer a capability CAP_NET_RAW. O kernel verifica essa permissão antes de permitir sockets AF_PACKET. De `capture.py:354-360`:

```python
def _check_linux_permissions() -> tuple[bool, str]:
    if os.geteuid() == 0:
        return True, "Executando como root"

    try:
        sock = socket.socket(
            socket.AF_PACKET,
            socket.SOCK_RAW,
            socket.htons(0x0003),
        )
```

O código tenta criar um raw packet socket. Se tiver sucesso, você possui a CAP_NET_RAW. Se receber um PermissionError, você precisa de privilégios elevados.

### Ataques Comuns

1. **Sniffing em modo promíscuo** - O atacante captura todo o tráfego em um segmento de rede, não apenas o tráfego endereçado a ele. Em redes comutadas (switched), isso requer ARP spoofing para redirecionar o tráfego. Em redes sem fio, o modo monitor captura todos os quadros. Defenda-se com criptografia (TLS/SSL) e segmentação de rede.

2. **Injeção de pacotes** - O atacante cria pacotes maliciosos e os injeta na rede. Ataques de previsão de sequência TCP funcionam desta forma. O spoofing da pilha TCP/IP do Metasploit depende de raw sockets. Defenda-se com filtragem de saída (egress filtering) e rastreamento de conexão no firewall.

3. **Análise de protocolo para reconhecimento** - Atacantes capturam pacotes para mapear a topologia da sua rede, identificar serviços e encontrar versões vulneráveis. O reconhecimento passivo é difícil de detectar porque não gera tráfego. Defenda-se com criptografia e monitoramento de capturas de pacotes incomuns (ferramentas como ArpON detectam interfaces promíscuas).

### Estratégias de Defesa

Este projeto implementa várias proteções:

**Verificação de privilégios** - Antes de iniciar a captura, o código valida as permissões (`capture.py:341-347`). Isso evita mensagens de erro confusas e explica claramente o que é necessário. Ferramentas de produção falham rápido com erros acionáveis.

**Filtragem BPF** - Em vez de processar cada pacote no espaço do usuário, os filtros BPF rodam no kernel e descartam o tráfego irrelevante. De `filters.py:83-92`, o FilterBuilder valida as entradas antes de enviar os filtros para o kernel. Isso evita ataques de injeção de filtro onde uma entrada maliciosa poderia travar a engine de captura.

**Operações de apenas leitura** - Esta ferramenta captura e analisa pacotes, mas nunca os modifica ou injeta. O princípio do menor privilégio: a captura requer permissões elevadas, mas não usamos essas permissões para nada além da leitura.

## Berkeley Packet Filter (BPF)

### O Que É

O BPF é uma máquina virtual dentro do kernel Linux/BSD que filtra pacotes de forma eficiente antes que eles cheguem ao espaço do usuário. Você escreve expressões de filtro como "tcp port 80", que são compiladas em bytecode BPF. O kernel executa esse bytecode contra cada pacote, mantendo apenas as correspondências.

### Por Que Isso Importa

Sem o BPF, a captura de pacotes no espaço do usuário é muito lenta para redes de alta velocidade. Cada pacote dispara uma troca de contexto do kernel para o espaço do usuário. A 10 Gbps, são milhões de interrupções por segundo. O BPF faz a filtragem no kernel, reduzindo as trocas de contexto em ordens de magnitude.

A botnet Mirai de 2016 sobrecarregou redes com floods UDP simples. Operadores de rede usaram filtros BPF para descartar o tráfego de ataque no nível do kernel, mantendo suas ferramentas de monitoramento operacionais. Sem o BPF, as próprias ferramentas de captura teriam caído.

### Como Funciona

O BPF compila expressões de filtro para bytecode que roda em uma máquina virtual baseada em registradores. Aqui está o que acontece quando você escreve "tcp port 443":

```
Carrega o campo de protocolo do cabeçalho IP
Compara com TCP (protocolo 6)
Se não for TCP, rejeita o pacote
Carrega a porta de destino do cabeçalho TCP
Compara com 443
Se não for 443, rejeita o pacote
Aceita o pacote
```

Isso roda no kernel para cada pacote antes que o espaço do usuário o veja. De `filters.py:136-150`, o FilterBuilder cria estas expressões:

```python
def port(self, port_number: int) -> FilterBuilder:
    _validate_port(port_number)
    self._expressions.append(f"port {port_number}")
    return self

def build(self, operator: Literal["and", "or"] = "and") -> str | None:
    if not self._expressions:
        return None
    return f" {operator} ".join(self._expressions)
```

As expressões se combinam com operadores booleanos. "tcp and port 443 and host 192.168.1.1" torna-se um bytecode BPF que verifica as três condições de forma eficiente.

### Armadilhas Comuns

**Erro 1: Não validar a sintaxe do filtro**

```python
# Ruim - passa filtro inválido para o kernel
filter_expr = user_input  # "tcp port foobar"
sniffer = AsyncSniffer(filter=filter_expr)  # Trava
```

O kernel rejeita sintaxe BPF inválida com erros crípticos. De `filters.py:227-235`:

```python
def validate_bpf_filter(filter_str: str) -> bool:
    try:
        from scapy.arch import compile_filter
        compile_filter(filter_str)
        return True
    except Exception:
        return False
```

Valide antes que a captura comece, não quando o usuário já esperou 5 minutos.

**Erro 2: Injeção de filtro via entrada não sanitizada**

```python
# Ruim - o usuário pode injetar filtros arbitrários
filter_expr = f"host {user_ip}"  # user_ip = "1.2.3.4 or (tcp port 1-65535)"
```

De `filters.py:35-41`, a validação captura isso:

```python
def _validate_ip_address(ip_address: str) -> None:
    try:
        ipaddress.ip_address(ip_address)
    except ValueError as e:
        raise ValidationError(f"Endereço IP inválido: {ip_address}") from e
```

Sempre valide as entradas com a verificação de tipo adequada, não com concatenação de strings.

## Análise de Camadas de Protocolo

### O Que É

Protocolos de rede se empilham em camadas, cada uma adicionando seu próprio cabeçalho com metadados. Quadros Ethernet contêm pacotes IP, que contêm segmentos TCP, que contêm requisições HTTP. A análise de protocolo significa dissecar essas camadas para extrair informações em cada nível.

O modelo OSI define sete camadas, mas o TCP/IP usa quatro camadas práticas:

```
Camada 4: Aplicação  (HTTP, DNS, SSH)
Camada 3: Transporte (TCP, UDP)
Camada 2: Rede       (IP)
Camada 1: Link       (Ethernet)
```

### Como Funciona

De `analyzer.py:14-48`, a função identify_protocol percorre as camadas:

```python
def identify_protocol(packet: Packet) -> Protocol:
    if packet.haslayer(DNS):
        return Protocol.DNS

    if packet.haslayer(TCP):
        tcp_layer = packet[TCP]
        if tcp_layer.dport == Ports.HTTP or tcp_layer.sport == Ports.HTTP:
            return Protocol.HTTP
        if tcp_layer.dport == Ports.HTTPS or tcp_layer.sport == Ports.HTTPS:
            return Protocol.HTTPS
        return Protocol.TCP
```

O sistema de camadas do Scapy permite que você verifique `packet.haslayer(TCP)` e acesse campos como `packet[TCP].dport`. Cada camada é um objeto Python com campos que coincidem com a especificação do protocolo.

A extração acontece em `analyzer.py:51-103`:

```python
def extract_packet_info(packet: Packet) -> PacketInfo | None:
    if packet.haslayer(Ether):
        ether_layer = packet[Ether]
        src_mac = ether_layer.src
        dst_mac = ether_layer.dst

    if packet.haslayer(IP):
        ip_layer = packet[IP]
        src_ip = ip_layer.src
        dst_ip = ip_layer.dst
```

Cada camada fornece informações diferentes. A camada de link fornece endereços MAC, a camada de rede fornece IPs, a camada de transporte fornece portas.

### Ataques Comuns

1. **Protocol tunneling** - Atacantes escondem tráfego malicioso dentro de protocolos legítimos. O tunelamento DNS exfiltra dados em consultas DNS. O tunelamento ICMP executa shells sobre pacotes de ping. O tunelamento HTTP ignora firewalls. A detecção requer análise de protocolo para identificar padrões incomuns.

2. **Manipulação de cabeçalho** - A manipulação de flags TCP (FIN scan, NULL scan, Xmas scan) sonda portas sem completar os handshakes. Ataques de fragmentação IP sobrecarregam os buffers de remontagem. Defenda-se validando a conformidade do protocolo.

3. **Inspeção de carga útil criptografada** - Mesmo o tráfego criptografado revela metadados. Handshakes TLS mostram detalhes do certificado, o SNI indica nomes de host de destino, tamanhos de pacotes e temporização revelam o comportamento da aplicação. Ataques de análise de tráfego funcionam sem descriptografia.

### Exemplo do Mundo Real

As revelações de Snowden em 2013 mostraram o sistema XKEYSCORE da NSA realizando análise de protocolo em escala. Ele capturava metadados de todas as camadas (IPs, portas, protocolos, detalhes de certificados) e os correlacionava para identificação de alvos. Você não precisava descriptografar o tráfego para identificar usuários e mapear relacionamentos de rede.

## Segurança de Threads e Concorrência

### O Que É

Código seguro para threads (thread-safe) pode ser chamado de múltiplas threads simultaneamente sem corromper dados. Isso requer primitivas de sincronização como locks, filas ou operações atômicas. Sem segurança de threads, o acesso concorrente causa condições de corrida (race conditions) onde o resultado depende da temporização das threads.

### Por Que Isso Importa

A captura de pacotes é inerentemente concorrente. Pacotes chegam de forma assíncrona enquanto você está processando pacotes anteriores. Perca pacotes e você perderá eventos de segurança. Bloqueie a thread de captura e você perderá pacotes. A solução é o threading produtor-consumidor com um buffer de fila.

De `capture.py:46-62`:

```python
def __init__(
    self,
    config: CaptureConfig,
    on_packet: Callable[[PacketInfo], None] | None = None,
    queue_size: int = CaptureDefaults.QUEUE_SIZE,
) -> None:
    self._queue: Queue[Packet] = Queue(maxsize = queue_size)
    self._stats = StatisticsCollector()
    self._stop_event = threading.Event()
    self._packet_count = 0
    self._dropped_packets = 0
    self._count_lock = threading.Lock()
```

A Queue é thread-safe por padrão. O lock protege as variáveis de contador que múltiplas threads modificam.

### Como Funciona

O padrão produtor-consumidor separa a captura do processamento:

```
Thread Produtora           Thread Consumidora
(Scapy AsyncSniffer)       (Loop de Processamento)
       ↓                          ↓
   Captura pacote             Pega da fila
       ↓                          ↓
   Coloca na fila             Analisa pacote
       ↓                          ↓
   Repete                     Atualiza estatísticas
```

A fila desacopla as threads. O produtor nunca bloqueia em um processamento lento. O consumidor processa em seu próprio ritmo. O tamanho do buffer determina o trade-off entre uso de memória e perda de pacotes.

De `statistics.py:47-67`, o coletor usa um lock para segurança de threads:

```python
def record_packet(self, packet: PacketInfo) -> None:
    with self._lock:
        self._total_packets += 1
        self._total_bytes += packet.size
        self._interval_packets += 1
        self._interval_bytes += packet.size

        self._protocol_counts[packet.protocol] += 1
        self._protocol_bytes[packet.protocol] += packet.size
```

O `with self._lock:` garante que apenas uma thread modifique as estatísticas por vez. Sem ele, os incrementos de contador disputariam e perderiam contagens.

### Armadilhas Comuns

**Erro 1: Esquecer de proteger o estado compartilhado**

```python
# Ruim - condição de corrida em packet_count
def _process_packet(self, packet):
    self.packet_count += 1  # Não é atômico!
```

Múltiplas threads fazem leitura-modificação-escrita na mesma variável. A Thread A lê 100, a Thread B lê 100, ambas escrevem 101. Você perdeu uma contagem. Use locks ou operações atômicas.

**Erro 2: Manter locks por muito tempo**

```python
# Ruim - bloqueia todas as threads durante E/S lenta
with self._lock:
    write_to_disk(data)  # E/S de arquivo com lock mantido
```

Locks serializam a execução. Mantenha-os apenas durante a seção crítica, nunca durante E/S ou computação cara. De `statistics.py:127-143`, o lock protege a cópia de dados, não a computação:

```python
def get_statistics(self) -> CaptureStatistics:
    with self._lock:
        return CaptureStatistics(
            start_time = self._start_time,
            total_packets = self._total_packets,
            protocol_distribution = dict(self._protocol_counts),
        )
```

A cópia `dict()` acontece dentro do lock porque ela acessa dados compartilhados. A formatação e o processamento acontecem fora do lock.

## Linha de Base de Rede e Detecção de Anomalias

### O Que É

Uma linha de base (baseline) de rede descreve o comportamento normal: proporções típicas de protocolos, padrões de largura de banda, pares de comunicação. A detecção de anomalias compara o tráfego atual com a linha de base para identificar desvios. Desvios significativos disparam alertas para investigação.

### Por Que Isso Importa

O worm Stuxnet de 2010 se espalhou via drives USB, mas se comunicava com servidores de comando e controle via HTTP. Linhas de base de rede teriam sinalizado conexões HTTP incomuns de sistemas de controle industrial que normalmente nunca acessam a internet. A detecção de anomalias captura ameaças que sistemas baseados em assinaturas perdem.

### Como Funciona

Este projeto coleta os dados necessários para o estabelecimento da linha de base. De `models.py:95-123`, o CaptureStatistics rastreia:

```python
@dataclass(slots = True)
class CaptureStatistics:
    protocol_distribution: dict[Protocol, int] = field(default_factory = dict)
    endpoints: dict[str, EndpointStats] = field(default_factory = dict)
    conversations: dict[tuple[str, str], ConversationStats] = field(default_factory = dict)
    bandwidth_samples: list[BandwidthSample] = field(default_factory = list)
```

A distribuição de protocolos mostra o mix normal de tráfego. Se sua rede é geralmente 60% TCP, 30% UDP, 10% outros, uma mudança repentina para 90% ICMP indica algo errado (possivelmente um flood de ping).

As estatísticas de endpoint rastreiam quem fala com quem. De `statistics.py:82-96`:

```python
def _update_endpoint(
    self,
    ip_address: str,
    sent_bytes: int = 0,
    received_bytes: int = 0,
) -> None:
    if ip_address not in self._endpoints:
        self._endpoints[ip_address] = EndpointStats(
            ip_address = ip_address
        )

    endpoint = self._endpoints[ip_address]
    endpoint.bytes_sent += sent_bytes
    endpoint.bytes_received += received_bytes
```

Rastreie a largura de banda por IP ao longo do tempo. Uma estação de trabalho transferindo gigabytes subitamente vale a pena ser investigada.

### Técnicas de Detecção

**Detecção estatística de anomalias:**

- Calcule a média e o desvio padrão para cada métrica.
- Alerte quando o valor atual exceder a média + 3σ.
- Funciona para largura de banda, taxas de pacotes, proporções de protocolos.

**Análise comportamental:**

- Rastreie grafos de comunicação (quem fala com quem).
- Alerte sobre novas conexões para destinos incomuns.
- Detecte movimentação lateral em violações.

**Análise de séries temporais:**

- Amostre a largura de banda a cada segundo (`statistics.py:112-127`).
- Procure por picos ou quedas repentinas.
- Ataques DDoS aparecem como aumentos dramáticos na taxa.

## Como Estes Conceitos se Relacionam

Os conceitos se constroem uns sobre os outros em camadas:

```
Acesso a Raw Socket
      ↓
Filtragem BPF (eficiência)
      ↓
Análise de Protocolo (compreensão)
      ↓
Coleta Segura para Threads (escala)
      ↓
Estabelecimento de Linha de Base (detecção)
```

Você precisa de raw sockets para ver os pacotes. O BPF torna isso eficiente. A análise de protocolo extrai significado. A segurança de threads permite o processamento em tempo real. Linhas de base permitem o monitoramento de segurança.

## Padrões e Frameworks da Indústria

### OWASP Top 10

Este projeto aborda:

- **A01:2021 - Controle de Acesso Quebrado** - A captura de pacotes requer verificação explícita de privilégios. O código valida a CAP_NET_RAW no Linux, Administrador no Windows, e falha claramente quando as permissões são insuficientes (`capture.py:341-375`).

- **A04:2021 - Design Inseguro** - O padrão produtor-consumidor com filas limitadas evita a exaustão de recursos. O tamanho da fila limita o uso de memória mesmo sob floods de pacotes (`capture.py:46-47`).

### MITRE ATT&CK

Técnicas relevantes:

- **T1040 - Network Sniffing** - Esta ferramenta implementa a técnica que os atacantes usam. Entender como a captura de pacotes funciona ajuda a detectar quando adversários implantam sniffers. Procure por interfaces em modo promíscuo e execução incomum de processos de captura.

- **T1071 - Application Layer Protocol** - O código de identificação de protocolo mostra como detectar tráfego de comando e controle escondido em HTTP/HTTPS. Frameworks de C2 como o Cobalt Strike usam DNS ou HTTP para canais ocultos.

- **T1048 - Exfiltration Over Alternative Protocol** - O tunelamento DNS e a exfiltração ICMP aparecem nas distribuições de protocolos. A detecção de linha de base sinaliza padrões incomuns de uso de protocolos.

### CWE

Enumerações de fraquezas comuns cobertas:

- **CWE-362 - Execução Concorrente usando Recurso Compartilhado com Sincronização Inadequada** - O projeto demonstra padrões adequados de lock para estatísticas compartilhadas. Condições de corrida em contadores de pacotes causariam métricas incorretas (`statistics.py:47-67`).

- **CWE-400 - Consumo de Recurso Não Controlado** - Fila limitada com tamanho configurável evita a exaustão de memória durante picos de tráfego. Sistemas de produção precisam de mecanismos de backpressure (`capture.py:77-80`).

## Exemplos do Mundo Real

### Estudo de Caso 1: Violação da Anthem Health Insurance (2015)

Atacantes comprometeram a rede da Anthem e exfiltraram 78,8 milhões de registros ao longo de vários meses. O monitoramento de rede detectou conexões incomuns de banco de dados para o exterior, mas os alertas foram ignorados. A captura de pacotes adequada e a análise de linha de base teriam sinalizado:

- Servidores de banco de dados iniciando conexões HTTPS de saída (comportamento incomum).
- Grandes transferências de dados fora do horário comercial (anomalia de largura de banda).
- Conexões para domínios recém-registrados (detecção baseada em reputação).

A violação custou US$ 115 milhões em acordos. A visibilidade da rede através da análise de pacotes não é opcional para ambientes de dados sensíveis.

### Estudo de Caso 2: Ataque à Cadeia de Suprimentos da SolarWinds (2020)

O backdoor SUNBURST se comunicava via DNS para comando e controle. Ele resolvia subdomínios de avsvmcloud.com para receber instruções. Defesas tradicionais perderam isso porque:

- O DNS é permitido para saída em todas as redes.
- A criptografia TLS escondia a carga útil do callback HTTP.
- Um software legítimo (Orion) estava realizando a comunicação.

No entanto, a análise em nível de pacote revelou anomalias:

- Volume incomum de consultas DNS vindas de servidores.
- Subdomínios com alta entropia (parecendo aleatórios).
- Respostas DNS com TTLs suspeitosamente longos.

Ferramentas de monitoramento de rede usando técnicas de captura de pacotes eventualmente identificaram sistemas comprometidos analisando padrões de metadados DNS, não o conteúdo da carga útil.

## Testando Seu Entendimento

Antes de passar para a arquitetura, certifique-se de que você consegue responder:

1. Por que a captura de pacotes requer privilégios elevados e qual capability específica do kernel ela precisa no Linux? Como você concederia essa capability sem tornar um programa totalmente privilegiado como root?

2. Explique como a filtragem BPF melhora o desempenho da captura de pacotes em comparação com a filtragem no espaço do usuário. Por que isso é crítico para redes de alta velocidade? O que acontece a 10 Gbps sem o BPF?

3. No padrão produtor-consumidor usado por este projeto, o que aconteceria se a thread consumidora bloqueasse por 10 segundos? Como a Queue evita a perda de dados? Qual é o trade-off entre o tamanho da fila e o uso de memória?

Se estas perguntas parecerem confusas, releia as seções relevantes. A implementação fará mais sentido quando estes fundamentos estiverem claros.

## Leitura Adicional

**Essencial:**

- **"The TCP/IP Guide" por Charles Kozierok** - Referência abrangente de protocolos. Leia as seções sobre enquadramento Ethernet, roteamento IP, gerenciamento de conexão TCP e manipulação de datagramas UDP. Estes são os protocolos que você dissecará nas capturas de pacotes.

- **"Building an IDS" (SANS Reading Room)** - Explica padrões de arquitetura de monitoramento de rede. O padrão produtor-consumidor, correspondência de assinaturas e conceitos de análise estatística se aplicam diretamente a este projeto.

**Aprofundamentos:**

- **"The BSD Packet Filter: A New Architecture for User-level Packet Capture" (McCanne & Jacobson, 1993)** - Artigo original do BPF. Explica o design da máquina virtual e por que a filtragem no nível do kernel é necessária. Leia isto quando quiser entender os internos do BPF.

- **Documentação da API PCAP (tcpdump.org)** - O Scapy envolve libpcap/WinPcap/Npcap. Entender a API C subjacente ajuda a depurar problemas de captura e explica as decisões de design do Scapy.

**Contexto histórico:**

- **"A Look Back at 'Security Problems in the TCP/IP Protocol Suite'" (Bellovin, 1989)** - Mostra que muitos ataques de rede têm décadas de idade. Falhas de design de protocolos de 1989 ainda afetam a segurança hoje. Entender a história evita repetir erros.
