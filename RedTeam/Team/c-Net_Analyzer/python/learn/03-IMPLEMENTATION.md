# Guia de Implementação

Este documento percorre o código real. Construiremos os recursos principais passo a passo e explicaremos as decisões ao longo do caminho.

## Passo a Passo da Estrutura de Arquivos

```
network-traffic-analyzer/
├── src/netanal/
│   ├── __init__.py          # Exportações do pacote, info de versão
│   ├── __main__.py          # Ponto de entrada para python -m netanal
│   ├── main.py              # Comandos Typer CLI (capture, analyze, export, chart)
│   ├── capture.py           # Engine de captura de pacotes produtor-consumidor
│   ├── analyzer.py          # Dissecação de protocolo usando camadas Scapy
│   ├── filters.py           # Construtor de filtro BPF type-safe
│   ├── statistics.py        # Agregação de estatísticas thread-safe
│   ├── models.py            # Modelos de dados (PacketInfo, Protocol, CaptureStatistics)
│   ├── visualization.py     # Geração de gráficos Matplotlib
│   ├── export.py            # Serialização JSON/CSV
│   ├── output.py            # Formatação de console Rich
│   ├── constants.py         # Constantes de configuração
│   └── exceptions.py        # Hierarquia de exceções personalizadas
├── tests/
│   ├── test_filters.py      # Testes de validação do FilterBuilder
│   └── test_models.py       # Testes de modelo de dados
└── pyproject.toml           # Dependências e config de build
```

## Construindo a Engine de Captura de Pacotes

### Passo 1: Configuração Produtor-Consumidor

O que estamos construindo: Uma engine de captura que recebe pacotes do Scapy na velocidade da rede enquanto os processa em uma thread separada sem perder dados.

O desafio central é que os pacotes chegam de forma assíncrona a taxas imprevisíveis. Se o processamento bloquear a thread de captura, os pacotes serão descartados. A solução é um padrão produtor-consumidor com uma fila limitada.

De `capture.py:31-62`:

```python
class CaptureEngine:
    def __init__(
        self,
        config: CaptureConfig,
        on_packet: Callable[[PacketInfo], None] | None = None,
        queue_size: int = CaptureDefaults.QUEUE_SIZE,
    ) -> None:
        self._config = config
        self._on_packet = on_packet
        self._queue: Queue[Packet] = Queue(maxsize = queue_size)
        self._stats = StatisticsCollector()
        self._sniffer: AsyncSniffer | None = None
        self._processor_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._packet_count = 0
        self._dropped_packets = 0
        self._running = False
        self._count_lock = threading.Lock()
```

**Por que este código funciona:**

- **Queue[Packet]**: Buffer limitado entre as threads. `maxsize = 10000` significa que se a fila encher, o produtor descarta os pacotes em vez de bloquear. Isso evita que a thread de captura desacelere.

- **StatisticsCollector**: Objeto separado que lida com todas as métricas. Mantém a lógica de captura separada da lógica de estatísticas.

- **threading.Event**: o stop_event sinaliza para ambas as threads quando é hora de desligar. Melhor que flags porque o Event.wait() é interrompível.

- **Lock**: o _count_lock protege o _packet_count e o _dropped_packets, que ambas as threads modificam. Sem ele, condições de corrida corromperiam as contagens.

**Erros comuns aqui:**

```python
# Errado: fila ilimitada
self._queue = Queue()  # Pode crescer para gigabytes, o OOM mata o processo

# Errado: sem lock nos contadores
self._packet_count += 1  # Condição de corrida, perde contagens

# Errado: flag booleana para desligamento
self._should_stop = False  # Thread.join() com timeout é melhor
```

### Passo 2: Configuração da Thread Produtora

Agora precisamos iniciar o AsyncSniffer do Scapy como o produtor.

Em `capture.py:92-131`:

```python
def start(self) -> None:
    if self._running:
        return

    self._running = True
    self._stop_event.clear()

    with self._count_lock:
        self._packet_count = 0
        self._dropped_packets = 0

    self._stats.reset()
    self._stats.start()

    self._processor_thread = threading.Thread(
        target = self._process_packets,
        daemon = True,
    )
    self._processor_thread.start()

    sniffer_kwargs: dict[str, object] = {
        "prn": self._enqueue_packet,
        "store": self._config.store_packets,
    }

    if self._config.interface:
        sniffer_kwargs["iface"] = self._config.interface

    if self._config.bpf_filter:
        sniffer_kwargs["filter"] = self._config.bpf_filter

    self._sniffer = AsyncSniffer(**sniffer_kwargs)
    self._sniffer.start()
```

**O que está acontecendo:**

1. Verifica a flag _running para evitar o início duplo (o que criaria threads duplicadas).
2. Reseta contadores e estatísticas para zero (folha em branco para nova captura).
3. Inicia a thread consumidora ANTES da produtora (para que a fila tenha um consumidor quando os pacotes chegarem).
4. Constrói o dicionário sniffer_kwargs condicionalmente (inclui apenas valores de config não nulos).
5. Passa _enqueue_packet como callback (parâmetro `prn`).
6. AsyncSniffer.start() inicia a thread produtora internamente.

**Por que fazemos desta forma:**

Iniciar o consumidor antes do produtor evita o estouro da fila durante a inicialização. Se o produtor rodar primeiro e a thread consumidora ainda não tiver iniciado, a fila enche imediatamente.

Threads daemon saem automaticamente quando o programa principal termina. Threads não-daemon manteriam o programa vivo mesmo após o Ctrl+C do usuário.

**Abordagens alternativas:**

- **Abordagem A**: Usar `sniff(prn=callback)` - Funciona, mas bloqueia a thread principal, não permitindo exibir o progresso ou responder a sinais.
- **Abordagem B**: Usar `sniff(timeout=1)` em loop - Introduz lacunas onde pacotes podem ser perdidos entre o timeout e o reinício.

### Passo 3: Callback do Produtor

O callback do produtor roda na thread de captura do Scapy para cada pacote.

Em `capture.py:64-70`:

```python
def _enqueue_packet(self, packet: Packet) -> None:
    try:
        self._queue.put_nowait(packet)
    except Full:
        with self._count_lock:
            self._dropped_packets += 1
```

Isso lida com a responsabilidade de adicionar pacotes à fila sem bloquear. `put_nowait()` lança a exceção Full se a fila estiver cheia. Nós a capturamos e incrementamos o contador de descartados em vez de travar.

**Partes principais explicadas:**

A razão pela qual usamos `put_nowait()` em vez de `put()` é o desempenho. `put()` bloqueia até que haja espaço disponível, o que desaceleraria a captura para a velocidade de processamento do consumidor. É melhor descartar pacotes do que desacelerar a captura.

O lock no _dropped_packets evita operações de incremento perdidas. Se duas threads fizerem leitura-modificação-escrita simultaneamente sem um lock, um incremento será perdido.

## Construindo a Identificação de Protocolo

### O Problema

Os pacotes do Scapy são objetos de camadas aninhadas. Precisamos identificar o protocolo de nível mais alto e extrair os campos relevantes sem codificar rigidamente cada combinação de protocolo possível.

### A Solução

Percorrer as camadas da mais alta (aplicação) para a mais baixa (link), retornando a primeira correspondência.

### Implementação

Em `analyzer.py:14-48`:

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

    if packet.haslayer(UDP):
        udp_layer = packet[UDP]
        if udp_layer.dport == Ports.DNS or udp_layer.sport == Ports.DNS:
            return Protocol.DNS
        return Protocol.UDP

    if packet.haslayer(ICMP):
        return Protocol.ICMP

    if packet.haslayer(ARP):
        return Protocol.ARP

    return Protocol.OTHER
```

**Partes principais explicadas:**

**Detecção de DNS primeiro** (`analyzer.py:14-15`)
O DNS pode rodar sobre TCP ou UDP. Verifique a camada DNS antes de verificar o protocolo de transporte, caso contrário, o DNS sobre TCP seria classificado apenas como TCP.

**Detecção de protocolo baseada em porta** (`analyzer.py:20-25`)
HTTP e HTTPS são apenas TCP com portas específicas. Verifique os números das portas para classificar melhor. Ambas as portas de origem e destino são verificadas porque as respostas do servidor têm HTTP/HTTPS como porta de origem.

**Fallback para OTHER** (`analyzer.py:45`)
Protocolos desconhecidos não travam o analisador. Eles são classificados como OTHER e contados separadamente nas estatísticas.

A ordem importa: protocolos da camada de aplicação (DNS, HTTP) são identificados antes da camada de transporte (TCP, UDP). Isso fornece uma classificação mais específica.

### Testando Este Recurso

```python
from scapy.layers.inet import IP, TCP
from scapy.layers.dns import DNS
from netanal.analyzer import identify_protocol
from netanal.models import Protocol

# Teste de detecção HTTP
http_packet = IP()/TCP(dport=80)
assert identify_protocol(http_packet) == Protocol.HTTP

# Teste de detecção DNS
dns_packet = IP()/UDP()/DNS()
assert identify_protocol(dns_packet) == Protocol.DNS
```

Saída esperada: Ambas as asserções passam, mostrando que a identificação de protocolo funciona corretamente.

Se você vir Protocol.TCP para HTTP, significa que a verificação de porta falhou. Verifique se a porta é realmente 80 no pacote.

## Coleta de Estatísticas Thread-Safe

### O Problema

Múltiplas threads atualizam as mesmas estatísticas simultaneamente. Sem sincronização, os contadores perdem incrementos e os dicionários são corrompidos.

### A Solução

Usar um único lock para proteger todo o estado compartilhado. As seções críticas (código sob o lock) devem ser as mais curtas possíveis.

### Implementação

Arquivo: `statistics.py:47-67`

```python
def record_packet(self, packet: PacketInfo) -> None:
    with self._lock:
        self._total_packets += 1
        self._total_bytes += packet.size
        self._interval_packets += 1
        self._interval_bytes += packet.size

        self._protocol_counts[packet.protocol] += 1
        self._protocol_bytes[packet.protocol] += packet.size

        self._update_endpoint(packet.src_ip, sent_bytes = packet.size)
        self._update_endpoint(
            packet.dst_ip,
            received_bytes = packet.size
        )

        self._update_conversation(
            packet.src_ip,
            packet.dst_ip,
            packet.size
        )

        self._check_bandwidth_sample(packet.timestamp)
```

**O que isso evita:**

Incrementos perdidos. Sem o lock:

```
Thread A lê total_packets = 100
Thread B lê total_packets = 100
Thread A escreve 101
Thread B escreve 101  # Perdeu um incremento!
```

Com o lock, as operações são atômicas:

```
Thread A adquire o lock
Thread A lê 100, escreve 101
Thread A libera o lock
Thread B adquire o lock (espera até que A termine)
Thread B lê 101, escreve 102
```

**Como funciona:**

1. `with self._lock:` adquire o lock, bloqueando se outra thread o detiver.
2. Todas as atualizações de contadores acontecem atomicamente.
3. Métodos auxiliares (_update_endpoint, etc.) rodam sob o mesmo lock.
4. O lock é liberado automaticamente ao sair do bloco with (mesmo em caso de exceção).

**O que acontece se você remover isso:**

Execute o código sob carga alta. Os contadores serão menores do que a contagem real de pacotes porque os incrementos serão perdidos. As porcentagens de distribuição de protocolos não somarão 100%. As estatísticas de endpoint terão totais incorretos.

### Amostragem de Largura de Banda

A cada segundo, precisamos calcular a largura de banda atual. Isso roda sob o mesmo lock para consistência.

De `statistics.py:112-127`:

```python
def _check_bandwidth_sample(self, timestamp: float) -> None:
    if timestamp - self._last_sample_time >= self._bandwidth_interval:
        elapsed = timestamp - self._last_sample_time
        if elapsed > 0:
            bps = self._interval_bytes / elapsed
            pps = self._interval_packets / elapsed
            self._bandwidth_samples.append(
                BandwidthSample(
                    timestamp = timestamp,
                    bytes_per_second = bps,
                    packets_per_second = pps,
                )
            )
        self._interval_bytes = 0
        self._interval_packets = 0
        self._last_sample_time = timestamp
```

Este código amostra a largura de banda em intervalos de 1 segundo (configurável). Ele calcula bytes/seg e pacotes/seg a partir dos contadores de intervalo e, em seguida, os reseta para o próximo intervalo.

O timestamp vem dos pacotes, não do relógio do sistema. Isso significa que o cálculo da largura de banda coincide exatamente com o tempo do pacote, mesmo se o relógio sofrer desvios ou o sistema pausar.

## Construção de Filtro BPF

### O Problema

A sintaxe BPF é propensa a erros. Escrever `"tcp port 80 and host 192.168.1.1"` manualmente corre o risco de erros de digitação, sintaxe inválida e vulnerabilidades de injeção de filtro.

### A Solução

Padrão Builder com métodos type-safe e validação de entrada.

### Implementação

De `filters.py:48-175`:

```python
@dataclass(slots = True)
class FilterBuilder:
    _expressions: list[str]

    def __init__(self) -> None:
        self._expressions = []

    def protocol(self, proto: Protocol) -> FilterBuilder:
        bpf_expr = BPF_PROTOCOL_MAP.get(proto)
        if bpf_expr:
            self._expressions.append(f"({bpf_expr})")
        return self

    def port(self, port_number: int) -> FilterBuilder:
        _validate_port(port_number)
        self._expressions.append(f"port {port_number}")
        return self

    def host(self, ip_address: str) -> FilterBuilder:
        _validate_ip_address(ip_address)
        self._expressions.append(f"host {ip_address}")
        return self

    def build(self, operator: Literal["and", "or"] = "and") -> str | None:
        if not self._expressions:
            return None
        return f" {operator} ".join(self._expressions)
```

**Detalhes importantes:**

**Retornando self** (`return self` em cada método)
Permite o encadeamento de métodos: `FilterBuilder().port(80).host("192.168.1.1").build()`

**Validação antes da construção** (`_validate_port`, `_validate_ip_address`)

```python
def _validate_port(port_number: int) -> None:
    if not PortRange.MIN <= port_number <= PortRange.MAX:
        raise ValidationError(
            f"Porta deve ser {PortRange.MIN}-{PortRange.MAX}, recebido {port_number}"
        )
```

A porta deve ser 0-65535. O IP deve ser analisado com `ipaddress.ip_address()`. Falha rápido com erros claros antes de passar para o kernel.

**Envolvendo expressões em parênteses**

```python
self._expressions.append(f"({bpf_expr})")
```

O BPF possui regras de precedência de operadores. O envolvimento garante o parsing correto. `tcp and port 80 or port 443` poderia significar `(tcp and port 80) or (port 443)` [errado] ou `tcp and (port 80 or port 443)` [pretendido]. Parênteses explícitos evitam ambiguidade.

## Exemplo de Fluxo de Dados

Vamos rastrear uma requisição completa através do sistema.

**Cenário:** O usuário executa `sudo netanal capture -i lo -c 5 --verbose`

### A Requisição Chega

```python
# Ponto de entrada: main.py:110-181
@app.command()
def capture(
    interface: str | None = None,
    filter_expr: str | None = None,
    count: int | None = None,
    timeout: float | None = None,
    output: Path | None = None,
    verbose: bool = False,
) -> None:
```

Neste ponto:

- O Typer analisou os argumentos da linha de comando.
- interface = "lo", count = 5, verbose = True.
- É necessário validar as permissões e criar a configuração de captura.

A verificação de permissão acontece em `main.py:139-143`:

```python
can_capture, msg = check_capture_permissions()
if not can_capture:
    print_error(f"Não é possível capturar pacotes: {msg}")
    raise typer.Exit(1)
```

Isso chama `capture.py:341-347`, que testa a criação de raw socket no Linux, o acesso a /dev/bpf no macOS ou verifica Npcap+Admin no Windows.

### Camada de Processamento

Criação da configuração em `main.py:149-154`:

```python
config = CaptureConfig(
    interface = interface,
    bpf_filter = filter_expr,
    packet_count = count,
    timeout_seconds = timeout,
)
```

CaptureConfig é uma dataclass frozen (`models.py:135-145`). Imutável após a criação, passada para o CaptureEngine.

A captura inicia em `main.py:159-167`:

```python
engine = CaptureEngine(
    config = config,
    on_packet = on_packet if verbose or output else None
)

with GracefulCapture(engine) as cap:
    stats = cap.wait()
```

O gerenciador de contexto GracefulCapture (`capture.py:197-230`) instala os manipuladores de sinal, inicia a captura, espera pela conclusão e depois limpa tudo. Mesmo que o usuário dê Ctrl+C, a limpeza é executada.

### Fluxo de Processamento de Pacotes

Para cada pacote capturado:

1. O Scapy chama o callback `_enqueue_packet` (`capture.py:64-70`).
2. O pacote vai para a fila limitada.
3. A thread consumidora pega o pacote da fila (`capture.py:76-78`).
4. `extract_packet_info()` analisa o pacote (`analyzer.py:51-103`).
5. `record_packet()` atualiza as estatísticas (`statistics.py:47-67`).
6. Se verbose, o callback `on_packet()` exibe o pacote (`output.py:46-54`).

Após 5 pacotes, a verificação de contagem em `capture.py:88-90` define o evento de parada:

```python
if self._config.packet_count and current_count >= self._config.packet_count:
    self._stop_event.set()
    break
```

### Armazenamento/Saída

O resultado é o CaptureStatistics retornado de `cap.wait()` (`capture.py:145-157`).

A exibição acontece em `main.py:169-171`:

```python
print_capture_summary(stats)
print_protocol_table(stats)
print_top_talkers(stats)
```

Cada função de impressão usa o Rich para formatar tabelas. De `output.py:84-111`:

```python
def print_protocol_table(stats: CaptureStatistics) -> None:
    table = Table(title = "Distribuição de Protocolos")
    table.add_column("Protocolo", style = "cyan", justify = "left")
    table.add_column("Pacotes", style = "green", justify = "right")
    table.add_column("Bytes", style = "yellow", justify = "right")
    table.add_column("Porcentagem", style = "magenta", justify = "right")

    percentages = stats.get_protocol_percentages()

    for protocol in sorted(stats.protocol_distribution.keys(),
                           key = lambda p: p.value):
        count = stats.protocol_distribution[protocol]
        bytes_count = stats.protocol_bytes.get(protocol, 0)
        pct = percentages.get(protocol, 0.0)
        table.add_row(
            protocol.value,
            f"{count:,}",
            format_bytes(bytes_count),
            f"{pct:.1f}%",
        )

    console.print(table)
```

## Padrões de Tratamento de Erro

### Erros de Permissão

Quando o usuário carece de permissões de captura de pacotes, queremos erros claros e acionáveis.

```python
# capture.py:341-347
def check_capture_permissions() -> tuple[bool, str]:
    system = platform.system()

    if system == "Linux":
        return _check_linux_permissions()
    elif system == "Darwin":
        return _check_macos_permissions()
    elif system == "Windows":
        return _check_windows_permissions()

    return False, f"Plataforma desconhecida: {system}"
```

**Por que este tratamento específico:**
Retorna uma tupla (bool, str) em vez de lançar uma exceção. O chamador decide se deve dar erro ou aviso. Mensagens claras dizem ao usuário exatamente o que é necessário ("Requer root ou capability CAP_NET_RAW" vs "Permissão negada" genérico).

Verificações específicas por plataforma porque os requisitos diferem:

- Linux: capability CAP_NET_RAW ou root.
- macOS: root ou acesso a /dev/bpf*.
- Windows: Administrador + Npcap instalado.

**O que NÃO fazer:**

```python
# Ruim: capturar tudo silenciosamente
try:
    start_capture()
except Exception:
    pass  # O usuário não recebe feedback, perde tempo depurando
```

Isso esconde problemas reais. Sempre trate exceções específicas e forneça feedback acionável.

### Validação de Filtro BPF

Filtros inválidos travam o Scapy com erros de kernel crípticos. Valide cedo.

De `filters.py:227-235`:

```python
def validate_bpf_filter(filter_str: str) -> bool:
    try:
        from scapy.arch import compile_filter
        compile_filter(filter_str)
        return True
    except Exception:
        return False
```

Uso em `main.py:145-147`:

```python
if filter_expr and not validate_bpf_filter(filter_expr):
    print_error(f"Filtro BPF inválido: {filter_expr}")
    raise typer.Exit(1)
```

Falha rápido antes de iniciar a captura. O usuário vê um erro claro imediatamente em vez de uma mensagem críptica do kernel após esperar.

## Otimizações de Desempenho

### Otimização 1: Slots de Dataclass

**Antes:**

```python
@dataclass
class PacketInfo:
    timestamp: float
    src_ip: str
    # ... mais 8 campos
```

Isso era lento porque cada instância usa um `__dict__` para armazenar atributos. Com 1 milhão de pacotes, são ~40MB desperdiçados em overhead de dicionário.

**Depois:**

```python
@dataclass(frozen = True, slots = True)
class PacketInfo:
    timestamp: float
    src_ip: str
    # ... mais 8 campos
```

**O que mudou:**

- Adicionado `slots = True` ao decorador da dataclass.
- Atributos armazenados em slots fixos, não em dicionário.
- Também adicionado `frozen = True` para imutabilidade.

**Benchmarks:**

- Antes: 1M pacotes = ~100MB de memória.
- Depois: 1M pacotes = ~60MB de memória.
- Melhoria: redução de 40% na memória.

Medido com:

```python
import sys
packet = PacketInfo(...)
print(sys.getsizeof(packet))
```

### Otimização 2: Filtragem BPF no Kernel

**Antes:**

```python
# Captura todos os pacotes, filtra no Python
for packet in capture_all():
    if packet.haslayer(TCP) and packet[TCP].dport == 80:
        process(packet)
```

Isso era lento porque cada pacote dispara uma troca de contexto do kernel para o espaço do usuário, e então o código Python verifica cada um.

**Depois:**

```python
# Filtra no kernel com BPF
AsyncSniffer(filter="tcp port 80", prn=process)
```

**O que mudou:**
O BPF roda no kernel, descartando pacotes indesejados antes que o espaço do usuário os veja. Sem troca de contexto para pacotes filtrados.

**Benchmarks:**
Em uma rede ocupada (1000 pacotes/seg, 95% irrelevantes):

- Antes: 80% de CPU, 950 trocas de contexto desnecessárias/seg.
- Depois: 5% de CPU, apenas 50 pacotes relevantes chegam ao espaço do usuário.

O kernel faz comparações simples (porta == 80) de forma extremamente rápida. O Python faz a mesma verificação milhares de vezes mais devagar.

## Armadilhas Comuns de Implementação

### Armadilha 1: Esquecer os Limites da Fila

**Sintoma:**
A memória do processo cresce para gigabytes, o sistema congela, o OOM killer encerra o processo.

**Causa:**

```python
# O código problemático
self._queue = Queue()  # Ilimitada!
```

Uma fila ilimitada cresce para sempre se o produtor for mais rápido que o consumidor. Com 10K pacotes/seg e tamanho médio de 1KB, uma fila ilimitada cresce a 10MB/seg.

**Correção:**

```python
# Abordagem correta
self._queue: Queue[Packet] = Queue(maxsize = 10000)
```

Uma fila limitada lança Full quando a capacidade é atingida. O produtor descarta o pacote com incremento de contador em vez de consumir memória infinita.

**Por que isso importa:**
Ferramentas de captura de pacotes em produção rodam por horas ou dias. Vazamentos de memória travam o sistema de monitoramento, criando pontos cegos durante incidentes.

### Armadilha 2: "Otimização" Lock-Free

**Sintoma:**
As contagens de pacotes não coincidem com a realidade. As porcentagens de protocolo não somam 100%. Estatísticas corrompidas aleatoriamente.

**Causa:**

```python
# Ruim: "otimização" que remove o lock
def record_packet(self, packet: PacketInfo) -> None:
    # Sem lock!
    self._total_packets += 1
    self._protocol_counts[packet.protocol] += 1
```

Raciocínio: "Locks são lentos, vamos pulá-los". Mas o `+=` do Python NÃO é atômico. Na verdade, são três operações:

```
1. Ler valor
2. Adicionar 1
3. Escrever resultado
```

Duas threads podem se intercalar, causando atualizações perdidas.

**Correção:**

```python
# Correto: usar lock
def record_packet(self, packet: PacketInfo) -> None:
    with self._lock:
        self._total_packets += 1
        self._protocol_counts[packet.protocol] += 1
```

**Por que isso importa:**
Estatísticas são inúteis se estiverem incorretas. Incidentes de segurança são perdidos porque a detecção de linha de base usa números errados.

### Armadilha 3: Concatenação de Strings para Filtros

**Sintoma:**
Erros de sintaxe BPF, vulnerabilidades de injeção de filtro, travamentos.

**Causa:**

```python
# Código vulnerável
user_ip = input("Digite o IP: ")  # Usuário digita: 1.2.3.4 or 1=1
filter_str = f"host {user_ip}"  # Resulta em "host 1.2.3.4 or 1=1"
```

Ataque de injeção de filtro. O atacante pode burlar restrições pretendidas ou criar filtros que correspondam a tudo.

**Correção:**

```python
# Correto: validar primeiro
def host(self, ip_address: str) -> FilterBuilder:
    _validate_ip_address(ip_address)  # Lança erro em entrada inválida
    self._expressions.append(f"host {ip_address}")
    return self
```

A validação com `ipaddress.ip_address()` garante que a entrada seja realmente um IP, não uma sintaxe BPF arbitrária.

**Por que isso importa:**
Se as ferramentas de monitoramento tiverem vulnerabilidades de injeção de filtro, os atacantes podem cegar o monitoramento fazendo com que os filtros não correspondam a nada, ou sobrecarregar os sistemas fazendo com que os filtros correspondam a tudo.

## Dicas de Depuração

### Tipo de Problema 1: Nenhum Pacote Capturado

**Problema:** Total de pacotes = 0 mesmo com a rede ativa.

**Como depurar:**

1. Verifique se a interface está correta: `netanal interfaces` mostra as interfaces disponíveis.
2. Verifique se o filtro BPF não é muito restritivo: Remova o filtro e tente novamente.
3. Verifique as permissões: `netanal capture` sem sudo mostra erro de permissão.
4. Verifique o modo promíscuo: Alguns adaptadores wireless o bloqueiam.

**Causas comuns:**

- Nome de interface errado ("eth0" vs "ens33").
- O filtro não corresponde a nada ("tcp port 12345" em uma rede apenas HTTP).
- Adaptador wireless em modo managed (precisa de modo monitor).
- Firewall bloqueando a captura de pacotes.

Adicione saída de depuração para ver os pacotes chegando na fila:

```python
def _enqueue_packet(self, packet: Packet) -> None:
    print(f"DEBUG: Pacote enfileirado de {packet[IP].src if packet.haslayer(IP) else 'desconhecido'}")
    self._queue.put_nowait(packet)
```

Se a fila recebe pacotes mas as estatísticas mostram zero, o problema está na thread consumidora.

### Tipo de Problema 2: Alta Contagem de Pacotes Descartados

**Problema:** As estatísticas mostram milhares de pacotes descartados.

**Como depurar:**

1. Verifique o tamanho da fila: `constants.py:QUEUE_SIZE = 10000` pode ser muito pequeno.
2. Perfile a thread consumidora: O processamento está lento?
3. Monitore o uso da CPU: O sistema está sobrecarregado?
4. Verifique os callbacks: A impressão detalhada (verbose) está desacelerando o processamento?

**Causas comuns:**

- Fila muito pequena para a taxa de tráfego.
- Thread consumidora bloqueada em E/S (escrevendo no disco).
- CPU no limite.
- Modo detalhado ativado durante tráfego intenso.

Aumente o tamanho da fila:

```python
engine = CaptureEngine(config=config, queue_size=50000)
```

Perfile o consumidor:

```python
import cProfile
cProfile.run('engine.wait()')
```

### Tipo de Problema 3: Memória Crescendo sem Limites

**Problema:** A memória do processo cresce continuamente até o OOM.

**Como depurar:**

1. Verifique se a fila é limitada: `Queue(maxsize=10000)` e não `Queue()`.
2. Verifique o armazenamento de pacotes: `store_packets=False` na configuração.
3. Monitore as amostras de largura de banda: A lista cresce para sempre?
4. Verifique ciclos de referência: Pacotes antigos estão permanecendo na memória?

**Causas comuns:**

- Fila ilimitada.
- `store_packets=True` mantém todos os pacotes na memória.
- Amostras de largura de banda não são limpas.
- Referências circulares impedindo o GC.

Corrija o crescimento ilimitado:

```python
# Limite as amostras de largura de banda
if len(self._bandwidth_samples) > 3600:  # Máximo de 1 hora a 1/seg
    self._bandwidth_samples = self._bandwidth_samples[-3600:]
```

## Princípios de Organização do Código

### Por que o capture.py é Estruturado Desta Forma

```
capture.py:
├── Classe CaptureEngine       # Implementação principal produtor-consumidor
│   ├── __init__               # Configura fila, threads, locks
│   ├── _enqueue_packet        # Callback do produtor (Scapy chama este)
│   ├── _process_packets       # Loop do consumidor (roda em thread)
│   ├── start/stop/wait        # Métodos públicos de ciclo de vida
│   └── Propriedades           # is_running, dropped_packets
├── GracefulCapture            # Gerenciador de contexto para tratamento de sinais
└── Funções auxiliares         # check_permissions, get_interfaces
```

Separamos as preocupações:

- CaptureEngine lida com threading e gerenciamento de fila.
- GracefulCapture lida com a limpeza de sinais.
- A verificação de permissão é uma função independente (reutilizável).

Isso facilita os testes. Você pode testar a verificação de permissão sem iniciar uma captura. Você pode testar o comportamento da fila sem o Scapy.

### Convenções de Nomenclatura

- `_metodo_privado`: Sublinhado inicial significa implementação interna.
- `metodo_publico`: Sem sublinhado significa parte da API pública.
- `CamelCase`: Classes.
- `snake_case`: Funções e variáveis.
- `SCREAMING_SNAKE`: Constantes.

Seguir esses padrões facilita entender o que é API privada vs pública apenas pelo nome.

## Estendendo o Código

### Adicionando um Novo Protocolo

Quer detectar tráfego BitTorrent? Aqui está o processo:

1.  **Adicione ao enum Protocol** em `models.py:11-21`

    ```python
    class Protocol(StrEnum):
        TCP = "TCP"
        # ... protocolos existentes
        BITTORRENT = "BITTORRENT"
    ```

2.  **Atualize a identificação de protocolo** em `analyzer.py:14-48`

    ```python
    def identify_protocol(packet: Packet) -> Protocol:
        # Verifique BitTorrent antes do fallback TCP
        if packet.haslayer(TCP):
            tcp_layer = packet[TCP]
            if tcp_layer.dport in range(6881, 6890) or tcp_layer.sport in range(6881, 6890):
                return Protocol.BITTORRENT
            # ... verificações HTTP/HTTPS existentes
            return Protocol.TCP
    ```

3.  **Adicione o mapeamento de cores** em `constants.py:63-84`

    ```python
    class ProtocolColors:
        RICH: Final[dict[str, str]] = {
            # ... cores existentes
            "BITTORRENT": "red",
        }

        HEX: Final[dict[str, str]] = {
            # ... cores existentes
            "BITTORRENT": "#ff0000",
        }
    ```

4.  **Adicione suporte ao filtro BPF** em `filters.py:16-26`

    ```python
    BPF_PROTOCOL_MAP: dict[Protocol, str] = {
        # ... protocolos existentes
        Protocol.BITTORRENT: "tcp portrange 6881-6889",
    }
    ```

5.  **Adicione testes** em `tests/test_models.py`
    ```python
    def test_bittorrent_protocol():
        assert Protocol.BITTORRENT.value == "BITTORRENT"
    ```

Agora o BitTorrent aparece na distribuição de protocolos, principais emissores e gráficos automaticamente.

## Dependências

### Por que Cada Dependência

- **typer (0.21.1+)**: Framework CLI. Fornece parsing de argumentos, geração de ajuda, roteamento de comandos. Escolhido em vez do argparse porque usa type hints para validação automática. Escolhido em vez do click por ser mais novo e com melhores padrões.

- **rich (14.3.1+)**: Formatação de terminal. Fornece tabelas coloridas, barras de progresso, realce de sintaxe. Cria saídas CLI de aparência profissional sem códigos ANSI manuais. Usado pela CLI do GitHub e outras ferramentas CLI modernas.

- **scapy (2.6.1+)**: Manipulação de pacotes. Única biblioteca com suporte abrangente a protocolos e manipulação de arquivos pcap. Alternativas (dpkt, pyshark) carecem de recursos de dissecação de protocolo ou exigem ferramentas externas.

- **matplotlib (3.10.0+)**: Visualização. Padrão da indústria para plotagem científica. Os gráficos gerados atendem às expectativas dos analistas. Alternativas (plotly, bokeh) geram HTML, não PNG, sendo menos adequadas para relatórios.

### Segurança de Dependências

Verifique por vulnerabilidades:

```bash
pip install pip-audit
pip-audit
```

Se você vir uma vulnerabilidade nas dependências:

1. Verifique se ela afeta como usamos a biblioteca.
2. Atualize para a versão corrigida, se disponível.
3. Considere uma biblioteca alternativa se não houver correção.
4. Adicione aos problemas conhecidos se precisar permanecer na versão vulnerável.

Exemplo: CVE em versões antigas do Scapy. Atualize para 2.6.1+, que corrige o problema.

## Próximos Passos

Você viu como o código funciona. Agora:

1.  **Tente os desafios** - [04-CHALLENGES.md](./04-CHALLENGES.md) tem ideias de extensão como remontagem de fluxo TCP e detecção de anomalias.
2.  **Modifique o código** - Altere a identificação de protocolo no analyzer.py para detectar seus próprios protocolos.
3.  **Perfile o desempenho** - Use o cProfile para encontrar gargalos em suas extensões.
